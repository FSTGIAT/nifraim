"""The agent's data, as a small Markdown site the AI can navigate ("data map").

The office agent (and later any AI) should not get one giant dump. It gets
`index.md` — the categories, a one-line fact each, links — and DRILLS DOWN by
opening linked pages, following the connections the answer needs:

    index.md
    ├── companies.md ──────► companies/<key>.md   production · נפרעים · agreement rates ·
    │                                              unpaid customers · contact · open mail ·
    │                                              open collection case + next step
    ├── unpaid.md ─────────► companies/<key>.md · customers/<id>.md
    ├── customers/<id>.md                          products per insurer, paid/unpaid,
    │                                              mails about the customer, links back
    ├── mail.md ───────────► companies/<key>.md · customers/<id>.md
    └── agreements.md ─────► companies/<key>.md

Pages are rendered ON DEMAND from one loaded context (`MapContext`) — a book
has hundreds of customers, only the pages the AI opens are built. Everything
is user-scoped. Nothing here writes. Links are relative paths the `open_page`
tool accepts verbatim.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collection_case import CollectionCase
from app.models.commission_comparison import CommissionComparison
from app.models.commission_rate import CommissionRate
from app.models.company_contact import CompanyContact
from app.models.mail_item import OPEN_STATUSES, MailItem
from app.models.user import User
from app.utils.company_norm import company_stem

STATUS_HE = {
    "production_only_file": "בפרודוקציה (לא בהשוואה האחרונה)",
    "matched": "שולם", "only_production": "לא שולם", "only_commission": "רק בנפרעים"}


def _key(name: str | None) -> str:
    return company_stem(name or "") or (name or "").strip()


def _slug(key: str) -> str:
    return re.sub(r"[\s/]+", "-", key.strip()) or "unknown"


def _money(v) -> str:
    try:
        return f"₪{round(float(v)):,}"
    except (TypeError, ValueError):
        return "—"


@dataclass
class MapContext:
    user: User
    result: dict = field(default_factory=dict)          # latest merged comparison
    period_label: str = ""
    rates: dict = field(default_factory=lambda: defaultdict(list))      # key -> [CommissionRate]
    contacts: dict = field(default_factory=dict)        # key -> CompanyContact
    cases: dict = field(default_factory=dict)           # key -> CollectionCase (latest period)
    mails: list = field(default_factory=list)           # open MailItem
    names: dict = field(default_factory=dict)           # key -> display name
    extra: dict = field(default_factory=dict)           # id -> customer from production only (@-mentioned, not in the comparison)
    calls: list = field(default_factory=list)           # done CallRecording, newest first
    policies: dict = field(default_factory=dict)        # id -> policies picture (services/policies/store.build_picture)

    # derived
    @property
    def customers(self) -> list[dict]:
        return self.result.get("customers") or []

    def company_rows(self) -> dict[str, dict]:
        """key -> {name, customers:set, paid:set, unpaid:set, products:int, received}"""
        out: dict[str, dict] = {}
        for c in self.customers:
            status = c.get("match_status")
            for p in (c.get("production_products") or []):
                k = _key(p.get("company") or p.get("company_full"))
                if not k:
                    continue
                r = out.setdefault(k, {"customers": set(), "paid": set(), "unpaid": set(), "products": 0, "received": 0.0})
                r["customers"].add(c.get("id_number"))
                r["products"] += 1
                (r["paid"] if status == "matched" else r["unpaid"] if status == "only_production" else set()).add(c.get("id_number"))
                self.names.setdefault(k, p.get("company") or p.get("company_full"))
            # Unpaid at one company, paid at another: these are the paid ones.
            for p in (c.get("paid_production_products") or []):
                k = _key(p.get("company") or p.get("company_full"))
                if not k:
                    continue
                r = out.setdefault(k, {"customers": set(), "paid": set(), "unpaid": set(), "products": 0, "received": 0.0})
                r["customers"].add(c.get("id_number"))
                r["products"] += 1
                r["paid"].add(c.get("id_number"))
                self.names.setdefault(k, p.get("company") or p.get("company_full"))
            for p in (c.get("commission_products") or []):
                k = _key(p.get("company") or p.get("receiving_company"))
                if k:
                    r = out.setdefault(k, {"customers": set(), "paid": set(), "unpaid": set(), "products": 0, "received": 0.0})
                    r["received"] += float(p.get("commission") or p.get("commission_paid") or 0)
                    self.names.setdefault(k, p.get("company") or p.get("receiving_company"))
        return out


async def load(db: AsyncSession, user: User) -> MapContext:
    ctx = MapContext(user=user)
    row = (await db.execute(
        select(CommissionComparison.result_json)
        .where(CommissionComparison.user_id == user.id, CommissionComparison.category == "merged")
        .order_by(CommissionComparison.computed_at.desc()).limit(1)
    )).scalar_one_or_none()
    ctx.result = row if isinstance(row, dict) else {}
    p = ctx.result.get("period_month")
    if p:
        from datetime import date
        from app.services.cycle_service import month_label
        try:
            ctx.period_label = month_label(date.fromisoformat(str(p)[:10]))
        except ValueError:
            pass
    for r in (await db.execute(select(CommissionRate).where(CommissionRate.user_id == user.id))).scalars():
        ctx.rates[_key(r.company_name)].append(r)
        ctx.names.setdefault(_key(r.company_name), r.company_name)
    for c in (await db.execute(select(CompanyContact).where(CompanyContact.user_id == user.id))).scalars():
        ctx.contacts[_key(c.company_name)] = c
    latest = (await db.execute(
        select(func.max(CollectionCase.period)).where(CollectionCase.user_id == user.id)
    )).scalar_one_or_none()
    for c in (await db.execute(select(CollectionCase).where(CollectionCase.user_id == user.id))).scalars():
        if c.period == latest or c.status in ("sent", "replied"):
            ctx.cases[c.company_key] = c
    # every customer in the active production files, not only the compared ones —
    # the app's own search finds them there, so the agent must too
    await add_production_customers(db, ctx)
    ctx.mails = (await db.execute(
        select(MailItem).where(MailItem.user_id == user.id, MailItem.status.in_(OPEN_STATUSES))
        .order_by(MailItem.received_at.desc()).limit(40)
    )).scalars().all()
    from app.models.call_recording import CallRecording
    ctx.calls = (await db.execute(
        select(CallRecording).where(CallRecording.user_id == user.id, CallRecording.status == "done",
                                    __import__("app.services.calls.privacy", fromlist=["visible"]).visible())
        .order_by(CallRecording.created_at.desc()).limit(300)
    )).scalars().all()
    from app.services.policies.store import all_pictures
    ctx.policies = await all_pictures(db, user.id)
    return ctx


# ─────────────────────────── pages ─────────────────────────────────────────

def page_index(ctx: MapContext) -> str:
    comp = ctx.company_rows()
    s = ctx.result.get("summary") or {}
    unpaid_cases = [c for c in ctx.cases.values() if c.status != "resolved"]
    lines = [
        f"# הנתונים של {ctx.user.full_name or ctx.user.email}",
        f"תקופת ההשוואה האחרונה: {ctx.period_label or 'אין השוואה עדיין'}",
        "",
        "## קטגוריות",
        f"- [חברות](companies.md) — {len(comp)} חברות בתיק",
        f"- [לא שולם](unpaid.md) — {s.get('only_in_production', 0)} לקוחות בלי עמלה · {len(unpaid_cases)} חברות בטיפול גבייה",
        f"- [מיילים פתוחים](mail.md) — {len(ctx.mails)} מיילים שמחכים לטיפול",
        "- [התאמת עמלות](reconcile.md) — הסכם מול נפרעים: פערים, שולם ₪0, פוליסות שנעלמו · פוליסה: `policy/<מספר>.md`",
        "- [שימור](retention.md) — סימני פיגור/ביטול, קופות רדומות",
        "- [פערים והזדמנויות](crosssell.md) — כפל כיסויים, איחוד קופות, כיסוי חסר",
        "- [מה פתוח לי היום](tasks.md) — מיילים ומעקב מול חברות",
        "- [לקוחות מובילים](top.md) — הלקוחות הגדולים לפי צבירה, פרמיה ועמלה",
        f"- [שיחות](calls.md) — {len(ctx.calls)} שיחות מוקלטות · לפי נושא · מה הובטח ועוד פתוח",
        f"- [פוליסות לקוחות](policies.md) — {len(ctx.policies)} לקוחות עם תיק מהר הביטוח או פוליסה שהועלתה · לקוח: `customers/<ת.ז>/policies.md`",
        f"- [הסכמי עמלות](agreements.md) — {sum(len(v) for v in ctx.rates.values())} שיעורים ב-{len(ctx.rates)} חברות",
        "- לקוח לפי ת.ז: `customers/<ת.ז>.md` · חיפוש לפי שם: `search/<שם>.md`",
        "",
        "## מספרים",
        f"- לקוחות בהשוואה: {s.get('total_customers', 0)} · שולמו: {s.get('matched', 0)} · לא שולמו: {s.get('only_in_production', 0)} · רק בנפרעים: {s.get('only_in_commission', 0)}",
        f"- עמלות שהתקבלו: {_money(s.get('total_commission'))}",
    ]
    return "\n".join(lines)


def page_companies(ctx: MapContext) -> str:
    rows = ctx.company_rows()
    lines = ["# חברות", "", "| חברה | לקוחות | שולמו | לא שולמו | עמלה שהתקבלה | הסכם |", "|---|---|---|---|---|---|"]
    for k, r in sorted(rows.items(), key=lambda kv: -len(kv[1]["unpaid"])):
        lines.append(f"| [{ctx.names.get(k, k)}](companies/{_slug(k)}.md) | {len(r['customers'])} | {len(r['paid'])} | {len(r['unpaid'])} | "
                     f"{_money(r['received'])} | {'יש' if ctx.rates.get(k) else 'אין'} |")
    return "\n".join(lines)


def _key_from_slug(ctx: MapContext, slug: str) -> str | None:
    keys = set(ctx.company_rows()) | set(ctx.rates) | set(ctx.cases) | set(ctx.contacts)
    return next((k for k in keys if _slug(k) == slug), None)


def page_company(ctx: MapContext, slug: str) -> str:
    k = _key_from_slug(ctx, slug)
    if not k:
        return f"# לא נמצא\nאין חברה בשם `{slug}`. ראו [חברות](../companies.md)."
    r = ctx.company_rows().get(k, {"customers": set(), "paid": set(), "unpaid": set(), "products": 0, "received": 0.0})
    name = ctx.names.get(k, k)
    lines = [f"# {name}", "", "## תמונת מצב",
             f"- לקוחות בפרודוקציה: {len(r['customers'])} ({r['products']} מוצרים)",
             f"- שולמו: {len(r['paid'])} · לא שולמו: {len(r['unpaid'])} · עמלה שהתקבלה: {_money(r['received'])}"]
    rates = ctx.rates.get(k) or []
    lines.append(f"- הסכם עמלות: {len(rates)} שיעורים" if rates else "- הסכם עמלות: **אין** — הצפי משוער; כדאי לבקש הסכם")
    contact = ctx.contacts.get(k)
    lines.append(f"- איש קשר: {contact.contact_name or ''} {contact.email}" if contact else "- איש קשר: **אין מייל** — צריך להוסיף כדי לפנות לחברה")
    case = ctx.cases.get(k)
    if case:
        from app.services.collection_agent import suggestion
        nxt = suggestion(case, datetime.utcnow())
        lines += ["", "## גבייה", f"- סטטוס: {case.status} · {case.customers_count} לקוחות · צפי {_money(case.expected_total)}",
                  f"- הצעד הבא: **{nxt['text']}**"]
        if case.reply_summary:
            lines.append(f"- תשובת החברה: {case.reply_summary}")
    mails = [m for m in ctx.mails if _key(m.linked_company) == k]
    if mails:
        lines += ["", "## מיילים פתוחים"] + [f"- {m.from_name or m.from_address}: {m.summary or m.subject}" for m in mails[:10]]
    if r["unpaid"]:
        lines += ["", "## לקוחות שלא שולמו (עד 25)"]
        by_id = {c.get("id_number"): c for c in ctx.customers}
        for idn in list(r["unpaid"])[:25]:
            c = by_id.get(idn) or {}
            nm = " ".join(x for x in (c.get("first_name"), c.get("last_name")) if x) or idn
            lines.append(f"- [{nm}](../customers/{idn}.md)")
    if rates:
        lines += ["", "## שיעורי עמלה (עד 10)"] + [
            f"- {x.product or 'כללי'}: {float(x.rate) * 100:.2f}%" + (f" ({x.rate_scope})" if x.rate_scope else "") for x in rates[:10]
        ]
    lines += ["", "[← חזרה לחברות](../companies.md)"]
    return "\n".join(lines)


async def add_production_customers(db, ctx: MapContext, ids=None) -> None:
    """Customers the agent @-mentioned who are in a production file but not in
    the last comparison (the @ search reads ALL active production files) — load
    them from ClientRecord so their page exists instead of "not found"."""
    from sqlalchemy import func, or_, select
    from app.api.production import _get_production_upload_ids
    from app.models.record import ClientRecord

    have = {str(c.get("id_number")).lstrip("0") for c in ctx.customers}
    upload_ids = await _get_production_upload_ids(db, ctx.user.id)
    if not upload_ids:
        return
    cond = [ClientRecord.user_id == ctx.user.id, ClientRecord.upload_id.in_(upload_ids), ClientRecord.id_number.isnot(None)]
    if ids is not None:  # None = every production customer (load() does this)
        want = {str(i).lstrip("0") for i in ids if i and str(i).lstrip("0") not in have}
        if not want:
            return
        cond.append(or_(ClientRecord.id_number.in_(want), func.ltrim(ClientRecord.id_number, "0").in_(want)))
    recs = (await db.execute(select(ClientRecord).where(*cond))).scalars().all()
    for r in recs:
        idn = str(r.id_number).lstrip("0")
        if idn in have:
            continue
        c = ctx.extra.setdefault(idn, {
            "id_number": idn, "first_name": r.first_name, "last_name": r.last_name,
            "client_email": r.client_email, "client_phone": r.client_phone,
            "match_status": "production_only_file", "production_products": [], "commission_products": [],
        })
        c["client_email"] = c["client_email"] or r.client_email
        c["client_phone"] = c["client_phone"] or r.client_phone
        c["production_products"].append({
            "company": r.receiving_company, "product": r.product, "product_type": r.product_type,
            "policy_number": r.fund_policy_number, "status": r.product_status,
            "accumulation": float(r.accumulation) if r.accumulation else None,
            "premium": float(r.total_premium) if r.total_premium else None,
        })


def page_customer(ctx: MapContext, idn: str) -> str:
    c = next((x for x in ctx.customers if str(x.get("id_number")) == idn), None) or ctx.extra.get(idn.lstrip("0"))
    if not c:
        if ctx.policies.get(idn.lstrip("0")):   # known only from הר הביטוח / an uploaded policy
            return (f"# ת.ז {idn} — לא בפרודוקציה, אבל יש פוליסות\n\n"
                    + page_customer_policies(ctx, idn.lstrip("0")))
        return f"# לא נמצא\nאין לקוח עם ת.ז {idn} בהשוואה האחרונה."
    nm = " ".join(x for x in (c.get("first_name"), c.get("last_name")) if x) or idn
    lines = [f"# {nm} (ת.ז {idn})", f"- סטטוס: **{STATUS_HE.get(c.get('match_status'), c.get('match_status'))}**"]
    if c.get("client_email") or c.get("client_phone"):
        lines.append(f"- קשר: {c.get('client_email') or ''} {c.get('client_phone') or ''}")
    lines += ["", "## מוצרים"]
    for p in (c.get("production_products") or [])[:20]:
        k = _key(p.get("company"))
        lines.append(f"- [{p.get('company')}](../companies/{_slug(k)}.md) · {p.get('product') or p.get('product_type') or ''}"
                     f" · פוליסה {p.get('policy_number') or '—'} · סטטוס {p.get('status') or '—'}"
                     + (f" · צבירה {_money(p.get('accumulation'))}" if p.get("accumulation") else "")
                     + (f" · צפי עמלה {_money(p.get('expected_commission'))}" if p.get("expected_commission") else ""))
    lines += _unpaid_section(c)
    from app.services import agent_insights
    lines += agent_insights.nifraim_section(ctx, c)
    lines += agent_insights.portfolio_section(c)
    lines += calls_section(ctx, idn)
    pic = ctx.policies.get(idn.lstrip("0"))
    if pic:
        t = pic["totals"]
        lines += ["", "## פוליסות (הר הביטוח / PDF) — תנאים, כיסויים ומחירים שלא מופיעים בפרודוקציה",
                  f"- {t['policies']} פוליסות מהר הביטוח, {len(pic['documents'])} מסמכי פוליסה → "
                  f"[פוליסות](customers/{idn.lstrip('0')}/policies.md) · שאלה על כיסוי/מחיר/תנאים: search_policies id_number={idn.lstrip('0')}"]
        lines += [f"  - {d['title']}" for d in pic["documents"][:6] if d["status"] == "ready"]
    mails = [m for m in ctx.mails if m.linked_customer_id_number == idn]
    if mails:
        lines += ["", "## מיילים על הלקוח"] + [f"- {m.from_name or m.from_address}: {m.summary or m.subject}" for m in mails]
    return "\n".join(lines)


# ── calls (שיחות) ──

def _call_line(c, with_customer: bool = True) -> str:
    from app.services.agent.tools_calls import _row
    r = _row(c)
    who = ""
    if with_customer and r["customer"]:
        who = f" · [{r['customer']}](customers/{r['id_number']}.md)" if r["id_number"] else f" · {r['customer']}"
    bits = [r["when"][:10], r["category"] or "", r["direction"] and f"שיחה {r['direction']}" or ""]
    return (f"- {' · '.join(b for b in bits if b)}{who} — **{r['title'] or 'שיחה'}**: {r['tldr'] or ''}"
            + (f" · {r['open_tasks']} משימות פתוחות" if r["open_tasks"] else "") + f" `call:{r['call_id']}`")


def page_calls(ctx: MapContext) -> str:
    from collections import Counter
    from app.services.agent.tools_calls import promises
    from app.services.calls.categories import CATEGORIES, label
    if not ctx.calls:
        return "# שיחות\nעוד אין שיחות מוקלטות."
    by = Counter(c.category or "other" for c in ctx.calls)
    prom = promises(ctx.calls, "agent")
    late = [p for p in prom if p["overdue_days"] > 0]
    lines = [f"# שיחות ({len(ctx.calls)})", "", "## לפי נושא"]
    lines += [f"- [{label(k)}](calls/{k}.md) — {n}" for k, n in by.most_common() if k in CATEGORIES]
    lines += ["", f"## מה הבטחת ועוד פתוח ({len(prom)}, {len(late)} עבר המועד)"]
    lines += [f"- {'⚠ עבר המועד ב-' + str(p['overdue_days']) + ' ימים · ' if p['overdue_days'] else ''}"
              f"{p['customer'] or 'לקוח'}: {p['text']}" + (f" (עד {p['due']})" if p.get("due") else "")
              + f" `call:{p['call_id']} task:{p['task_index']}`" for p in prom[:15]] or ["- אין"]
    lines += ["", "## אחרונות"] + [_call_line(c) for c in ctx.calls[:10]]
    lines += ["", "חיפוש בתוך התמלולים: search_calls · שיחה מלאה: get_call"]
    return "\n".join(lines)


def page_calls_category(ctx: MapContext, key: str) -> str:
    from app.services.calls.categories import CATEGORIES, label
    if key not in CATEGORIES:
        return f"# לא נמצא\nאין נושא `{key}`. ראו [שיחות](../calls.md)."
    rows = [c for c in ctx.calls if (c.category or "other") == key]
    lines = [f"# שיחות — {label(key)} ({len(rows)})", "[כל השיחות](../calls.md)", ""]
    return "\n".join(lines + ([_call_line(c).replace("(customers/", "(../customers/") for c in rows[:40]] or ["אין שיחות בנושא הזה."]))


def calls_section(ctx: MapContext, idn: str) -> list[str]:
    """The customer's calls on their page: what was said and what is still open."""
    mine = [c for c in ctx.calls if (c.id_number or ((c.insights or {}).get("customer") or {}).get("id_number") or "").lstrip("0") == idn.lstrip("0")]
    if not mine:
        return []
    out = ["", f"## שיחות ({len(mine)})"]
    for c in mine[:8]:
        out.append(_call_line(c, with_customer=False))
        ins = c.insights or {}
        for q in (ins.get("customer_quotes") or [])[:2]:
            out.append(f"  - הלקוח: «{q}»")
        for a in ins.get("action_items") or []:
            if not a.get("done"):
                out.append(f"  - פתוח ({'סוכן' if a.get('owner') == 'agent' else 'לקוח'}): {a.get('text')}" + (f" — עד {a['due']}" if a.get("due") else ""))
    return out


