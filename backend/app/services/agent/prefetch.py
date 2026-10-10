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
    (r"פנסי|מקפת", "compare_pension"),   # "מגדל מקפת אישית כללי" is Migdal's pension fund
    (r"פוליס[הות] חיסכון|פוליסות חסכון", "compare_savings_policy"),
    (r"קופ(?:ת|ות) גמל|(?<![א-ת])[בלהו]?גמל(?![א-ת])", "compare_gemel"),   # \b fails on "בגמל" (Hebrew letters are all \w)
]
FUND_Q = re.compile(r"קרן|קרנות|קופ|מסלול|תשוא|הכי טוב|דמי (?:ה)?ניהול|להשוות|השווא|מומלץ")
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
    # one track's allocation — also "מה השתנה בפילוח של X" (fund_allocation carries the change vs last month);
    # only a market-wide "אילו מסלולים הגדילו חשיפה" goes to market_changes (2026-10-10: the change words
    # sent "כלל פנסיה כללי" to a returns table and Nifra said it had no allocation)
    market_wide = re.search(r"(?:^|\s)(?:אילו|איזה|אלו)\s|מסלולים|קרנות", q)
    if ALLOC_Q.search(q) and not ID_RE.search(q) and (not MARKET_CHANGE_Q.search(q) or not market_wide):
        calls.append(("fund_allocation", {"fund": q}))
        return calls[:3]
    cos = companies_in(q)
    if len(set(cos)) >= 2 and re.search(r"תשווה|השווה|השוואה|מול|לעומת|בין", q) and not ID_RE.search(q):
        cat_tool = next((t for p_, t in FUND_CATS if re.search(p_, q)), None)
        if cat_tool:   # "תשווה בין מור למיטב בפנסיה" — each company's tracks (was: the market top 10, Mor absent)
            return [(cat_tool, {"company": c}) for c in list(dict.fromkeys(cos))[:3]]
    if re.search(r"לא פעיל", q) and re.search(r"הכי|גדול|לקוחות", q) and not ID_RE.search(q):
        return [("get_insights", {"kind": "retention"})]   # inactive funds with balances — not the all-book top list
    named_co = companies_in(q)
    if named_co and re.search(r"(?:^|\s)(?:מי|איזה|אילו)\b.*לקוח|הלקוח(?:ה)? (?:עם|הכי)|הכי (?:גבוה|גדול)", q) \
            and not re.search(r"לא שול|חוב|עמל|נפרע|מפגר|ירד|עלו|דירוג", q):
        # "מי הלקוחה עם הצבירה הכי גבוהה במור?" / "איזה לקוחות שלי בגמל מניות בהפניקס?"
        prod = next((w for w in ("גמל להשקעה", "השתלמות", "פנסיה", "פוליסת חיסכון", "גמל", "חיים", "בריאות", "סיעוד", "מנהלים") if w in q), "")
        trk = next((t for t in TRACKS if t in q), "")
        return [("customers_by_product", {"company": named_co[0], **({"product": prod} if prod else {}), **({"track": trk} if trk else {})})]
    if re.search(r"מסלול", q) and re.search(r"רוב הלקוחות|הכי הרבה לקוחות|התיק (?:שלי )?לפי מסלול|כמה (?:כסף|צבירה) (?:אצלי )?במסלול", q):
        return [("tracks_in_book", {"company": next(iter(companies_in(q)), "")})]   # "באיזה מסלול רוב הלקוחות שלי?"
    if re.search(r"פער", q) and re.search(r"כולל|כל הלקוחות|סך הכל|בסך הכל", q) and re.search(r"שוק|מסלול|תשוא", q):
        return [("fund_opportunities", {"min_gap_ils": 0})]   # the book's total gap vs the market
    if re.search(r"הכי גדול|הגדול", q) and not companies_in(q):
        cat_tool = next((t for p_, t in FUND_CATS if re.search(p_, q)), None)
        if cat_tool:   # "איזה קרן פנסיה הכי גדולה?" — by size
            return [(cat_tool, {"sort_by": "size"})]
    if re.search(r"כמה (?:כסף )?(?:נכנס|יצא|זרם|גייס)", q) and not re.search(r"עמל", q):
        cat_tool = next((t for p_, t in FUND_CATS if re.search(p_, q)), None)
        if cat_tool:   # "כמה כסף נכנס לקרנות ההשתלמות החודש?" — market flows
            return [("market_flows", {"category": cat_tool.removeprefix("compare_")})]
    explain = re.search(r"מה ההבדל|מה זה|תסביר|הסבר|איך עובד", q)
    if re.search(r"לקוחות", q) and re.search(r"ירד|עלו|טיפס|נפל", q) and re.search(r"דירוג|מסלול|קרנ|קופ", q):
        calls.append(("customers_in_market_moves", {"direction": "up" if re.search(r"עלו|טיפס", q) else "down"}))
        return calls[:3]
    m_cust = ID_RE.search(q)
    if m_cust and CUSTOMER_CHANGE_Q.search(q):
        calls.append(("customer_changes", {"id_number": m_cust.group(1)}))
        return calls[:3]
    advice = re.search(r"הציע|הצעה|המלצ|להמליץ|כדאי|חסר|לנייד|ניוד|לשפר|לשדרג|לאחד|איחוד", q)
    if m_cust and (FUND_Q.search(q) or advice or any(re.search(p_, q) for p_, _ in FUND_CATS)):
        calls.append(("get_customer_fund_fit", {"id_number": m_cust.group(1)}))   # this customer's money vs the market
        return calls[:3]
    about_customer = bool(calls) or re.search(r"לקוח|שלו\b|שלה\b", q)
    market_change = MARKET_CHANGE_Q.search(q) and not about_customer
    if (FUND_Q.search(q) or market_change) and not explain and not re.search(r"מסלק", q):
        for pat, tool_name in FUND_CATS:
            if re.search(pat, q):
                named = companies_in(q)
                if market_change and named:   # "איך הפנסיה של מגדל השתנתה?" — that company's tracks (YTD, 12m, rank)
                    calls += [(tool_name, {"company": c}) for c in named[:2]]
                    break
                if market_change:   # what changed in the market this month
                    calls.append(("market_changes", {"category": tool_name.removeprefix("compare_")}))
                    break
                track = next((t for t in TRACKS if t in q), "")
                cheap = re.search(r"דמי (?:ה)?ניהול", q) and re.search(r"נמוכ|הזול|הכי פחות", q)   # sort by fee, not returns
                co_f = next(iter(companies_in(q)), "")   # "מגדל מקפת אישית כללי" — that company's tracks
                calls.append((tool_name, {**({"track": track} if track else {}), **({"sort_by": "fee"} if cheap else {}),
                                          **({"company": co_f} if co_f else {})}))
                break
    co = next(iter(companies_in(q)), "")
    market_q = any(t.startswith("compare_") or t == "market_changes" for t, _ in calls)
    if co and not market_q and any(re.search(p_, q) for p_, _ in FUND_CATS) \
            and re.search(r"תשוא|ביצוע|מתחילת השנה|השתנ|דמי ניהול|הכי טוב", q) and not re.search(r"עמל|לא שול|נפרע|חוב", q):
        # "איך הפנסיה של מגדל השתנתה מתחילת השנה?" — Migdal's tracks, not Migdal's commissions
        cat_tool = next(t for p_, t in FUND_CATS if re.search(p_, q))
        calls.append((cat_tool, {"company": co}))
        market_q = True
    # "כמה לקוחות יש לי בהראל?" / "כמה צבירה בהפניקס" is the BOOK at that company, not its debt
    # (measured: answered "155 לקוחות לא שולמו" and "I don't have the total")
    book_q = re.search(r"לקוחות|צביר|פרמי|מוצר|פוליסות|תיק", q) and not re.search(r"לא שול|חוב|חייב|פער|גבי|לא שיל|עמל", q)
    if co and book_q and not market_q:
        calls.append(("get_portfolio", {"company": co, "metric": "premium" if "פרמי" in q else "accumulation"}))
    elif co and not market_q:
        calls.append(("get_unpaid", {"company": co}))
        if re.search(r"הסכם|שיעור|אחוז|עמלה|למה|מתעכב|לא שיל", q):
            calls.append(("get_rate", {"company": co}))
        if re.search(r"למה|מתעכב|מגמה|חודש|עיכוב", q):
            calls.append(("get_commission_trend", {"company": co}))
    return calls[:3]


