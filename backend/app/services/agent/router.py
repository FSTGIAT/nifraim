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
    """A company named as a WORD (with ב/ל/מ/ה/ו/ש prefixes) — "לעומר מור" is a customer, not מור."""
    for c in COMPANIES:
        if re.search(rf"(?:^|[\s,.?!\"'(])(?:[בלמהוש]{{0,2}}){re.escape(c)}(?=$|[\s,.?!\"')])", q) and not _surname(q, c):
            return c
    return _company_typo(q)


def _lev1(a: str, b: str) -> bool:
    """Edit distance ≤ 1 (one letter added, dropped or swapped)."""
    if abs(len(a) - len(b)) > 1 or a == b:
        return a == b
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    s, l = (a, b) if len(a) < len(b) else (b, a)
    return any(l[:i] + l[i + 1:] == s for i in range(len(l)))


def _company_typo(q: str) -> str:
    """"מנורא", "פנקס", "הפנקס", "מיגדל" — one letter off a company of 4+ letters (no prefix-stripped
    match on short words: "מור" is too close to too many names)."""
    for w in re.findall(r"[א-ת]{4,}", q):
        for cand in {w, re.sub(r"^[בלמהוש]{1,2}", "", w)}:
            for c in COMPANIES:
                bare = c.removeprefix("ה")
                if len(bare) >= 4 and (_lev1(cand, c) or _lev1(cand, bare)) and not _surname(q, cand):
                    return c
    return ""


def _surname(q: str, company: str) -> bool:
    """The company word right after a first name ("עומר מור") is a person's surname."""
    return bool(re.search(rf"[א-ת]{{2,}}\s+{re.escape(company)}(?=$|[\s,.?!])", q)) and not re.search(
        rf"(?:^|\s)(?:ב|ל|של|מ|את|עם|לגבי|בחברת|חברת)\s*{re.escape(company)}", q)


MONTH_RE = re.compile(r"(?:^|[\s,(])(?:[בלמ]?)(?:ינואר|פברואר|מרץ|מרס|אפריל|מאי|יוני|יולי|אוגוסט|ספטמבר|אוקטובר|נובמבר|דצמבר)(?=$|[\s,.?!)])"
                      r"|\b\d{1,2}[/.-]\d{2,4}\b")

# words an unpaid / company question is made of — anything else (a customer's name) → agent lane
_UNPAID_WORDS = set("""מי מה כמה על של את עם לגבי יש לי לא שולם שולמו שילמו שילם קיבלתי חוב חובות חייב חייבים חייבת
פער פערים עמלה עמלות עמלת נפרעים במנורה החברה חברה חברות לפי בכל כל הכי תראה תן ספר רשימה רשימת לקוחות לקוח
ממנה ממנו מהם שלא עדיין אצל איפה איזה אילו אלו מהחברה ומה ואיפה הגדול הגדולים
חודש החודש בחודש אחרון האחרון קודם הקודם שעבר מגמה קיבלתי נכנס הכנסתי הרווחתי סך הכל בסך""".split())


def _unexplained_words(q: str, co: str) -> bool:
    for w in re.findall(r"[א-ת]+", q):
        base = re.sub(r"^[בלמהוש]{1,2}(?=[א-ת]{2,})", "", w)
        if w in _UNPAID_WORDS or base in _UNPAID_WORDS or (co and co in w):
            continue
        return True
    return False