def _unpaid_section(c: dict) -> list[str]:
    """Said outright: every product of this customer that received NO commission — no
    נפרעים line, or a line that paid ₪0 — whatever its size or status (QA 2026-10-08:
    the agent hid רונן חיראק's inactive Harel gemel and שרה אשר's ₪10 as "negligible").
    The comparison already narrowed an unpaid customer's `production_products` to exactly
    those products, per product, so this lists them as they are."""
    if c.get("match_status") != "only_production":
        return []
    rows = []
    for p in c.get("production_products") or []:
        exp = float(p.get("expected_commission") or 0)
        bits = [p.get("company") or p.get("company_full") or "", p.get("product") or p.get("product_type") or ""]
        if p.get("policy_number"):
            bits.append(f"פוליסה {p['policy_number']}")
        if p.get("status"):
            bits.append(p["status"])
        bits.append(f"צפי {_money(exp)}" if exp >= 1 else (f"צפי ₪{exp:,.2f}" if exp > 0 else "צפי: נתון חסר (אין אחוז בהסכם)"))
        rows.append((exp, "- " + " · ".join(b for b in bits if b) + " — לא התקבלה עמלה"))
    if not rows:
        return []
    return ["", "## לא שולם (המוצרים שלא התקבלה עליהם עמלה — כולם, גם סכום קטן וגם קופה לא פעילה)"] + [
        r for _, r in sorted(rows, key=lambda x: -x[0])]


