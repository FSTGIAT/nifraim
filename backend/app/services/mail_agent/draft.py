"""Draft a reply in the agent's voice — Claude Sonnet, grounded, never sent here."""
from __future__ import annotations

import json

from app.services.ai_answer_validator import _extract_currency_amounts, validate_answer

from .llm import HAIKU, SONNET, call_tool

DRAFT_TOOL = {
    "name": "write_reply",
    "description": "The reply email the agent will review before sending.",
    "input_schema": {
        "type": "object",
        "properties": {
            "subject": {"type": "string"},
            "body": {"type": "string", "description": "Plain-text Hebrew email body, signed with the agent's name."},
            "missing": {"type": "array", "items": {"type": "string"},
                        "description": "Facts the reply needs but that are NOT in the data you were given."},
        },
        "required": ["subject", "body"],
    },
}

SYSTEM = (
    "אתה כותב טיוטת תשובה למייל, בשם סוכן ביטוח ישראלי. הסוכן יקרא, יערוך ויאשר לפני שליחה.\n"
    "כללים מחייבים:\n"
    "1. כתוב בעברית, מנומס וענייני, בגוף ראשון בשם הסוכן, וחתום בשמו.\n"
    "2. השתמש רק בעובדות מתוך 'נתוני המערכת' ומתוך המייל עצמו. אסור להמציא סכומים, מספרי פוליסה, "
    "תאריכים, סטטוסים או התחייבויות.\n"
    "3. אסור לחשב עמלה משיעור × פרמיה. אסור לטעון דבר על עמלות של חברה שאין לה קובץ נפרעים.\n"
    "4. אם חסר מידע כדי לענות — כתוב בגוף המייל [להשלים: ...] במקום המתאים, ורשום אותו ב-missing.\n"
    "5. אל תבטיח דבר בשם הסוכן מעבר למה שמתבקש לעניין."
)


def _source_block(facts: dict) -> str:
    return json.dumps(facts, ensure_ascii=False, indent=1, default=str)


async def draft_reply(*, agent_name: str, sender_label: str, subject: str, own_text: str,
                      summary: str, facts: dict):
    """Returns (result dict with 'warnings', model, usage)."""
    source = _source_block(facts)
    user = (
        f"שם הסוכן: {agent_name}\n"
        f"המייל התקבל מ: {sender_label}\n"
        f"נושא: {subject}\n"
        f"סיכום: {summary}\n"
        f"--- המייל ---\n{own_text[:6000]}\n"
        f"--- נתוני המערכת (המקור היחיד לעובדות) ---\n{source}"
    )
    result, model, usage = await call_tool(
        models=[SONNET, HAIKU], system=SYSTEM, tool=DRAFT_TOOL, max_tokens=2000, user=user,
    )
    body = result.get("body", "")
    known = source + "\n" + own_text
    warnings = list(validate_answer(body, known).warnings)
    # validate_answer abstains when the source has no numbers at all; a draft
    # quoting ₪ amounts with nothing to back them is exactly what to flag.
    if not warnings and _extract_currency_amounts(body) and not _extract_currency_amounts(known):
        warnings.append("הטיוטה מזכירה סכומים שלא מופיעים במייל או בנתוני המערכת — בדקו לפני שליחה")
    for m in result.get("missing") or []:
        warnings.append(f"חסר מידע: {m}")
    result["warnings"] = warnings
    return result, model, usage