def harb_request(q: str) -> dict | None:
    """"תביא לי מהר הביטוח 203717186 תאריך לידה 06091991 הנפקה 30.6.2020" → {id_number, birth_date,
    issue_date}, or None unless exactly one ID and two valid dates are there. Dates with separators,
    or 8 digits (ddmmyyyy) after the ID. A label (לידה / הנפקה) right before a date decides which is
    which; otherwise the earlier date is the birth date (an ID is always issued after birth)."""
    from app.services.office_agent import HARB_ACTION_RE
    from app.services.policies.harb_jobs import parse_user_date
    if not HARB_ACTION_RE.search(q):
        return None
    toks = [(m.group(0), m.start()) for m in re.finditer(r"\d{1,4}[/.\-]\d{1,2}[/.\-]\d{2,4}|\d{5,9}", q)]
    idn, dates = None, []
    for tok, pos in toks:
        d = parse_user_date(tok) if (not tok.isdigit() or (idn and len(tok) == 8)) else None
        if d:
            label = q[max(0, pos - 25):pos]
            kind = ("issue" if re.search(r"הנפק", label) and not re.search(r"לידה[^\d]*$", label)
                    else "birth" if re.search(r"לידה", label) else None)
            dates.append((d, kind))
        elif tok.isdigit() and idn is None:
            idn = tok
    if not idn or len(dates) != 2:
        return None
    birth = next((d for d, k in dates if k == "birth"), None)
    issue = next((d for d, k in dates if k == "issue"), None)
    if birth is None or issue is None:
        birth, issue = sorted(d for d, _ in dates)
    out = {"id_number": idn, "birth_date": birth.strftime("%d/%m/%Y"), "issue_date": issue.strftime("%d/%m/%Y")}
    if re.search(r"שוב|מחדש|בכל זאת|עדכני|רענן", q):
        out["confirm_refetch"] = True          # the agent already said "again"
    return out