def page_top(ctx: MapContext) -> str:
    """The biggest customers — "הלקוח הכי גדול" has three honest meanings, so
    rank all three: accumulation (צבירה), premium, commission received."""
    rows = []
    for c in [*ctx.customers, *ctx.extra.values()]:
        prods = c.get("production_products") or []
        acc = sum(float(p.get("accumulation") or 0) for p in prods)
        prem = sum(float(p.get("premium") or 0) for p in prods)
        exp = sum(float(p.get("expected_commission") or 0) for p in prods)
        paid = float(c.get("total_commission") or 0)
        nm = " ".join(x for x in (c.get("first_name"), c.get("last_name")) if x) or str(c.get("id_number"))
        rows.append((nm, str(c.get("id_number")), acc, prem, exp, paid, len(prods)))

    def block(title, idx):
        top = [r for r in sorted(rows, key=lambda r: -r[idx]) if r[idx] > 0][:12]
        out = ["", f"## {title}"]
        out += [f"{i}. [{r[0]}](customers/{r[1]}.md) · {_money(r[idx])} · {r[6]} מוצרים"
                + (f" · צבירה {_money(r[2])}" if idx != 2 and r[2] else "")
                + (f" · צפי עמלה {_money(r[4])}" if r[4] else "") for i, r in enumerate(top, 1)]
        return out if top else out + ["אין נתונים."]

    lines = ["# לקוחות מובילים", "הלקוח \"הכי גדול\" לפי צבירה, לפי פרמיה ולפי עמלה שהתקבלה."]
    lines += block("לפי צבירה", 2) + block("לפי פרמיה חודשית", 3) + block("לפי עמלה שהתקבלה", 5)
    return "\n".join(lines)