CUSTOMER_CHANGE_Q = re.compile(r"השתנ|שינוי|לאורך (?:ה)?זמן|מהחודש שעבר|מגמה|היסטורי|עלה|ירד")
ADVICE_Q = re.compile(r"הציע|הצעה|המלצ|להמליץ|כדאי|חסר|לנייד|ניוד|לשפר|לשדרג|לאחד|איחוד|ביחס לשוק|תשוא|מסלול|להעביר|העברה|מפסיד")


async def _id_for_name(ctx, full_name: str) -> str | None:
    m = await ctx.map()
    a, b = (full_name.split() + [""])[:2]
    for c in [*m.customers, *m.extra.values()]:
        fn, ln = _norm(c.get("first_name") or ""), _norm(c.get("last_name") or "")
        if {fn, ln} == {a, b}:
            return str(c.get("id_number")).lstrip("0")
    return None


def companies_in(q: str) -> list[str]:
    """Companies named as WORDS (prefixes ב/ל/מ/ה/ו/ש allowed). "פנסיה מקיפה לכללית" is not כלל — the
    substring match prefetched Clal's unpaid commissions for a definition question (2026-10-10)."""
    return [c for c in COMPANIES
            if re.search(rf"(?:^|[\s,.?!\"'(])(?:[בלמהוש]{{0,2}}){re.escape(c)}(?=$|[\s,.?!\"')])", q)]


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
    if fc and CUSTOMER_CHANGE_Q.search(question) and not any(n == "customer_changes" for n, _ in steps):
        idn = await _id_for_name(ctx, ctx.named_customer or fc.get("query") or "")
        if idn:   # "אילת דנה לוי — מה השתנה אצלה מהחודש שעבר?"
            steps = [s_ for s_ in steps if not s_[0] in ("market_changes",) and not s_[0].startswith("compare_")]
            steps.insert(steps.index(("find_customer", fc)) + 1, ("customer_changes", {"id_number": idn}))
    elif fc and ADVICE_Q.search(question) and not any(n == "get_customer_fund_fit" for n, _ in steps):
        idn = await _id_for_name(ctx, ctx.named_customer or fc.get("query") or "")
        if idn:
            steps.insert(steps.index(("find_customer", fc)) + 1, ("get_customer_fund_fit", {"id_number": idn}))
    if any(n == "get_customer_fund_fit" for n, _ in steps):
        # "ישראלה — הפנסיה שלה במסלול טוב?" / "להעביר את בועז לאלטשולר?" — about ONE customer: a market top-10
        # table or the insurer's unpaid commissions only push the customer's comparison out (2026-10-10)
        steps = [(n, a) for n, a in steps if not n.startswith("compare_") and n not in ("get_unpaid", "get_rate", "get_commission_trend")]
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