def route(question: str) -> Route | None:
    q = " ".join((question or "").split())
    # a הר הביטוח fetch with everything it needs → the proposal, deterministically (never a model's
    # "done" — measured 2026-10-07: with policies already stored it answered "השליפה הושלמה" unfetched)
    hr = harb_request(q)
    if hr:
        return Route("harb_fetch", "propose_harb_fetch", hr)
    if q and len(q) <= 60:
        if re.search(r"^(?:תעצור|עצור|תפסיק|הפסק|סיים|תסיים)\b.*(?:הקלט|שיחה)|^(?:עצור|תעצור|stop)[!.\s]*$", q):
            return Route("stop_call", "stop_call_recording", {})
        m = re.search(r"(?:^|\s)(?:ת?קליט|הקלט|תתחיל להקליט|להקליט|record)\b(.*)", q)
        if m and not re.search(r"מה|כמה|איך|למה|שיחות שהוקלטו|סיכום", q):
            about = re.sub(r"^\s*(?:את\s+)?(?:ה)?שיחה\s*", "", m.group(1)).strip(" .?!")
            return Route("record_call", "start_call_recording", {"about": about[:80]})
    if not q or len(q) > 90 or ACTION.search(q) or WHY.search(q):
        return None
    if re.search(r"שיח|(?:^|\s)(?:אמר|אמרה|סיפר|סיפרה|דיבר|דיברה|התלונן|התלוננה)(?:\s|$)", q):
        return None            # calls: the agent lane picks search_calls / calls_stats / open_promises
    if re.search(r"הר\s*ה?ביטוח|פוליס|כיסוי|מכוסה|מבוטח[תי]? ב|החרג", q) and not re.search(r"הכי הרבה", q):
        return None            # policies / הר הביטוח: agent lane (customer_policies / search_policies / propose_harb_fetch)
    co = _company(q)
    # "אילו מוצרים יש ללקוחות המובילים" asks WHAT they hold, not who they are — a compound
    # question; the instant ranking would answer only half of it. → agent lane (+prefetch).
    if re.search(r"(?:אילו|איזה|אלו|מה)\s+(?:מוצר|פוליס|ביטוח|קופ|כיסו)|מה יש ל|יש ל(?:לקוחות|הם|הן)\b", q) \
            and re.search(r"מובילים|הגדול|הכי גדול|top", q):
        return None
    about_one_customer = bool(re.search(r"(?:^|\s)(?:ל|ה|של )?לקוח(?:ה)?\s+[א-ת]", q))
    if re.search(r"מסלק", q):
        # Only a plain status question is instant. What CHANGED in the file, what is
        # new / removed, or one customer's holdings go to the agent lane, which picks
        # maslaka_delta / customer_holdings (2026-10-09: every מסלקה question got the
        # same canned status line, the delta and holdings tools were never reached).
        if ID_RE.search(q) or about_one_customer or re.search(
                r"השתנ|שינוי|שינויים|חדש|הוסר|נעלמ|נוספ|לעומת|מול|הפרש|עלה|ירד|צביר|מוצר|לקוחות עם|מי ה", q):
            return None
        return Route("maslaka_status", "maslaka_status", {})
    m = ID_RE.search(q)
    if m and re.search(r"לקוח|ת\.?ז|תז|מה יש", q) and not re.search(
            r"שוק|תשוא|מסלול|דמי ניהול|פער|פילוח|חשיפ|הציע|הצעה|המלצ|להמליץ|כדאי|חסר|לנייד|ניוד|לשפר|לשדרג|לאחד|איחוד"
            r"|אצלי|אצל סוכן|לא אצל|מסלק|השתנ|שינוי|לאורך|מגמה", q):
        # "הלקוח X — המסלול שלו ביחס לשוק?" / "מה כדאי להציע ל-X?" need advice, not the raw card (2026-10-10)
        return Route("customer", "get_customer", {"id_number": m.group(1)})
    if re.search(r"הכי הרבה (מוצרים|פוליסות|קופות)|(מוצרים|פוליסות) הכי הרבה|הכי הרבה מוצר", q):
        return Route("top", "top_customers", {"metric": "products", "n": 10})
    if re.search(r"הגדול|מובילים|הכי גדול|הכי גדולים|top", q) and not re.search(
            r"מוצר|עמל|(?:^|\s)(?:הוא|היא|זה)\s+לא\b|לא נכון|טעית|לא פעיל|קופות", q) and not co:
        # "אילו לקוחות עם קופות לא פעילות הכי גדולות" / "הכי גדול במור" are not the all-book top list
        return Route("top", "top_customers", {"metric": "premium" if "פרמי" in q else "", "n": 10})
    m = re.search(r"(?:^|\s)(?:מה יש ל|מה עם |כרטיס של |תראה לי את )?(?:ה)?לקוח(?:ה)?\s+([א-ת'\"\- ]{3,30}?)\s*\??$", q)
    if m and (re.search(r"\b(?:הכי|שלי|שלך|כולם|בכלל|חדש|חדשים)\b", m.group(1))
              or re.match(r"(?:על|עם|לגבי|בנוגע|של|את)\b", m.group(1))):
        m = None
    if m and not re.search(r"לא שול|חוב|עמל|מסלק", q):
        return Route("customer_name", "find_customer", {"query": m.group(1).strip()})
    if about_one_customer:
        return None            # a question about ONE named customer → the agent finds them first
    # "paid vs the agreement" is the rate audit, not the unpaid list — they
    # answered ₪49 (unpaid customers) to a −₪10,137 rate gap (QA 2026-10-08).
    if re.search(r"הסכמ|לפי ההסכם", q) and re.search(r"בפועל|ששולמ|שולם|מול|פער|לשלם יותר|משלמ", q):
        return Route("agreement_audit", "get_agreement_audit", {"company": co})
    if re.search(r"לא שול|לא קיבלתי|לא שיל[םמ]|לא משלמ|חוב|פער|חייב", q):
        if _unexplained_words(q, co):
            return None        # "על מה לא שולם עומר עמר" — about a PERSON (and maybe a follow-up) → agent lane
        return Route("unpaid", "get_unpaid", {"company": co})
    if re.search(r"(שיעור|אחוז)\s*(ה)?עמלה|מה ההסכם|הסכם עם", q) and co:
        return Route("rate", "get_rate", {"company": co})
    if re.search(r"עזב|עזבו|בוטל|ביטלו|יצאו|לקוחות חדשים|נכנסו", q):
        return Route("changes", "get_production_changes", {})
    if re.search(r"הגדול|מובילים|הכי גדול|הכי גדולים|top", q):
        # "אקסלנס גמל הוא לא המוצר הגדול ביותר" is a CORRECTION about a product, not "top customers"
        if re.search(r"מוצר|עמל|(?:^|\s)(?:הוא|היא|זה)\s+לא\b|לא נכון|טעית|לא פעיל|קופות", q) or co:
            return None
        return Route("top", "top_customers", {"metric": "premium" if "פרמי" in q else "accumulation", "n": 10})
    if (re.search(r"עמל|נכנס|הכנס|קיבלתי", q) and re.search(r"החודש|חודש שעבר|חודש קודם|מגמה|לפי חודש|קיבלתי", q)) \
            or re.search(r"כמה נכנס|כמה הרווחתי|כמה הכנסתי", q):
        # "כמה קיבלתי במרץ?" was answered with the LAST month — a named month is the agent's job;
        # "מה העמלה הצפויה החודש?" got last month's RECEIVED amount (2026-10-10) — expected = agent
        if re.search(r"צפוי|צפי", q) or MONTH_RE.search(q) or (co == "" and re.search(r"(?:^|\s)(?:מ|מה|ב)[א-ת]{3,}(?=\s|\?|$)", q) and _unexplained_words(q, co)):
            return None
        return Route("trend", "get_commission_trend", {"company": co})
    if re.search(r"צביר|פרמי", q) and re.search(r"לפי חברה|בתיק|כמה יש|סך", q):
        return Route("portfolio", "get_portfolio", {"company": co, "metric": "premium" if "פרמי" in q else "accumulation"})
    if re.search(r"מה (כדאי|לעשות|פתוח)|משימות|מה מחכה", q) and not ID_RE.search(q) and not re.search(r"ל?לקוח|הציע|להמליץ", q):
        # "מה כדאי להציע ללקוח X" is advice for ONE customer, not the agent's task list (2026-10-10)
        return Route("tasks", "get_insights", {"kind": "tasks"})
    if re.search(r"תמונת מצב|איך אני עומד|סיכום (של )?התיק|סיכום כללי|כמה לקוחות (יש לי|בתיק)", q):
        if co:   # "כמה לקוחות יש לי במגדל?" answered the whole book (2,175) — 2026-10-10
            return Route("portfolio", "get_portfolio", {"company": co, "metric": "accumulation"})
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
            if float(data.get("total_expected") or 0) < 1:
                return f"ב{data['company']} אין חוב פתוח — {n} רשומות ללא עמלה צפויה (צפי ₪0).", None
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
        if len(rows) == 1 and rows[0].get("clients"):
            r = rows[0]
            bits = [f"{r['clients']} לקוחות", f"{r.get('products') or 0} מוצרים"]
            if r.get("accumulation"):
                bits.append(f"צבירה {_m(r['accumulation'])}")
            if r.get("premium"):
                bits.append(f"פרמיה {_m(r['premium'])}")
            return f"ב{r['label']}: " + " · ".join(bits) + ".", None
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
        if data.get("metric") == "products":
            return ("הכי הרבה מוצרים: " + ", ".join(f"{r['label']} ({r['value']} מוצרים, {r['companies']} חברות)" for r in rows[:3])
                    + ". כיסויים של אותה פוליסה נספרים כמוצר אחד."), "bar"
        return ("הלקוחות הגדולים לפי " + ("פרמיה" if data.get("metric") == "premium" else "צבירה") + ": "
                + ", ".join(f"{r['label']} ({_m(r['value'])})" for r in rows[:3]) + "."), "bar"
    if i == "changes":
        rows = data.get("companies") or []
        if not rows:
            return ((data.get("note") or "אין שינויים להצגה.")
                    + " קובץ המסלקה כן מושווה לפרודוקציה — שאלו \"מה השתנה בקובץ המסלקה?\""), None
        parts = [f"{r['company']}: {r['new']} חדשים, {r['left']} יצאו" for r in rows]
        return "מול הקובץ הקודם — " + " · ".join(parts) + ".", "bar" if sum(r["left"] for r in rows) else None
    if i == "agreement_audit":
        if data.get("company"):
            if data.get("found") is False or data.get("comparable") is False:
                return data.get("note"), None
            s = (f"ב{data['company']}, על המוצרים שנבדקו מול ההסכם: מגיע {_m(data.get('agreement_expected'))}, "
                 f"התקבל {_m(data.get('paid_checked'))} — "
                 + (f"חסר {_m(-float(data.get('gap') or 0))}." if float(data.get('gap') or 0) < 0
                    else f"עודף {_m(data.get('gap'))}."))
            w = data.get("worst_product_customers")
            if w and w.get("summary"):
                sm = w["summary"]
                s += (f" עיקר הפער ב{w['product']}: {sm.get('customers')} לקוחות, חסר {_m(sm.get('shortfall'))}"
                      f" (לחיצה על המוצר בכרטיס 'עמלות בפועל מול ההסכמים' פותחת אותם).")
            return s, "bar"
        rows = data.get("by_company") or []
        if not rows:
            return "אין חברה שאפשר לבדוק מול ההסכם — חסרים שיעורים מפורשים בהסכמים.", None
        lead = rows[0]
        return (f"הפער הגדול מול ההסכם: {lead['label']} — חסר {_m(-lead['value'])} "
                f"(מגיע {_m(lead['agreement_expected'])}, התקבל {_m(lead['paid_checked'])})."), "bar"
    if i == "rate":
        if not data.get("found"):
            return data.get("note"), None
        r = data["rates"][:4]
        return f"ההסכם עם {data['company']}: " + " · ".join(f"{x['product']} {x['rate_pct']}%" + (f" ({x['scope']})" if x.get('scope') else "") for x in r) + ".", None
    if i == "maslaka_status":
        a = data.get("association") or {}
        s = "השיוך למסלקה מאושר." if a.get("status") == "approved" else f"השיוך למסלקה: {a.get('status')}."
        if data.get("open_requests"):
            s += f" {data.get('open_requests_count', len(data['open_requests']))} בקשות פתוחות; הקרובה צפויה ב-{data['open_requests'][0]['answer_expected']}."
        f = data.get("latest_production_file")
        if f:
            got = [c["company"] for c in f["companies_answered"]]
            s += (f" קובץ הפרודוקציה האחרון (נכון ל-{f['valid_as_of']}"
                  + (f", הגיע ב-{f['arrived_at']}" if f.get("arrived_at") else "") + ")"
                  + (f" — הגיעו נתונים מ-{len(got)} חברות: {', '.join(got)}" if got else "")
                  + (f"; עוד {len(f['companies_waiting'])} ממתינות" if f.get("companies_waiting") else "") + ".")
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
    if r.intent == "harb_fetch":
        out = await t.fn(ctx, **r.args)
        if not ctx.proposals and str(out).startswith("שאל את הסוכן: "):
            # fetched recently → ask first ("נשלף היום ב-10:42 — לשלוף שוב?"); "כן" goes to the agent lane
            return {"text": str(out)[len("שאל את הסוכן: "):], "vizs": [], "status": t.status_he}
        if not ctx.proposals:
            # a gate said no (no credential / worker offline / already open) — say exactly that.
            # Never hand it to the model: measured, it wrote "prepared, awaiting approval" AND "not done".
            m = re.match(r"לא הוכנה שליפה: (.*?)\s*הסבר לסוכן", str(out))
            if not m:
                return None
            return {"text": f"לא הכנתי שליפה מהר הביטוח — {m.group(1).strip()}", "vizs": [], "status": t.status_he}
        from app.services.agent.loop import proposal_line
        p = ctx.proposals[-1]
        return {"text": proposal_line(p), "vizs": [], "status": t.status_he, "proposal": p}
    if r.intent in ("record_call", "stop_call"):
        await t.fn(ctx, **r.args)
        from app.services.agent.loop import proposal_line
        p = ctx.proposals[-1]
        return {"text": proposal_line(p), "vizs": [], "status": t.status_he, "proposal": p}
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


def followup_question(question: str, history: list[dict] | None) -> str | None:
    """"ועם הפניקס?" / "ובהראל?" after "מה ההסכם שלי עם מגדל?" means the SAME question about the new
    company — measured: the agent answered unpaid instead of the agreement. Returns the previous user
    question with the company swapped, or None when this isn't such a follow-up."""
    q = " ".join((question or "").split())
    if not history or len(q.split()) > 4 or not re.match(r"^ו", q):
        return None
    new = _company(q)
    prev = next((t.get("text") or "" for t in reversed(history) if t.get("role") == "user"), "")
    old = _company(prev)
    if not new or new == old or not prev:
        return None
    if not old:                # "כמה לקוחות יש לי?" → "ובהראל?" = the same question, at הראל
        return prev.rstrip(" ?") + f" ב{new}?"
    return re.sub(re.escape(old), new, prev, count=1)