def page_unpaid(ctx: MapContext) -> str:
    lines = ["# לא שולם", ""]
    for k, c in sorted(ctx.cases.items(), key=lambda kv: -kv[1].expected_total):
        if c.status == "resolved":
            continue
        from app.services.collection_agent import suggestion
        lines.append(f"- [{c.company_name}](companies/{_slug(k)}.md): {c.customers_count} לקוחות · צפי {_money(c.expected_total)}"
                     f" · {suggestion(c, datetime.utcnow())['text']}")
    if len(lines) == 2:
        lines.append("אין כרגע חברות בטיפול גבייה.")
    return "\n".join(lines)


def page_mail(ctx: MapContext) -> str:
    lines = ["# מיילים פתוחים", ""]
    for m in ctx.mails:
        links = []
        if m.linked_company:
            links.append(f"[{m.linked_company}](companies/{_slug(_key(m.linked_company))}.md)")
        if m.linked_customer_id_number:
            links.append(f"[לקוח](customers/{m.linked_customer_id_number}.md)")
        draft = " · יש טיוטה" if m.draft_body else ""
        lines.append(f"- {m.from_name or m.from_address} <{m.from_address}> ({m.category or 'מייל'}): {m.summary or m.subject}{draft} {' '.join(links)}")
    if len(lines) == 2:
        lines.append("אין מיילים פתוחים.")
    return "\n".join(lines)


