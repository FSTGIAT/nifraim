"""Nifra Agent's analyses — data-map pages COMPUTED here, only narrated by the
model (so it can't invent). One page per job the agents asked for (2026-09-29):

    reconcile.md   commission reconciliation — expected vs paid per company,
                   policies paid ₪0 / below the agreement, active policies with
                   no נפרעים line
    retention.md   arrears / cancellation SIGNALS — active policy, nothing paid
                   this period; inactive funds with a balance
    crosssell.md   portfolio gaps / overlaps across the book (rule-based)
    tasks.md       what is open today — mails, insurer follow-ups
    policy/<n>.md  "did I get paid on policy X?"

Everything is limited to what the agent's own files show: a customer may hold
products with another agent, and there is no market data, no policy end dates
and no birth dates — those questions get an honest "not in the data".
"""
from __future__ import annotations

import re
from datetime import datetime

INACTIVE = ("לא פעיל", "מוקפא", "סילוק", "תום תקופה")
DUP_TYPES = ("ביטוח בריאות", "ביטוח סיעודי", "קרן פנסיה חדשה מקיפה")   # two active = likely overlap
MERGE_TYPES = ("קרן השתלמות", "קופת גמל לתגמולים ופיצויים")           # two active = consolidation talk
LIFE_TYPES = ("ביטוח חיים", "ביטוח מנהלים", "מנהלים חיסכון טהור")


def suspicious(paid: float, exp: float) -> bool:
    """An expected commission that dwarfs the payment is more likely a bad
    expected calc (e.g. a pension rate applied to the balance) than a debt."""
    return exp > 5000 and exp > 50 * max(paid, 1)


def _m(v) -> str:
    try:
        return f"₪{round(float(v)):,}"
    except (TypeError, ValueError):
        return "₪0"


