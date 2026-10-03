"""Claude reads one call transcript and returns a Hebrew summary + structured insights.

Reuses mail_agent.llm.call_tool (forced JSON tool, model fallback). The model sees the
transcript only — it may not invent customers, amounts or dates that weren't said.
"""
from __future__ import annotations

from app.services.mail_agent.llm import HAIKU, call_tool

MODELS = ["claude-sonnet-5-5", "claude-sonnet-5", HAIKU]
MAX_TRANSCRIPT_CHARS = 120_000   # ~2h of speech; longer calls keep head + tail

SYSTEM = """אתה עוזר של סוכן ביטוח ופנסיה בישראל. קיבלת תמלול אוטומטי (ivrit.ai) של שיחה בין הסוכן ללקוח.
התמלול עלול להכיל שגיאות זיהוי — הסק מההקשר, אבל:
- כתוב רק מה שנאמר בשיחה. אל תמציא סכומים, תאריכים, שמות חברות או מוצרים.
- אם שדה לא עלה בשיחה — השאר רשימה ריקה או מחרוזת ריקה.
- כתוב בעברית, בגוף שלישי ("הלקוח ביקש…", "הסוכן התחייב…").
- קצר מאוד: הסוכן קורא את זה בחצי דקה. כל פריט ברשימה — עד 6 מילים, בלי משפטי פתיחה. עדיף פחות פריטים טובים.
- הדובר לא מסומן בתמלול; הסק מי הסוכן ומי הלקוח מתוכן הדברים.
- customer_name / customer_id_number: רק אם נאמרו בשיחה במפורש. אחרת ריק.
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
                    },
                    "required": ["text", "owner"],
                },
            },
            "customer_needs": {"type": "array", "maxItems": 4, "items": {"type": "string"}},
            "products_mentioned": {"type": "array", "maxItems": 4, "items": {"type": "string"}},
            "objections": {"type": "array", "maxItems": 4, "items": {"type": "string"}},
            "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative", "mixed"]},
            "follow_up": {"type": "string", "description": "הצעד הבא לסוכן, עד 10 מילים"},
            "customer_name": {"type": "string", "description": "שם הלקוח כפי שנאמר, או ריק"},
            "customer_id_number": {"type": "string", "description": "ת.ז של הלקוח אם נאמרה, ספרות בלבד, או ריק"},
            "followup_subject": {"type": "string", "description": "נושא המייל ללקוח"},
            "followup_body": {"type": "string", "description": "גוף המייל ללקוח, בלי חתימה"},
        },
        "required": ["title", "tldr", "summary", "key_points", "action_items", "sentiment"],
    },
}


def _clip(text: str) -> str:
    if len(text) <= MAX_TRANSCRIPT_CHARS:
        return text
    half = MAX_TRANSCRIPT_CHARS // 2
    return text[:half] + "\n[…קטע מהאמצע הושמט…]\n" + text[-half:]


def _fmt(segments: list[dict]) -> str:
    def ts(s: float) -> str:
        s = int(s or 0)
        return f"{s // 60:02d}:{s % 60:02d}"
    return "\n".join(f"[{ts(s.get('start'))}] {s.get('text', '')}" for s in segments if s.get("text"))


async def summarize_call(segments: list[dict], duration_s: float | None) -> tuple[dict, str]:
    """Returns (tool_input, model_used). Raises LlmUnavailable."""
    mins = f"{(duration_s or 0) / 60:.0f}"
    user = f"משך השיחה: כ-{mins} דקות.\n\nתמלול:\n{_clip(_fmt(segments))}"
    out, model, _usage = await call_tool(models=MODELS, system=SYSTEM, user=user, tool=TOOL, max_tokens=2600)
    return out, model
