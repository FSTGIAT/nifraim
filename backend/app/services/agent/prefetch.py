"""Prefetch — run the obvious tools BEFORE the model, so it answers in ONE call.

A model round trip costs ~1.5–2.5s just to decide "call get_unpaid(הפניקס)". When the
question names a company, a customer (name or ת.ז) or a fund category, we already know
which tools it needs: run them here (same registry, same ToolContext → same privacy and
same numbers) and put their output in the first user message. The model can still call
more tools if something is missing.
"""
from __future__ import annotations

import re

from app.services.agent import registry
from app.services.agent.router import COMPANIES, ID_RE

FUND_CATS = [  # (pattern, tool)
    (r"חיסכון לכל ילד|חסכון לכל ילד|לילד", "compare_child_savings"),
    (r"גמל להשקעה", "compare_gemel_invest"),
    (r"השתלמות", "compare_hishtalmut"),
    (r"פנסי", "compare_pension"),
    (r"פוליס[הות] חיסכון|פוליסות חסכון", "compare_savings_policy"),
    (r"קופ(?:ת|ות) גמל|\bגמל\b", "compare_gemel"),
]
FUND_Q = re.compile(r"קרן|קרנות|קופ|מסלול|תשוא|הכי טוב|דמי ניהול|להשוות|השווא|מומלץ")
MARKET_CHANGE_Q = re.compile(r"השתנ|שינוי|שינויים|לעומת החודש|החודש שעבר|החודש הקודם|נכנס הכי|יצא הכי|זרם|גייס|עלו בדירוג|ירדו בדירוג|חדשות"
                             r"|הגדיל|הקטינ|העלו|הורידו")
# one track's allocation ("מה הפילוח של מור פנסיה מקיפה לבני 50 ומטה?") — never the insurer's commissions
ALLOC_Q = re.compile(r"פילוח|הרכב (?:ה)?נכסים|חשיפה ל|כמה (?:אג\"ח|מניות|מזומן)|אג\"ח מיועדות|איזון אקטוארי")
TRACKS = ["מניות", "כללי", "S&P", "אג\"ח", "אגח", "לבני 50", "עד 60", "ומעלה", "ומטה", "הלכה", "כספי", "שקלי"]
# A name ends at punctuation, at "עם/יש/של", or at "ב/מ + an insurer" ("…משה בהפניקס").
# NOT at any word starting with ב/מ — that cut "אברהם משה" to "אברהם" and "ברק" off names.
_CO = "|".join(COMPANIES)
NAME_RE = re.compile(r"(?:^|\s)(?:ל|ה|של )?לקוח(?:ה)?\s+([א-ת][א-ת'\"\- ]{2,30}?)"
                     r"(?=\s*(?:\?|$|,|\.| עם\b| יש\b| של\b| לא\b| (?:ב|מ)(?:" + _CO + r")))")
MAX_CHARS = 12000


NOT_A_NAME = re.compile(r"^(?:על|עם|לגבי|בנוגע|של|את|שלי|הזה|הזאת|ש)\b")
CALL_Q = re.compile(r"סיכמ|בשיחה|השיחה|שיחות|דיברנו|דיברתי|הקלט")
# "השתל" is for השתלה (transplant). Without (?!מות) every קרן השתלמות question was a policy question:
# search_policies prefetched a customer's policies and the market tools never ran (2026-10-10).
# A question about what a policy SAYS (cover, price, terms) — answered from the policy documents,
# never from commissions. Measured 2026-10-07: "כמה עולה לשאול גולן ביטוח הסיעוד שלו בהראל?" got
# get_unpaid(הראל) prefetched (the insurer name) and answered "no nursing record" from production.
POLICY_Q = re.compile(r"סיעוד|כיסוי|מכוס|החרג|מוטב|סכום (?:ה)?ביטוח|אכשר|תרופ|השתל(?!מות)|ניתוח|מחלות קשות|ריסק|"
                      r"אובדן כושר|אבדן כושר|עולה ל|משלמ?ת? על|תנאי|הנחה|פיצוי")