def _f(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _name(c: dict) -> str:
    return " ".join(x for x in (c.get("first_name"), c.get("last_name")) if x) or str(c.get("id_number"))


def _active(p: dict) -> bool:
    st = (p.get("status") or "").strip()
    return not any(st.startswith(x) for x in INACTIVE)


def _all(ctx) -> list[dict]:
    return [*ctx.customers, *ctx.extra.values()]


def reporting_companies(ctx) -> dict[str, str]:
    """key -> display name, for insurers that sent a נפרעים file this period."""
    from app.services.data_map import _key
    out = {}
    for c in ctx.customers:
        for p in c.get("commission_products") or []:
            n = p.get("company") or p.get("company_full")
            if n:
                out.setdefault(_key(n), n)
    return out


# ─────────────────────────── per customer ───────────────────────────────

def nifraim_section(ctx, c: dict) -> list[str]:
    """What the insurers actually paid on this customer, line by line — ₪0 shown as ₪0."""
    from app.services.data_map import _key
    lines = []
    cps = c.get("commission_products") or []
    if cps:
        lines += ["", "## נפרעים (מה שהחברות שילמו בפועל)"]
        for p in cps[:15]:
            paid, exp = _f(p.get("commission")), _f(p.get("expected_commission"))
            bits = [p.get("company") or p.get("company_full") or "", p.get("product") or ""]
            if p.get("account"):
                bits.append(f"חשבון {p['account']}")
            bits.append(f"שולם {_m(paid)}")
            if exp:
                bits.append(f"צפי {_m(exp)}" + (" (משוער)" if p.get("expected_is_estimate") else ""))
                if suspicious(paid, exp):
                    bits.append("צפי חשוד (כנראה חישוב שגוי)")
                elif exp - paid > 1:
                    bits.append(f"**חסר {_m(exp - paid)}**")
            if p.get("rate"):
                bits.append(f"שיעור {_f(p['rate']) * 100:.2f}%")
            lines.append("- " + " · ".join(b for b in bits if b))
    reporting = reporting_companies(ctx)
    missing = sorted({p.get("company") for p in (c.get("production_products") or [])
                      if p.get("company") and _key(p.get("company")) not in reporting})
    if missing:
        lines += ["", "אין דוח נפרעים לתקופה מ: " + ", ".join(missing) + " — לכן אין נתוני תשלום על המוצרים שם."]
    return lines


def portfolio_section(c: dict) -> list[str]:
    """Rule-based portfolio picture: overlaps, consolidation, gaps — only what the files show."""
    prods = c.get("production_products") or []
    if not prods:
        return []
    active = [p for p in prods if _active(p)]
    types: dict[str, set] = {}
    for p in active:
        types.setdefault(p.get("product_type") or "", set()).add(p.get("company") or "")
    items = []
    for t in DUP_TYPES:
        n = sum(1 for p in active if p.get("product_type") == t)
        if n >= 2:
            items.append(f"כפל אפשרי: {n} × {t} פעילים ({', '.join(sorted(types.get(t, [])))}) — לבדוק חפיפת כיסויים")
    for t in MERGE_TYPES:
        n = sum(1 for p in active if p.get("product_type") == t)
        if n >= 2:
            items.append(f"איחוד אפשרי: {n} × {t} פעילות — פחות דמי ניהול ומעקב פשוט יותר")
    for p in prods:
        if not _active(p) and _f(p.get("accumulation")) > 0:
            items.append(f"קופה לא פעילה עם צבירה: {p.get('product') or p.get('product_type')} ב{p.get('company')} · {_m(p.get('accumulation'))} — איחוד/ניוד")
    has = set(types)
    savings = any(("גמל" in t or "השתלמות" in t or "פנסיה" in t) for t in has)
    if savings and "ביטוח בריאות" not in has:
        items.append("אין ביטוח בריאות בתיק שלך — הזדמנות להציע")
    if savings and not (has & set(LIFE_TYPES)) and not any("פנסיה" in t for t in has):
        items.append("אין ביטוח חיים/ריסק ואין קרן פנסיה בתיק שלך — לבדוק כיסוי למקרה מוות")
    if has and not savings:
        items.append("יש לו ביטוח אצלך אבל אין חיסכון פנסיוני בתיק שלך — הזדמנות לגמל/השתלמות/פנסיה")
    if not items:
        return ["", "## תמונת תיק", "- לא נמצאו כפלים או פערים בולטים במוצרים שבתיק שלך."]
    return ["", "## תמונת תיק (רק מה שבתיק שלך — ייתכנו מוצרים אצל סוכן אחר)"] + [f"- {x}" for x in items[:8]]


def _opportunities(c: dict) -> list[str]:
    return [x[2:] for x in portfolio_section(c) if x.startswith("- ") and not x.startswith("- לא נמצאו")]


# ─────────────────────────── book-level pages ───────────────────────────

def page_reconcile(ctx) -> str:
    """Commission reconciliation: expected vs paid per reporting insurer."""
    from app.services.data_map import _key, _slug
    per: dict[str, dict] = {}
    under: list[tuple] = []
    sus: list[tuple] = []
    for c in ctx.customers:
        for p in c.get("commission_products") or []:
            n = p.get("company") or p.get("company_full") or "?"
            r = per.setdefault(_key(n), {"name": n, "paid": 0.0, "exp": 0.0, "lines": 0, "zero": 0, "under": 0, "sus": 0, "sus_exp": 0.0})
            paid, exp = _f(p.get("commission")), _f(p.get("expected_commission"))
            r["paid"] += paid
            r["exp"] += exp
            r["lines"] += 1
            if exp > 1 and paid <= 0:
                r["zero"] += 1
            if suspicious(paid, exp):
                r["sus"] += 1
                r["sus_exp"] += exp
                sus.append((exp, c, p, paid))
                r["exp"] -= exp  # keep it out of the gap total
            elif exp > 1 and exp - paid > max(1, exp * 0.1):
                r["under"] += 1
                under.append((exp - paid, c, p, paid, exp))
    reporting = reporting_companies(ctx)
    missing_line: dict[str, list] = {}
    for c in ctx.customers:
        if c.get("match_status") != "only_production":
            continue
        for p in c.get("production_products") or []:
            k = _key(p.get("company"))
            if k in reporting and _active(p):
                missing_line.setdefault(k, []).append((c, p))

    lines = ["# התאמת עמלות — הסכם מול נפרעים",
             f"תקופה: {ctx.period_label or '—'}. צפי = לפי הסכמי העמלות ששמורים במערכת (\"משוער\" כשאין הסכם).", "",
             "## לפי חברה"]
    for k, r in sorted(per.items(), key=lambda kv: -(kv[1]["exp"] - kv[1]["paid"])):
        gap = r["exp"] - r["paid"]
        lines.append(f"- [{r['name']}](companies/{_slug(k)}.md): שולם {_m(r['paid'])} מול צפי {_m(r['exp'])}"
                     + (f" · **פער {_m(gap)}**" if gap > 1 else "")
                     + f" · {r['lines']} שורות · {r['zero']} שולמו ₪0 · {r['under']} מתחת להסכם"
                     + (f" · {len(missing_line.get(k, []))} פוליסות פעילות בלי שורת נפרעים" if missing_line.get(k) else ""))
        if r["sus"]:
            lines.append(f"  - לא נכלל בפער: {r['sus']} שורות עם צפי חשוד ({_m(r['sus_exp'])}) — ראו למטה")
    if not per:
        lines.append("אין עדיין דוחות נפרעים בהשוואה.")
    no_report = sorted({p.get("company") for c in _all(ctx) for p in c.get("production_products") or []
                        if p.get("company") and _key(p.get("company")) not in reporting})
    if no_report:
        lines += ["", "## חברות שלא שלחו נפרעים לתקופה", "- " + ", ".join(no_report[:20])]
    if under:
        lines += ["", "## הפערים הגדולים (שולם פחות מהצפי, עד 15)"]
        for gap, c, p, paid, exp in sorted(under, key=lambda x: -x[0])[:15]:
            lines.append(f"- [{_name(c)}](customers/{c.get('id_number')}.md) · {p.get('company')} · {p.get('product') or ''}"
                         f" · חשבון {p.get('account') or '—'} · שולם {_m(paid)} מול {_m(exp)} · חסר {_m(gap)}")
    if sus:
        lines += ["", "## צפי חשוד — כנראה חישוב שגוי, לא חוב (לבדוק את ההסכם/המוצר)"]
        for exp, c, p, paid in sorted(sus, key=lambda x: -x[0])[:10]:
            lines.append(f"- [{_name(c)}](customers/{c.get('id_number')}.md) · {p.get('company')} · {p.get('product') or ''}"
                         f" · חשבון {p.get('account') or '—'} · שולם {_m(paid)} מול צפי {_m(exp)}")
    if missing_line:
        lines += ["", "## פוליסות פעילות בלי שורת נפרעים (נעלמו מהדוח?) — ראו גם [לא שולם](unpaid.md)"]
        for k, rows in missing_line.items():
            exp = sum(_f(p.get("expected_commission")) for _, p in rows)
            lines.append(f"- {reporting.get(k, k)}: {len(rows)} פוליסות · צפי {_m(exp)}")
    return "\n".join(lines)


def page_retention(ctx) -> str:
    """Arrears / churn SIGNALS — not verdicts."""
    from app.services.data_map import _key
    reporting = reporting_companies(ctx)
    arrears, dormant, all_off = [], [], []
    for c in _all(ctx):
        prods = c.get("production_products") or []
        if c.get("match_status") == "only_production":
            act = [p for p in prods if _active(p) and _key(p.get("company")) in reporting]
            if act:
                arrears.append((sum(_f(p.get("premium")) + _f(p.get("expected_commission")) for p in act), c, act))
        for p in prods:
            if not _active(p) and _f(p.get("accumulation")) > 0:
                dormant.append((_f(p.get("accumulation")), c, p))
        if prods and not any(_active(p) for p in prods):
            all_off.append(c)
    lines = ["# שימור — סימנים לפיגור, ביטול ונטישה",
             "אלה **סימנים** מהנתונים, לא קביעה: כדאי לאמת מול הלקוח/החברה.",
             "אין בקבצים תאריכי סיום פוליסה או תאריכי לידה — לכן אין כאן התראות חידוש או מעבר גיל.", "",
             f"## פעיל בפרודוקציה אבל לא שולמה עליו עמלה בתקופה — חשד לפיגור/ביטול ({len(arrears)} לקוחות, עד 20)"]
    for _, c, act in sorted(arrears, key=lambda x: -x[0])[:20]:
        p = act[0]
        lines.append(f"- [{_name(c)}](customers/{c.get('id_number')}.md) · {p.get('company')} · {p.get('product') or p.get('product_type')}"
                     + (f" · פרמיה {_m(p.get('premium'))}" if _f(p.get("premium")) else "")
                     + (f" · +{len(act) - 1} מוצרים" if len(act) > 1 else ""))
    lines += ["", f"## קופות לא פעילות עם צבירה — סכנת ניוד החוצה / הזדמנות איחוד ({len(dormant)}, עד 20)"]
    for acc, c, p in sorted(dormant, key=lambda x: -x[0])[:20]:
        lines.append(f"- [{_name(c)}](customers/{c.get('id_number')}.md) · {p.get('company')} · {p.get('product') or p.get('product_type')} · {_m(acc)}")
    lines += ["", f"## לקוחות שכל המוצרים שלהם לא פעילים ({len(all_off)}, עד 15)"]
    lines += [f"- [{_name(c)}](customers/{c.get('id_number')}.md)" for c in all_off[:15]] or ["- אין."]
    return "\n".join(lines)


def page_crosssell(ctx) -> str:
    rows = []
    for c in _all(ctx):
        ops = _opportunities(c)
        if ops:
            prods = c.get("production_products") or []
            acc = sum(_f(p.get("accumulation")) for p in prods)
            dormant = sum(_f(p.get("accumulation")) for p in prods if not _active(p))
            strong = any(o.startswith(("כפל", "איחוד")) for o in ops)
            # money first: dormant balances, then consolidation/overlap on big books; coverage gaps only break ties
            ops.sort(key=lambda o: 0 if o.startswith(("קופה לא פעילה", "איחוד", "כפל")) else 1)
            rows.append((dormant + (acc * 0.5 if strong else 0) + len(ops), c, ops, acc))
    lines = ["# פערים והזדמנויות בתיק (Cross-sell)",
             "לפי כללים על המוצרים שבתיק שלך בלבד: כפל כיסויים, איחוד קופות, קופות רדומות, כיסוי חסר.", "",
             f"## לקוחות עם הכי הרבה הזדמנויות ({len(rows)}, עד 20)"]
    for _, c, ops, acc in sorted(rows, key=lambda x: -x[0])[:20]:
        lines.append(f"- [{_name(c)}](customers/{c.get('id_number')}.md)" + (f" · צבירה {_m(acc)}" if acc else "") + f" · {ops[0]}"
                     + (f" (+{len(ops) - 1})" if len(ops) > 1 else ""))
    counts: dict[str, int] = {}
    for _, _c, ops, _a in rows:
        for o in ops:
            counts[o.split(":")[0].split(" — ")[0]] = counts.get(o.split(":")[0].split(" — ")[0], 0) + 1
    if counts:
        lines += ["", "## לפי סוג"] + [f"- {k}: {v} לקוחות" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])]
    return "\n".join(lines)