def page_agreements(ctx: MapContext) -> str:
    lines = ["# הסכמי עמלות", ""]
    rows = ctx.company_rows()
    for k in sorted(set(ctx.rates) | set(rows)):
        n = len(ctx.rates.get(k) or [])
        lines.append(f"- [{ctx.names.get(k, k)}](companies/{_slug(k)}.md): " + (f"{n} שיעורים" if n else "**אין הסכם**"))
    return "\n".join(lines)


def page_search(ctx: MapContext, text: str) -> str:
    """Find by NAME (the agent rarely knows the ID): customers + open mails."""
    t = (text or "").strip()
    lines = [f"# חיפוש: {t}", ""]
    hits = []
    # a customer you spoke with lately is the likely one ("מה הצעד הבא מול חיים?" — 6 people named חיים)
    spoke: dict = {}
    for cr in ctx.calls:
        idn = (cr.id_number or ((cr.insights or {}).get("customer") or {}).get("id_number") or "").lstrip("0")
        if idn and idn not in spoke and cr.created_at:
            spoke[idn] = cr.created_at.strftime("%d/%m")
    found = []
    for c in [*ctx.customers, *ctx.extra.values()]:
        nm = " ".join(x for x in (c.get("first_name"), c.get("last_name")) if x)
        rev = " ".join(x for x in (c.get("last_name"), c.get("first_name")) if x)
        toks = t.split()
        # word match, any order: "גורן גורן" finds "גיא גורן" (the same person, stored differently per file)
        if t and (t in nm or t in rev or t == str(c.get("id_number"))
                  or (len(toks) >= 2 and all(x in nm.split() for x in toks))
                  or (len(toks) >= 2 and len(set(toks)) == 1 and toks[0] in nm.split())):
            when = spoke.get(str(c.get("id_number")).lstrip("0"))
            found.append((0 if when else 1, f"- לקוח: [{nm}](customers/{c.get('id_number')}.md) · {STATUS_HE.get(c.get('match_status'), '')}"
                                            + (f" · **דיברת איתו בשיחה ב-{when}**" if when else "")))
    hits += [h for _, h in sorted(found, key=lambda x: x[0])]
    for m in ctx.mails:
        if t and (t in (m.from_name or "") or t in (m.summary or "") or t in (m.subject or "")):
            draft = " · יש טיוטה" if m.draft_body else ""
            hits.append(f"- מייל מ{m.from_name or m.from_address} <{m.from_address}>: {m.summary or m.subject}{draft}")
            if m.draft_body:
                hits.append("  טיוטת התשובה שהוכנה: " + " ".join(m.draft_body.split())[:700])
    lines += hits[:30] or ["לא נמצא לקוח או מייל בשם הזה."]
    return "\n".join(lines)


