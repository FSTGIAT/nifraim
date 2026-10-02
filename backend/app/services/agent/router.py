"""Fast lane: the agent's most common questions answered WITHOUT an LLM.

Conservative by design — a question only takes the fast lane when one pattern
matches clearly, it is short, and it is not an action ("תשלח/תכין…") or a "why"
question. Everything else goes to the agent loop. The answer is a Hebrew
template over the SAME tool the agent lane would call, plus its chart.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.agent import registry
from app.services.agent.tools_viz import build_viz

COMPANIES = ["הפניקס", "הראל", "מגדל", "כלל", "מנורה", "מור", "מיטב", "אלטשולר", "ילין", "איילון", "הכשרה", "אקסלנס",
             "אנליסט", "פסגות", "אינפיניטי", "הלמן", "שומרה", "ביטוח ישיר", "AIG", "ווישור"]
ACTION = re.compile(r"(?:^|\s)(?:ו|ש)?(?:ת?שלח|ת?כין|הכן|ת?קבע|ת?זמן|ת?זכיר|תענה|ת?כתוב|לשלוח|לקבוע|להכין|תבקש|בקש)")
WHY = re.compile(r"למה|מדוע|איך זה|הסבר")
ID_RE = re.compile(r"(?<!\d)(\d{5,9})(?!\d)")


@dataclass
class Route:
    intent: str
    tool: str
    args: dict


def _company(q: str) -> str:
    return next((c for c in COMPANIES if c in q), "")


def route(question: str) -> Route | None:
    q = " ".join((question or "").split())
    if not q or len(q) > 90 or ACTION.search(q) or WHY.search(q):
        return None
    co = _company(q)
    about_one_customer = bool(re.search(r"(?:^|\s)(?:ל|ה|של )?לקוח(?:ה)?\s+[א-ת]", q))
    if re.search(r"מסלק", q):
        return Route("maslaka_status", "maslaka_status", {})
    m = ID_RE.search(q)
    if m and re.search(r"לקוח|ת\.?ז|תז|מה יש", q):
        return Route("customer", "get_customer", {"id_number": m.group(1)})
    if re.search(r"הגדול|מובילים|הכי גדול|הכי גדולים|top", q):
        return Route("top", "top_customers", {"metric": "premium" if "פרמי" in q else "", "n": 10})
    m = re.search(r"(?:^|\s)(?:מה יש ל|מה עם |כרטיס של |תראה לי את )?(?:ה)?לקוח(?:ה)?\s+([א-ת'\"\- ]{3,30}?)\s*\??$", q)
    if m and re.search(r"\b(?:הכי|שלי|שלך|כולם|בכלל|חדש|חדשים)\b", m.group(1)):
        m = None
    if m and not re.search(r"לא שול|חוב|עמל|מסלק", q):
        return Route("customer_name", "find_customer", {"query": m.group(1).strip()})
    if about_one_customer:
        return None            # a question about ONE named customer → the agent finds them first
    if re.search(r"לא שול|לא קיבלתי|לא שיל[םמ]|לא משלמ|חוב|פער|חייב", q):
        return Route("unpaid", "get_unpaid", {"company": co})
    if re.search(r"(שיעור|אחוז)\s*(ה)?עמלה|מה ההסכם|הסכם עם", q) and co:
        return Route("rate", "get_rate", {"company": co})
    if re.search(r"עזב|עזבו|בוטל|ביטלו|יצאו|לקוחות חדשים|נכנסו", q):
        return Route("changes", "get_production_changes", {})
    if re.search(r"הגדול|מובילים|הכי גדול|הכי גדולים|top", q):
        return Route("top", "top_customers", {"metric": "premium" if "פרמי" in q else "accumulation", "n": 10})
    if (re.search(r"עמל|נכנס|הכנס|קיבלתי", q) and re.search(r"החודש|חודש שעבר|חודש קודם|מגמה|לפי חודש|קיבלתי", q)) \
            or re.search(r"כמה נכנס|כמה הרווחתי|כמה הכנסתי", q):
        return Route("trend", "get_commission_trend", {"company": co})
    if re.search(r"צביר|פרמי", q) and re.search(r"לפי חברה|בתיק|כמה יש|סך", q):
        return Route("portfolio", "get_portfolio", {"company": co, "metric": "premium" if "פרמי" in q else "accumulation"})
    if re.search(r"מה (כדאי|לעשות|פתוח)|משימות|מה מחכה", q):
        return Route("tasks", "get_insights", {"kind": "tasks"})
    if re.search(r"תמונת מצב|איך אני עומד|סיכום (של )?התיק|סיכום כללי|כמה לקוחות (יש לי|בתיק)", q):
        return Route("overview", "get_overview", {})
    return None


def _m(v) -> str:
    try:
        return f"₪{round(float(v)):,}"
    except (TypeError, ValueError):
        return "—"


def render(route_: Route, data) -> tuple[str, str | None]:
    """(answer text, chart type or None)."""
    if route_.intent == "customer_name":
        # exactly one customer → their card; none / several → let the agent ask or choose
        ids = set(re.findall(r"ת\.ז (\d+)", data or ""))
        if len(ids) != 1 or data.startswith("נמצאו 2") or data.startswith("# חיפוש"):
            return "", None
    if isinstance(data, str):            # markdown page tools (tasks, customer)
        lines = []
        for l in data.splitlines():
            l = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", l).replace("**", "").strip()
            l = re.sub(r"\s*·\s*[^·]*?\s—(?=\s*·|\s*$)", "", l)   # empty fields: show nothing, never "—"
            if not l or l.startswith("[←"):
                continue
            if l.startswith("#"):
                l = l.lstrip("# ").strip()
                if not lines:          # the page title is the question — skip it
                    continue
                l = l + ":"
            lines.append(l)
        return "\n".join(lines[:16]), None
    i = route_.intent
    if i == "unpaid":
        if data.get("company"):
            n = data.get("customers_count", 0)
            if not n:
                return f"ב{data['company']} אין כרגע לקוחות שלא שולמו.", None
            top = ", ".join(c["label"] for c in data["customers"][:3])
            return (f"ב{data['company']} {n} לקוחות לא שולמו, צפי {_m(data.get('total_expected'))}. הגדולים: {top}.\n"
                    f"אפשר לבקש ממני להכין תזכורת גבייה ל{data['company']}."), "bar"
        rows = data.get("by_company") or []
        if not rows:
            return "אין כרגע עמלות פתוחות — כל מה שצפוי שולם.", None
        lead = rows[0]
        return (f"סה\"כ לא שולם: {_m(data.get('total_gap'))} ל-{data.get('unpaid_customers')} לקוחות. "
                f"הפער הגדול ב{lead['label']} ({_m(lead['value'])}, {lead.get('unpaid_customers')} לקוחות)."), "bar"
    if i == "trend":
        last, prev = data.get("last"), data.get("prev")
        if not last:
            return "עוד אין קבצי נפרעים עם חודש מזוהה.", None
        s = f"ב-{last['label']} התקבלו {_m(last['value'])}"
        if prev:
            ch = last["value"] - prev["value"]
            s += f", {'עלייה' if ch >= 0 else 'ירידה'} של {_m(abs(ch))} מול {prev['label']}"
        return s + ".", "trend" if len(data.get("months") or []) > 1 else None
    if i == "portfolio":
        rows = data.get("companies") or []
        if not rows:
            return "אין קובץ פרודוקציה פעיל.", None
        tot_acc = sum(r["accumulation"] for r in rows)
        tot_pr = sum(r["premium"] for r in rows)
        bits = []
        if tot_acc:
            bits.append(f"צבירה {_m(tot_acc)}")
        if tot_pr:
            bits.append(f"פרמיה {_m(tot_pr)}")
        return f"בתיק: {' · '.join(bits)} ב-{len(rows)} חברות. המובילה: {rows[0]['label']} ({_m(rows[0]['value'])}).", "donut"
    if i == "top":
        rows = data.get("customers") or []
        if not rows:
            return "אין לקוחות בפרודוקציה.", None
        return ("הלקוחות הגדולים לפי " + ("פרמיה" if data.get("metric") == "premium" else "צבירה") + ": "
                + ", ".join(f"{r['label']} ({_m(r['value'])})" for r in rows[:3]) + "."), "bar"
    if i == "changes":
        rows = data.get("companies") or []
        if not rows:
            return data.get("note") or "אין שינויים להצגה.", None
        parts = [f"{r['company']}: {r['new']} חדשים, {r['left']} יצאו" for r in rows]
        return "מול הקובץ הקודם — " + " · ".join(parts) + ".", "bar" if sum(r["left"] for r in rows) else None
    if i == "rate":
        if not data.get("found"):
            return data.get("note"), None
        r = data["rates"][:4]
        return f"ההסכם עם {data['company']}: " + " · ".join(f"{x['product']} {x['rate_pct']}%" + (f" ({x['scope']})" if x.get('scope') else "") for x in r) + ".", None
    if i == "maslaka_status":
        a = data.get("association") or {}
        s = "השיוך למסלקה מאושר." if a.get("status") == "approved" else f"השיוך למסלקה: {a.get('status')}."
        if data.get("open_requests"):
            s += f" {len(data['open_requests'])} בקשות פתוחות; הקרובה צפויה ב-{data['open_requests'][0]['answer_expected']}."
        s += f" {data.get('customers_with_maslaka_data', 0)} לקוחות עם נתוני מסלקה. הפרודוקציה הבאה: {data.get('next_production_date')}."
        return s, None
    if i == "overview":
        s = (f"{data.get('customers_in_production')} לקוחות בפרודוקציה. "
             f"התקבלו {_m(data.get('received_total'))} מתוך צפי {_m(data.get('expected_total'))}; "
             f"לא שולם {_m(data.get('gap_unpaid_total'))} ל-{data.get('unpaid_customers')} לקוחות.")
        if data.get("last_commission_month"):
            s += f" בחודש האחרון ({data['last_commission_month']}) נכנסו {_m(data.get('last_month_received'))}."
        return s, "donut"
    return "", None


async def _preferred_metric(ctx) -> str:
    """'הגדולים' has two honest meanings — use the one this agent told us to remember."""
    from sqlalchemy import select
    from app.models.ai_memory import AiMemory
    texts = (await ctx.db.execute(select(AiMemory.text).where(AiMemory.user_id == ctx.user.id))).scalars().all()
    rank_words = ("דרג", "דורג", "דירוג", "גדול", "מובילים")
    return "premium" if any("פרמי" in t and "צביר" not in t.split("פרמי")[0] and any(w in t for w in rank_words)
                            for t in texts) else "accumulation"


async def answer(ctx, r: Route) -> dict | None:
    if r.intent == "top" and not r.args.get("metric"):
        r.args["metric"] = await _preferred_metric(ctx)
    t = registry.get(r.tool)
    if not t:
        return None
    data = await t.fn(ctx, **r.args)
    text, chart = render(r, data)
    if not text:
        return None
    vizs = []
    if chart and isinstance(data, dict) and data.get("result_id") in ctx.results:
        kept = ctx.results[data["result_id"]]
        positive = [r for r in kept["rows"] if isinstance(r.get("value"), (int, float)) and r["value"] > 0]
        if len(positive) >= 2 or (chart == "trend" and len(kept["rows"]) >= 2):
            vizs.append(build_viz(kept, chart))
    return {"text": text, "vizs": vizs, "status": t.status_he}