def page_tasks(ctx) -> str:
    from app.services.collection_agent import suggestion
    now = datetime.utcnow()
    lines = ["# מה פתוח לי היום", ""]
    if ctx.mails:
        lines.append(f"## מיילים שמחכים לך ({len(ctx.mails)})")
        for m in ctx.mails[:15]:
            act = f" → {m.suggested_action}" if getattr(m, "suggested_action", None) else ""
            draft = " · יש טיוטה מוכנה" if m.draft_body else ""
            lines.append(f"- {m.from_name or m.from_address} <{m.from_address}>: {m.summary or m.subject}{draft}{act}")
    open_cases = [c for c in ctx.cases.values() if c.status != "resolved"]
    if open_cases:
        lines += ["", f"## מעקב מול חברות ({len(open_cases)})"]
        for c in open_cases:
            nxt = suggestion(c, now)
            lines.append(f"- {c.company_name}: {c.customers_count} לקוחות · צפי {_m(c.expected_total)} · הצעד הבא: **{nxt['text']}**")
    if len(lines) == 2:
        lines.append("אין משימות פתוחות.")
    lines += ["", "תזכורת למעקב: אפשר לבקש ממני \"תזכיר לי…\" ואשים ביומן."]
    return "\n".join(lines)


def page_policy(ctx, num: str) -> str:
    """"Did I get paid on policy X?" — look the number up on both sides."""
    want = re.sub(r"\D", "", num or "").lstrip("0")
    if not want:
        return "# פוליסה\nצריך מספר פוליסה/חשבון."
    hits, paid_amounts = [], []
    for c in _all(ctx):
        for p in c.get("production_products") or []:
            if re.sub(r"\D", "", str(p.get("policy_number") or "")).lstrip("0") == want:
                hits.append(f"- פרודוקציה: [{_name(c)}](customers/{c.get('id_number')}.md) · {p.get('company')} · "
                            f"{p.get('product') or p.get('product_type')} · סטטוס {p.get('status') or '—'}"
                            + (f" · צפי עמלה {_m(p.get('expected_commission'))}" if p.get("expected_commission") else ""))
        for p in c.get("commission_products") or []:
            if re.sub(r"\D", "", str(p.get("account") or "")).lstrip("0") == want:
                paid_amounts.append(_f(p.get("commission")))
                hits.append(f"- נפרעים: [{_name(c)}](customers/{c.get('id_number')}.md) · {p.get('company')} · "
                            f"שולם {_m(p.get('commission'))}" + (f" מול צפי {_m(p.get('expected_commission'))}" if p.get("expected_commission") else ""))
    if not hits:
        return f"# פוליסה {num}\nלא נמצאה בפרודוקציה או בנפרעים של התקופה."
    if paid_amounts:
        verdict = ("**התקבלה עמלה בנפרעים של התקופה.**" if max(paid_amounts) > 0
                   else "**יש שורת נפרעים לפוליסה, אבל שולם עליה ₪0 בתקופה — כדאי לברר מול החברה.**")
    else:
        verdict = "**אין שורת נפרעים לפוליסה הזו בתקופה — לא התקבלה עליה עמלה.**"
    return "\n".join([f"# פוליסה {num}", "", *hits, "", verdict])