def page_policies(ctx: MapContext) -> str:
    lines = ["# פוליסות לקוחות", "מקור: הר הביטוח (כל החברות, לא רק של הסוכן) ופוליסות PDF שהועלו.", "",
             "| לקוח | פוליסות | בתוקף | חברות | פרמיה חודשית בתוקף | מסמכים |", "|---|---|---|---|---|---|"]
    for idn, p in ctx.policies.items():
        t = p["totals"]
        lines.append(f"| [{p.get('customer_name') or idn}](customers/{idn}/policies.md) | {t['policies']} | {t['active_policies']} | "
                     f"{', '.join(t['companies'][:5])} | {_money(t['monthly_premium_active']) if t['monthly_premium_active'] else ''} | "
                     f"{len(p['documents'])} |")
    if not ctx.policies:
        lines.append("עוד אין פוליסות. אפשר לשלוף מהר הביטוח (ת.ז + תאריך לידה + תאריך הנפקה) או להעלות PDF בכרטיס הלקוח.")
    return "\n".join(lines)


def page_customer_policies(ctx: MapContext, idn: str) -> str:
    p = ctx.policies.get(idn)
    if not p:
        return (f"# אין פוליסות ללקוח {idn}\nעוד לא נשלף מהר הביטוח ולא הועלתה פוליסה. "
                "אפשר להציע שליפה מהר הביטוח (צריך ת.ז, תאריך לידה ותאריך הנפקת ת.ז).")
    t = p["totals"]
    fetched = p["fetched_at"].strftime("%d/%m/%Y") if p.get("fetched_at") else None
    lines = [f"# הפוליסות של {p.get('customer_name') or idn} (ת.ז {idn})",
             f"- {t['policies']} פוליסות ({t['coverages']} כיסויים), {t['active_policies']} בתוקף · חברות: {', '.join(t['companies'])}"]
    if fetched:
        lines.append(f"- נשלף מהר הביטוח: {fetched}")
    if t["monthly_premium_active"]:
        lines.append(f"- פרמיה חודשית משוערת לכיסויים בתוקף: {_money(t['monthly_premium_active'])} (שנתית חולקה ל-12)")
    ch = p.get("changes")
    if ch:
        from app.services.policies.store import changes_md
        prev = next((h["fetched_at"] for h in p.get("history", [])[1:2]), None)
        lines += [""] + changes_md(ch, prev).strip().splitlines()
    if len(p.get("history") or []) > 1:
        lines += ["", "## שליפות קודמות"] + [
            f"- {h['fetched_at'].strftime('%d/%m/%Y')}: {h['coverages'] or 0} כיסויים"
            + (f" · {h['changes']}" if h.get("changes") else "") + ("" if h["current"] else f" · document_id `{h['document_id']}`")
            for h in p["history"][:10] if h.get("fetched_at")]
    from app.services.policies.markdown import _money as _pmoney

    def head(pol):
        return (f"**{pol['branch'] or ''} — {' + '.join(pol['sub_branches'])}** · {pol['company_short']}"
                + (f" · פוליסה {pol['policy_number']}" if pol["policy_number"] else "")
                + (f" · {pol['period']}" if pol["period"] else ""))

    # active first and complete (an answer reads from the top; a cut must never drop a live policy)
    active = [x for x in p["policies"] if x["active"]]
    ended = [x for x in p["policies"] if not x["active"]]
    lines += ["", f"## בתוקף ({len(active)})"]
    for pol in active:
        lines.append(f"- {head(pol)} · תחום {pol['domain'] or 'אחר'}"
                     + (f" · ₪{pol['monthly_premium']:,.2f}/חודש" if pol["monthly_premium"] else ""))
        many = len(pol["sub_branches"]) > 1
        for c in pol["coverages"][:10]:
            prem = f"{_pmoney(c['premium'])} {c['premium_type'] or ''}".strip() if c["premium"] else ""
            lines.append(f"  - {c['product'] or ''}{' · ' + c['sub_branch'] if many and c['sub_branch'] else ''}"
                         + (f" · {c['period']}" if many and c["period"] != pol["period"] else "")
                         + (f" · {prem}" if prem else ""))
    if ended:
        lines += ["", f"## הסתיימו ({len(ended)})"] + [f"- {head(pol)}" for pol in ended]
    if p["documents"]:
        lines += ["", "## מסמכי פוליסה (לפרטים: get_policy_document עם document_id)"]
        for d in p["documents"]:
            src = {"harb_portfolio": "הר הביטוח", "harb_policy": "הר הביטוח — פרטי פוליסה", "pdf": "PDF"}.get(d["source"], d["source"])
            lines.append(f"- {d['title']} · {src}" + (f" · {d['company']}" if d.get("company") else "")
                         + ("" if d["status"] == "ready" else f" · {d['status']}") + f" · document_id `{d['id']}`")
    return "\n".join(lines)


