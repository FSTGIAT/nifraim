"""Policies → Markdown, the form the AI reads, embeds and links (no LLM for הר הביטוח data).

portfolio_md: one document per customer fetch — headline, then per domain (תחום) one section
per POLICY (coverages that share a מספר פוליסה + company sit under one heading: a car policy is
פוליסת ביטוח + שמשות + גרירה + רכב חלופי). Each policy section is self-contained (customer, company,
policy number repeated in its heading) so an embedded chunk still says whose and which policy it is.
"""
from __future__ import annotations

from collections import OrderedDict
from datetime import date


def _d(v: date | None) -> str:
    return v.strftime("%d/%m/%Y") if v else ""


def _money(v) -> str:
    if v is None or float(v) == 0:
        return ""          # the app never shows ₪0 / dashes for empty amounts
    v = float(v)
    return f"₪{v:,.2f}".rstrip("0").rstrip(".") if v % 1 else f"₪{v:,.0f}"


def period_text(r: dict) -> str:
    if r.get("renewing"):
        return "מתחדש"
    a, b = _d(r.get("period_start")), _d(r.get("period_end"))
    return f"{a} – {b}" if a or b else ""


def monthly(r: dict) -> float | None:
    """Monthly premium when the type says how — שנתית /12, חודשית as is; else None (not guessed)."""
    p, t = r.get("premium"), (r.get("premium_type") or "")
    if p is None:
        return None
    if t.startswith("שנתית"):
        return float(p) / 12
    if t.startswith("חודשית"):
        return float(p)
    return None


def is_active(r: dict, today: date | None = None) -> bool:
    today = today or date.today()
    return bool(r.get("renewing")) or (r.get("period_end") is None) or r["period_end"] >= today


def short_company(name: str | None) -> str:
    s = (name or "").replace('בע"מ', "").replace("חברה לביטוח", "").replace("ביטוח", "").strip(" -")
    return s or (name or "")


def group_policies(rows: list[dict]) -> "OrderedDict[tuple, list[dict]]":
    g: OrderedDict[tuple, list[dict]] = OrderedDict()
    for r in rows:
        key = (r.get("domain") or "", r.get("company") or "", r.get("policy_number") or f"_{r.get('sub_branch')}")
        g.setdefault(key, []).append(r)
    return g


def portfolio_md(customer_id: str, customer_name: str | None, rows: list[dict], produced_at: date | None = None,
                 notes: list[str] | None = None) -> str:
    who = f"{customer_name} (ת.ז {customer_id})" if customer_name else f"ת.ז {customer_id}"
    today = date.today()
    groups = group_policies(rows)
    active = [r for r in rows if is_active(r, today)]
    m_total = sum(m for m in (monthly(r) for r in active) if m)
    companies = sorted({short_company(r.get("company")) for r in rows if r.get("company")})
    by_domain: OrderedDict[str, int] = OrderedDict()
    for (dom, _c, _p) in groups:
        by_domain[dom or "אחר"] = by_domain.get(dom or "אחר", 0) + 1

    out = [f"# תיק ביטוחי — {who}", "",
           f"מקור: הר הביטוח (משרד האוצר){', הופק ' + _d(produced_at) if produced_at else ''}.", "",
           "## סיכום",
           f"- {len(groups)} פוליסות ({len(rows)} כיסויים) ב-{len(companies)} חברות: {', '.join(companies)}",
           "- לפי תחום: " + " · ".join(f"{d} {n}" for d, n in by_domain.items())]
    if m_total:
        out.append(f"- פרמיה חודשית משוערת לכיסויים בתוקף: {_money(round(m_total, 2))} "
                   "(שנתית חולקה ל-12; כיסויים בלי סוג פרמיה לא נספרו)")
    expired = len(rows) - len(active)
    if expired:
        out.append(f"- {expired} כיסויים שתקופתם הסתיימה לפני {_d(today)} (ייתכן שחודשו ועוד לא עודכנו בהר הביטוח)")
    out.append("")

    cur_dom = None
    for (dom, company, pno), items in groups.items():
        if dom != cur_dom:
            out += [f"## תחום {dom or 'אחר'}", ""]
            cur_dom = dom
        head = items[0]
        subs = list(OrderedDict.fromkeys(r.get("sub_branch") for r in items if r.get("sub_branch")))
        title = f"{head.get('main_branch') or ''} — {' + '.join(subs)}".strip(" —")
        num = head.get("policy_number")
        out.append(f"### {title} · {short_company(company)}" + (f" · פוליסה {num}" if num else ""))
        out.append(f"- מבוטח: {who}")
        out.append(f"- חברה: {company}" + (f" · סיווג: {head['plan_class']}" if head.get("plan_class") else ""))
        per = period_text(head)
        if per:
            out.append(f"- תקופת ביטוח: {per}" + ("" if is_active(head, today) else " (הסתיימה)"))
        out += ["", "| כיסוי | ענף משני | תקופה | פרמיה | סוג פרמיה |", "|---|---|---|---|---|"]
        for r in items:
            out.append("| {} | {} | {} | {} | {} |".format(
                r.get("product_type") or "", r.get("sub_branch") or "", period_text(r),
                _money(r.get("premium")), (r.get("premium_type") or "").replace("\n", " ").replace("|", "/")))
        out.append("")
    if notes:
        out += ["## הערות מהקובץ", *[f"- {n}" for n in notes], ""]
    return "\n".join(out).strip() + "\n"


def policy_detail_md(customer_id: str, customer_name: str | None, title: str, text: str,
                     company: str | None = None, policy_number: str | None = None) -> str:
    """A הר הביטוח policy detail view (its visible text, already cleaned) as one document."""
    who = f"{customer_name} (ת.ז {customer_id})" if customer_name else f"ת.ז {customer_id}"
    head = [f"# {title}", "", f"- מבוטח: {who}"]
    if company:
        head.append(f"- חברה: {company}")
    if policy_number:
        head.append(f"- מספר פוליסה: {policy_number}")
    head += ["- מקור: הר הביטוח — פרטי פוליסה", "", "## פרטים", ""]
    return "\n".join(head) + text.strip() + "\n"
