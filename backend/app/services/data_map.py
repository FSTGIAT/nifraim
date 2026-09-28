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
    ctx.mails = (await db.execute(
        select(MailItem).where(MailItem.user_id == user.id, MailItem.status.in_(OPEN_STATUSES))
        .order_by(MailItem.received_at.desc()).limit(40)
    )).scalars().all()
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
        "- [לקוחות מובילים](top.md) — הלקוחות הגדולים לפי צבירה, פרמיה ועמלה",
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


async def add_production_customers(db, ctx: MapContext, ids) -> None:
    """Customers the agent @-mentioned who are in a production file but not in
    the last comparison (the @ search reads ALL active production files) — load
    them from ClientRecord so their page exists instead of "not found"."""
    from sqlalchemy import func, or_, select
    from app.api.production import _get_production_upload_ids
    from app.models.record import ClientRecord

    have = {str(c.get("id_number")).lstrip("0") for c in ctx.customers}
    want = {str(i).lstrip("0") for i in ids if i and str(i).lstrip("0") not in have}
    upload_ids = await _get_production_upload_ids(db, ctx.user.id) if want else []
    if not want or not upload_ids:
        return
    recs = (await db.execute(select(ClientRecord).where(
        ClientRecord.user_id == ctx.user.id, ClientRecord.upload_id.in_(upload_ids),
        or_(ClientRecord.id_number.in_(want), func.ltrim(ClientRecord.id_number, "0").in_(want)),
    ))).scalars().all()
    for r in recs:
        idn = str(r.id_number).lstrip("0")
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
    if c.get("commission_products"):
        lines += ["", "## עמלות שהתקבלו"] + [
            f"- {p.get('company') or p.get('receiving_company')}: {_money(p.get('commission') or p.get('commission_paid'))}"
            for p in c["commission_products"][:10]
        ]
    mails = [m for m in ctx.mails if m.linked_customer_id_number == idn]
    if mails:
        lines += ["", "## מיילים על הלקוח"] + [f"- {m.from_name or m.from_address}: {m.summary or m.subject}" for m in mails]
    return "\n".join(lines)


def page_top(ctx: MapContext) -> str:
    """The biggest customers — "הלקוח הכי גדול" has three honest meanings, so
    rank all three: accumulation (צבירה), premium, commission received."""
    rows = []
    for c in ctx.customers:
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
    for c in ctx.customers:
        nm = " ".join(x for x in (c.get("first_name"), c.get("last_name")) if x)
        rev = " ".join(x for x in (c.get("last_name"), c.get("first_name")) if x)
        if t and (t in nm or t in rev or t == str(c.get("id_number"))):
            hits.append(f"- לקוח: [{nm}](customers/{c.get('id_number')}.md) · {STATUS_HE.get(c.get('match_status'), '')}")
    for m in ctx.mails:
        if t and (t in (m.from_name or "") or t in (m.summary or "") or t in (m.subject or "")):
            draft = " · יש טיוטה" if m.draft_body else ""
            hits.append(f"- מייל מ{m.from_name or m.from_address} <{m.from_address}>: {m.summary or m.subject}{draft}")
            if m.draft_body:
                hits.append("  טיוטת התשובה שהוכנה: " + " ".join(m.draft_body.split())[:700])
    lines += hits[:30] or ["לא נמצא לקוח או מייל בשם הזה."]
    return "\n".join(lines)


def render(ctx: MapContext, path: str) -> str:
    path = (path or "index.md").strip().lstrip("./").removeprefix("../")
    if path in ("", "index.md"):
        return page_index(ctx)
    if path == "companies.md":
        return page_companies(ctx)
    if path == "top.md":
        return page_top(ctx)
    if path == "unpaid.md":
        return page_unpaid(ctx)
    if path == "mail.md":
        return page_mail(ctx)
    if path == "agreements.md":
        return page_agreements(ctx)
    m = re.fullmatch(r"companies/(.+)\.md", path)
    if m:
        return page_company(ctx, m.group(1))
    m = re.fullmatch(r"search/(.+?)(\.md)?", path)
    if m:
        return page_search(ctx, m.group(1))
    m = re.fullmatch(r"customers/(\d+)\.md", path)
    if m:
        return page_customer(ctx, m.group(1).lstrip("0") or "0")
    return f"# לא נמצא\nאין דף `{path}`. התחילו מ-[index](index.md)."