def plan(question: str) -> list[tuple[str, dict]]:
    q = " ".join((question or "").split())
    calls: list[tuple[str, dict]] = []
    if re.search(r"מובילים|הגדולים|הכי גדול", q) and re.search(r"מוצר|פוליס|מה יש|ביטוח|קופ", q):
        calls.append(("top_customers", {"metric": "premium" if "פרמי" in q else "pref", "n": 8}))
    if CALL_Q.search(q) and not re.search(r"(?:^|\s)(?:ת?קליט|עצור|תעצור)", q):
        # pick the calls tool that FITS (calls plane, tools_calls.py) — or none:
        if re.search(r"כמה שיחות|על מה (?:מדבר|דיבר)|נושא|סטטיסט|תמונת מצב של השיחות", q):
            calls.append(("calls_stats", {"days": 7 if "שבוע" in q else 30}))
        elif re.search(r"השיחה האחרונה|בשיחה האחרונה|מה סיכמ|סכם לי את השיחה", q):
            calls.append(("get_call_summaries", {"which": "last", "n": 3}))
        # "מה X אמר" / ציטוט / by meaning → no prefetch: the model uses search_calls / customer_calls
    m = ID_RE.search(q)
    if m:
        calls.append(("get_customer", {"id_number": m.group(1)}))
    else:
        n = NAME_RE.search(q)
        if n and not NOT_A_NAME.search(n.group(1)) and not re.search(r"\b(?:הכי|שלי|כולם|בכלל|חדשים)\b", n.group(1)):
            calls.append(("find_customer", {"query": n.group(1).strip()}))
    if POLICY_Q.search(q) and not re.search(r"עמל|לא שול|נפרע", q):
        m_id = ID_RE.search(q)
        calls.append(("search_policies", {"query": q, **({"id_number": m_id.group(1)} if m_id else {}), "limit": 8}))
        return calls[:3]          # never prime a cover/price question with commission tools
    if ALLOC_Q.search(q) and not MARKET_CHANGE_Q.search(q) and not ID_RE.search(q):
        calls.append(("fund_allocation", {"fund": q}))
        return calls[:3]
    explain = re.search(r"מה ההבדל|מה זה|תסביר|הסבר|איך עובד", q)
    if re.search(r"לקוחות", q) and re.search(r"ירד|עלו|טיפס|נפל", q) and re.search(r"דירוג|מסלול|קרנ|קופ", q):
        calls.append(("customers_in_market_moves", {"direction": "up" if re.search(r"עלו|טיפס", q) else "down"}))
        return calls[:3]
    m_cust = ID_RE.search(q)
    advice = re.search(r"הציע|הצעה|המלצ|להמליץ|כדאי|חסר|לנייד|ניוד|לשפר|לשדרג|לאחד|איחוד", q)
    if m_cust and (FUND_Q.search(q) or advice or any(re.search(p_, q) for p_, _ in FUND_CATS)):
        calls.append(("get_customer_fund_fit", {"id_number": m_cust.group(1)}))   # this customer's money vs the market
        return calls[:3]
    about_customer = bool(calls) or re.search(r"לקוח|שלו\b|שלה\b", q)
    market_change = MARKET_CHANGE_Q.search(q) and not about_customer
    if (FUND_Q.search(q) or market_change) and not explain and not re.search(r"מסלק", q):
        for pat, tool_name in FUND_CATS:
            if re.search(pat, q):
                if market_change:   # what changed in the market this month
                    calls.append(("market_changes", {"category": tool_name.removeprefix("compare_")}))
                    break
                track = next((t for t in TRACKS if t in q), "")
                calls.append((tool_name, {"track": track} if track else {}))
                break
    co = next((c for c in COMPANIES if c in q), "")
    # "כמה לקוחות יש לי בהראל?" / "כמה צבירה בהפניקס" is the BOOK at that company, not its debt
    # (measured: answered "155 לקוחות לא שולמו" and "I don't have the total")
    book_q = re.search(r"לקוחות|צביר|פרמי|מוצר|פוליסות|תיק", q) and not re.search(r"לא שול|חוב|חייב|פער|גבי|לא שיל|עמל", q)
    if co and book_q and not any(t.startswith("compare_") for t, _ in calls):
        calls.append(("get_portfolio", {"company": co, "metric": "premium" if "פרמי" in q else "accumulation"}))
    elif co and not any(t.startswith("compare_") for t, _ in calls):
        calls.append(("get_unpaid", {"company": co}))
        if re.search(r"הסכם|שיעור|אחוז|עמלה|למה|מתעכב|לא שיל", q):
            calls.append(("get_rate", {"company": co}))
        if re.search(r"למה|מתעכב|מגמה|חודש|עיכוב", q):
            calls.append(("get_commission_trend", {"company": co}))
    return calls[:3]


