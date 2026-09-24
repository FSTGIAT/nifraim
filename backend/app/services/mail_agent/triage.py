"""Classify one incoming email and summarise it — Claude Haiku, strict JSON."""
from __future__ import annotations

from .llm import HAIKU, SONNET, call_tool

CATEGORIES = ("commission_reply", "report_file", "customer_question", "info", "other")
ACTIONS = ("reply", "import_file", "none")

TRIAGE_TOOL = {
    "name": "triage_email",
    "description": "Record how this email should be handled.",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {"type": "string", "enum": list(CATEGORIES),
                         "description": "commission_reply = an insurer answering about commissions/payments; "
                                        "report_file = mail whose point is an attached report/file; "
                                        "customer_question = a customer asking something; "
                                        "info = informational, nothing to do; other = anything else."},
            "summary": {"type": "string", "description": "1-3 short sentences IN HEBREW: what the sender says or asks."},
            "needs_reply": {"type": "boolean", "description": "True only if the sender asks something or expects an answer."},
            "suggested_action": {"type": "string", "enum": list(ACTIONS)},
            "id_numbers": {"type": "array", "items": {"type": "string"},
                           "description": "Israeli ID numbers (ת.ז) exactly as written in the email."},
            "policy_numbers": {"type": "array", "items": {"type": "string"}},
            "company": {"type": "string", "description": "Insurance company named in the email, if any; else empty."},
            "amounts_quoted": {"type": "array", "items": {"type": "string"},
                               "description": "Money amounts copied VERBATIM from the email text. Never compute or infer."},
        },
        "required": ["category", "summary", "needs_reply", "suggested_action"],
    },
}

SYSTEM = (
    "אתה עוזר לסוכן ביטוח ישראלי לטפל בדואר העבודה שלו. תפקידך לסווג מייל אחד ולסכם אותו. "
    "הסתמך רק על מה שכתוב במייל. אל תמציא מספרים, סכומים, שמות או פרטים. "
    "סכומים והמספרים מועתקים מילה במילה מהמייל בלבד. הסיכום בעברית, קצר וענייני."
)


def _prompt(*, sender_label: str, sender_kind: str, subject: str, own_text: str, attachments: list[dict]) -> str:
    att = ", ".join(a.get("name", "") for a in attachments) or "אין"
    return (
        f"שולח: {sender_label} (סוג: {sender_kind})\n"
        f"נושא: {subject}\n"
        f"קבצים מצורפים: {att}\n"
        f"--- תוכן המייל (ללא הציטוט של השרשור) ---\n{own_text[:6000]}"
    )


async def triage(*, sender_label: str, sender_kind: str, subject: str, own_text: str, attachments: list[dict]):
    """Returns (result dict, model, usage)."""
    return await call_tool(
        models=[HAIKU, SONNET], system=SYSTEM, tool=TRIAGE_TOOL, max_tokens=800,
        user=_prompt(sender_label=sender_label, sender_kind=sender_kind, subject=subject,
                     own_text=own_text, attachments=attachments),
    )
