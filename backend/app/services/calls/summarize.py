"""Claude reads one call transcript and returns a Hebrew summary + structured insights.

Reuses mail_agent.llm.call_tool (forced JSON tool, model fallback). The model sees the
transcript only — it may not invent customers, amounts or dates that weren't said.
"""
from __future__ import annotations

import re

from app.services.calls.categories import CATEGORIES, URGENCY
from app.services.mail_agent.llm import HAIKU, call_tool

MODELS = ["claude-sonnet-5-5", "claude-sonnet-5", HAIKU]
MAX_TRANSCRIPT_CHARS = 120_000   # ~2h of speech; longer calls keep head + tail

SPEAKERS_LABELLED = ("הדוברים מסומנים בתמלול S1 / S2 (זיהוי קולי אוטומטי). קבע מי מהם הסוכן ומי הלקוח והחזר ב-speaker_roles. "
                     "שייך משימות והתחייבויות לפי מי שאמר אותן. customer_quotes: עד 3 משפטים קצרים שהלקוח אמר, מילה במילה.")
SPEAKERS_UNLABELLED = "הדובר לא מסומן בתמלול; הסק מי הסוכן ומי הלקוח מתוכן הדברים."

SYSTEM = """אתה עוזר של סוכן ביטוח ופנסיה בישראל. קיבלת תמלול אוטומטי (ivrit.ai) של שיחה בין הסוכן ללקוח.
התמלול עלול להכיל שגיאות זיהוי — הסק מההקשר, אבל:
- כתוב רק מה שנאמר בשיחה. אל תמציא סכומים, תאריכים, שמות חברות או מוצרים.
- אם שדה לא עלה בשיחה — השאר רשימה ריקה או מחרוזת ריקה.
- כתוב בעברית, בגוף שלישי ("הלקוח ביקש…", "הסוכן התחייב…").
- קצר מאוד: הסוכן קורא את זה בחצי דקה. כל פריט ברשימה — עד 6 מילים, בלי משפטי פתיחה. עדיף פחות פריטים טובים.
- {speakers}
- customer_name / customer_id_number: רק אם נאמרו בשיחה במפורש. אחרת ריק.
- category: הנושא העיקרי של השיחה, אחד מהרשימה. topics: עד 4 תגיות קצרות. companies_mentioned: חברות ביטוח/גופים שהוזכרו בשמם.
- action_items.due_date: אם נאמר מועד ("עד יום חמישי", "מחר", "בסוף החודש") — התאריך עצמו YYYY-MM-DD לפי תאריך השיחה שבראש ההודעה. אחרת ריק.
- followup_subject / followup_body: מייל קצר שהסוכן ישלח ללקוח אחרי השיחה, בגוף ראשון של הסוכן ("שלום <שם>, תודה על השיחה"),
  מה סיכמנו והצעדים הבאים עם המועדים שנאמרו. 4–8 שורות, חם ומקצועי, בלי חתימה (נוסיף אותה), בלי מידע שלא נאמר."""

TOOL = {
    "name": "call_summary",
    "description": "סיכום ותובנות משיחת סוכן–לקוח",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "כותרת של 3–6 מילים לשיחה"},
            "tldr": {"type": "string", "description": "שורה אחת, עד 14 מילים: מה קרה ומה הלאה"},
            "summary": {"type": "string", "description": "2–3 משפטים קצרים"},
            "key_points": {"type": "array", "maxItems": 4, "items": {"type": "string"}},
            "action_items": {
                "type": "array",
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "owner": {"type": "string", "enum": ["agent", "customer"]},
                        "due": {"type": "string", "description": "מועד כפי שנאמר בשיחה, או ריק"},
                        "due_date": {"type": "string", "description": "המועד כתאריך YYYY-MM-DD, או ריק"},
                    },
                    "required": ["text", "owner"],
                },
            },
            "category": {"type": "string", "enum": list(CATEGORIES), "description": "הנושא העיקרי: " + ", ".join(f"{k}={v}" for k, v in CATEGORIES.items())},
            "topics": {"type": "array", "maxItems": 4, "items": {"type": "string"}, "description": "תגיות קצרות (2–3 מילים)"},
            "companies_mentioned": {"type": "array", "maxItems": 5, "items": {"type": "string"}},
            "urgency": {"type": "string", "enum": list(URGENCY), "description": "high אם יש מועד קרוב/בעיה דחופה"},
            "customer_needs": {"type": "array", "maxItems": 4, "items": {"type": "string"}},
            "products_mentioned": {"type": "array", "maxItems": 4, "items": {"type": "string"}},
            "objections": {"type": "array", "maxItems": 4, "items": {"type": "string"}},
            "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative", "mixed"]},
            "follow_up": {"type": "string", "description": "הצעד הבא לסוכן, עד 10 מילים"},
            "customer_name": {"type": "string", "description": "שם הלקוח כפי שנאמר, או ריק"},
            "customer_id_number": {"type": "string", "description": "ת.ז של הלקוח אם נאמרה, ספרות בלבד, או ריק"},
            "followup_subject": {"type": "string", "description": "נושא המייל ללקוח"},
            "followup_body": {"type": "string", "description": "גוף המייל ללקוח, בלי חתימה"},
            "speaker_roles": {
                "type": "object",
                "description": "רק כשהתמלול מסומן S1/S2: מי הסוכן ומי הלקוח",
                "additionalProperties": {"type": "string", "enum": ["agent", "customer"]},
            },
            "customer_quotes": {"type": "array", "maxItems": 3, "items": {"type": "string"},
                                "description": "ציטוטים מילה במילה של הלקוח, רק כשהדוברים מסומנים"},
        },
        "required": ["title", "tldr", "summary", "key_points", "action_items", "sentiment", "category"],
    },
}