ADVICE_Q = re.compile(r"הציע|הצעה|המלצ|להמליץ|כדאי|חסר|לנייד|ניוד|לשפר|לשדרג|לאחד|איחוד|ביחס לשוק|תשוא|מסלול")


async def _id_for_name(ctx, full_name: str) -> str | None:
    m = await ctx.map()
    a, b = (full_name.split() + [""])[:2]
    for c in [*m.customers, *m.extra.values()]:
        fn, ln = _norm(c.get("first_name") or ""), _norm(c.get("last_name") or "")
        if {fn, ln} == {a, b}:
            return str(c.get("id_number")).lstrip("0")
    return None


_PREFIX = "ולבשמה"   # Hebrew one-letter prefixes: לעומר, שעומר, ועומר, מעומר, בעומר, העומר


def _norm(w: str) -> str:
    return re.sub(r"[^\u0590-\u05FFa-zA-Z0-9]", "", w or "")


async def named_customer(ctx, question: str) -> str | None:
    """The full name of one of THIS agent's customers mentioned in the question, or None.
    Matched on two consecutive words (first+last, either order), a one-letter prefix allowed
    on the first word — "כמה לא שולם לעומר עמר" → "עומר עמר". Single words are never
    matched: חיים / מור / שמחה are both names and words."""
    words = [_norm(w) for w in (question or "").split()]
    words = [w for w in words if w]
    if len(words) < 2:
        return None
    m = await ctx.map()
    names = set()
    for c in [*m.customers, *m.extra.values()]:
        fn, ln = _norm(c.get("first_name") or ""), _norm(c.get("last_name") or "")
        if fn and ln:
            names.add(f"{fn} {ln}")
            names.add(f"{ln} {fn}")
    for i in range(len(words) - 1):
        a, b = words[i], words[i + 1]
        for first in {a, a[1:] if len(a) > 2 and a[0] in _PREFIX else a}:
            if f"{first} {b}" in names:
                return f"{first} {b}"
    return None


async def run_prefetch(ctx, question: str):
    """Yields status events; returns (via ctx.prefetched) the text block for the prompt."""
    blocks = []
    steps = plan(question)
    if ctx.named_customer and not any(n in ("find_customer", "get_customer") for n, _ in steps):
        steps = [("find_customer", {"query": ctx.named_customer})] + steps

    # "מה כדאי להציע ללירן סורני?" — a customer named by NAME also gets the market comparison
    # (plan() or named_customer may have added find_customer; either way the fit never ran — 2026-10-10)
    fc = next((a for n, a in steps if n == "find_customer"), None)
    if fc and ADVICE_Q.search(question) and not any(n == "get_customer_fund_fit" for n, _ in steps):
        idn = await _id_for_name(ctx, ctx.named_customer or fc.get("query") or "")
        if idn:
            steps.insert(steps.index(("find_customer", fc)) + 1, ("get_customer_fund_fit", {"id_number": idn}))
    for name, args in steps[:3]:
        if args.get("metric") == "pref":          # the agent's remembered ranking (e.g. by premium)
            from app.services.agent.router import _preferred_metric
            args = {**args, "metric": await _preferred_metric(ctx)}
        t = registry.get(name)
        if not t:
            continue
        yield {"status": t.status_he}
        out = await registry.dispatch(ctx, name, args)
        # the market comparisons carry a summary + one line per product — cutting them hid a customer's
        # pension (2026-10-10); they get a larger share of the MAX_CHARS budget
        cap = 7500 if name in ("get_customer_fund_fit", "market_changes") else (6000 if len(steps[:3]) == 1 else 4000)
        blocks.append(f"### {name}({', '.join(f'{k}={v}' for k, v in args.items())})\n{out[:cap]}")
    text = "\n\n".join(blocks)
    ctx.prefetched = text[:MAX_CHARS]