def render(ctx: MapContext, path: str) -> str:
    path = (path or "index.md").strip().lstrip("./").removeprefix("../")
    if path in ("", "index.md"):
        return page_index(ctx)
    if path == "companies.md":
        return page_companies(ctx)
    from app.services import agent_insights
    if path == "reconcile.md":
        return agent_insights.page_reconcile(ctx)
    if path == "retention.md":
        return agent_insights.page_retention(ctx)
    if path == "crosssell.md":
        return agent_insights.page_crosssell(ctx)
    if path == "tasks.md":
        return agent_insights.page_tasks(ctx)
    if path.startswith("policy/"):
        return agent_insights.page_policy(ctx, path[len("policy/"):].removesuffix(".md"))
    if path == "top.md":
        return page_top(ctx)
    if path == "unpaid.md":
        return page_unpaid(ctx)
    if path == "mail.md":
        return page_mail(ctx)
    if path == "agreements.md":
        return page_agreements(ctx)
    if path == "calls.md":
        return page_calls(ctx)
    m = re.fullmatch(r"calls/(\w+)\.md", path)
    if m:
        return page_calls_category(ctx, m.group(1))
    m = re.fullmatch(r"companies/(.+)\.md", path)
    if m:
        return page_company(ctx, m.group(1))
    m = re.fullmatch(r"search/(.+?)(\.md)?", path)
    if m:
        return page_search(ctx, m.group(1))
    if path == "policies.md":
        return page_policies(ctx)
    m = re.fullmatch(r"customers/(\d+)/policies\.md", path)
    if m:
        return page_customer_policies(ctx, m.group(1).lstrip("0") or "0")
    m = re.fullmatch(r"customers/(\d+)\.md", path)
    if m:
        return page_customer(ctx, m.group(1).lstrip("0") or "0")
    return f"# לא נמצא\nאין דף `{path}`. התחילו מ-[index](index.md)."