def _clip(text: str) -> str:
    if len(text) <= MAX_TRANSCRIPT_CHARS:
        return text
    half = MAX_TRANSCRIPT_CHARS // 2
    return text[:half] + "\n[…קטע מהאמצע הושמט…]\n" + text[-half:]


def has_speakers(segments: list[dict]) -> bool:
    return any(s.get("speaker") for s in segments)


def _fmt(segments: list[dict]) -> str:
    def ts(s: float) -> str:
        s = int(s or 0)
        return f"{s // 60:02d}:{s % 60:02d}"

    def who(s: dict) -> str:
        return f"{s['speaker']}: " if s.get("speaker") else ""
    return "\n".join(f"[{ts(s.get('start'))}] {who(s)}{s.get('text', '')}" for s in segments if s.get("text"))


def _who(agent_name: str | None, customer_name: str | None) -> str:
    """Names we KNOW (the account + the customer matched by phone number). Without them the
    model guesses from the audio — and a name said on the line ("מדבר קיקו", "בוקר טוב קיקו")
    is as likely the agent's as the customer's: a follow-up once opened "שלום קיקו" to the customer."""
    out = []
    if agent_name:
        out.append(f"הסוכן: {agent_name}. אל תפנה אליו במייל — הוא השולח.")
    if customer_name:
        out.append(f"הלקוח (זוהה לפי מספר הטלפון): {customer_name}. פנה אליו במייל בשמו הפרטי בלבד.")
    elif agent_name:
        out.append("שם הלקוח לא ידוע: במייל פנה בשם רק אם ברור שהוא שם הלקוח ולא של הסוכן, אחרת \"שלום,\".")
    return ("\n".join(out) + "\n\n") if out else ""


_DAYS = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]


def when_line(call_date) -> str:
    """The call's date plus a ready calendar of the next 14 days, so "עד יום חמישי" becomes
    a date by LOOKUP — models get weekday arithmetic wrong (measured: Tuesday + "רביעי" → Thursday)."""
    if not call_date:
        return ""
    from datetime import timedelta
    days = [call_date + timedelta(days=i) for i in range(1, 15)]
    cal = ", ".join(f"יום {_DAYS[d.weekday()]}" + (" (מחר)" if i == 0 else " הבא" if i >= 7 else "") + f"={d.isoformat()}"
                    for i, d in enumerate(days))
    return (f"תאריך השיחה: יום {_DAYS[call_date.weekday()]} {call_date.isoformat()} (היום={call_date.isoformat()})\n"
            f"לוח הימים הבאים (העתק מכאן, אל תחשב): {cal}. \"סוף השבוע\" = יום שישי הקרוב. \"סוף החודש\" = היום האחרון בחודש.\n")


async def summarize_call(segments: list[dict], duration_s: float | None,
                         agent_name: str | None = None, customer_name: str | None = None,
                         call_date=None) -> tuple[dict, str]:
    """Returns (tool_input, model_used). Raises LlmUnavailable."""
    mins = f"{(duration_s or 0) / 60:.0f}"
    user = f"{_who(agent_name, customer_name)}{when_line(call_date)}משך השיחה: כ-{mins} דקות.\n\nתמלול:\n{_clip(_fmt(segments))}"
    system = SYSTEM.replace("{speakers}", SPEAKERS_LABELLED if has_speakers(segments) else SPEAKERS_UNLABELLED)
    out, model, _usage = await call_tool(models=MODELS, system=system, user=user, tool=TOOL, max_tokens=2600)
    return _untag(out), model


_TAG = re.compile(r"</?(?:%s|parameter|invoke)\b[^>]*>" % "|".join(TOOL["input_schema"]["properties"]))


def _untag(v):
    """The model now and then leaks a field's own tag into its value ("…בינתיים.</followup_body>"),
    or writes its newlines escaped ("שלום שרית,\\n\\nתודה…") — both reach the customer's email."""
    if isinstance(v, str):
        return _TAG.sub("", v.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", " ")).strip()
    if isinstance(v, list):
        return [_untag(x) for x in v]
    if isinstance(v, dict):
        return {k: _untag(x) for k, x in v.items()}
    return v


CLASSIFY_TOOL = {
    "name": "call_category",
    "description": "סיווג שיחה שכבר סוכמה",
    "input_schema": {
        "type": "object",
        "properties": {k: TOOL["input_schema"]["properties"][k] for k in ("category", "topics", "companies_mentioned", "urgency")} | {
            "due_dates": {"type": "array", "items": {"type": "string"},
                          "description": "לכל משימה ברשימה, לפי הסדר: YYYY-MM-DD או ריק"},
        },
        "required": ["category", "due_dates"],
    },
}


async def classify_call(title: str, summary: str, action_items: list[dict], transcript: str, call_date=None) -> dict:
    """Category/topics/due dates for a call summarised before categories existed. Cheap (Haiku),
    and it never rewrites the summary or the follow-up the agent may already have sent."""
    tasks = "\n".join(f"{i + 1}. {a.get('text', '')} (מועד: {a.get('due') or '—'})" for i, a in enumerate(action_items or []))
    user = (f"{when_line(call_date)}כותרת: {title}\nסיכום: {summary}\nמשימות:\n{tasks or '—'}\n\n"
            f"תמלול (קטע):\n{(transcript or '')[:6000]}")
    out, _m, _u = await call_tool(models=[HAIKU], system="סווג שיחת סוכן ביטוח–לקוח. רק לפי מה שנאמר.",
                                  user=user, tool=CLASSIFY_TOOL, max_tokens=500)
    return _untag(out)
