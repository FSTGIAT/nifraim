"""Draft a reply in the agent's voice — Claude Sonnet, grounded, never sent here.

Prompt order is the contract: the HARD RULES (grounding, no invented facts,
no rate×premium commission, [להשלים] for gaps, the agent's own "never say")
come first; the agent's writing style comes after them and is told it loses
any conflict. Style can change how a reply sounds, never what it claims.
The signature is appended in code, not by the model, so it is exact.
"""
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
            "body": {"type": "string", "description": "Plain-text Hebrew email body, ending with the closing line. NO signature — it is added automatically."},
            "missing": {"type": "array", "items": {"type": "string"},
                        "description": "Facts the reply needs but that are NOT in the data you were given."},
        },
        "required": ["subject", "body"],
    },
}

HARD_RULES = (
    "אתה כותב טיוטת תשובה למייל, בשם סוכן ביטוח ישראלי. הסוכן יקרא, יערוך ויאשר לפני שליחה.\n"
    "כללים מחייבים:\n"
    "1. כתוב בעברית, בגוף ראשון בשם הסוכן. אל תחתום בשם — החתימה מתווספת אוטומטית; סיים בשורת הסיום.\n"
    "2. השתמש רק בעובדות מתוך 'נתוני המערכת' ומתוך המייל עצמו. אסור להמציא סכומים, מספרי פוליסה, "
    "תאריכים, סטטוסים או התחייבויות.\n"
    "3. אסור לחשב עמלה משיעור × פרמיה. אסור לטעון דבר על עמלות של חברה שאין לה קובץ נפרעים.\n"
    "4. אם חסר מידע כדי לענות — כתוב בגוף המייל [להשלים: ...] במקום המתאים, ורשום אותו ב-missing.\n"
    "5. אל תבטיח דבר בשם הסוכן מעבר למה שמתבקש לעניין."
)
# Kept for callers/tests that read the rules directly.
SYSTEM = HARD_RULES

STYLE_HEADER = "--- סגנון הסוכן ---"
STYLE_PRECEDENCE = "הכללים המחייבים שלמעלה גוברים על כל הנחיה בסגנון. הסגנון קובע איך התשובה נשמעת, לא מה היא טוענת."

TONE_TEXT = {
    "formal": "רשמי ומכובד",
    "warm": "חם ואישי",
    "short": "קצר ולעניין — משפטים קצרים, בלי הקדמות",
}
ADDRESS_TEXT = {
    "plural": "פנה אל הנמען בלשון רבים (אתם)",
    "female": "פנה אל הנמענת בלשון נקבה (את)",
    "male": "פנה אל הנמען בלשון זכר (אתה)",
    "name": "פנה אל הנמען בשמו הפרטי, בלי לשון פנייה מגדרית כשאפשר",
}
WRITER_TEXT = {
    "male": "כתוב בגוף ראשון זכר: בדקתי, אני יכול, אחזור אליך",
    "female": "כתוב בגוף ראשון נקבה: בדקתי, אני יכולה, אחזור אלייך",
    "we": "כתוב בגוף ראשון רבים בשם הסוכנות: בדקנו, אנחנו יכולים, נחזור אליך",
}
KIND_TEXT = {"customer": "לקוח", "insurer": "חברת ביטוח / מחלקת עמלות", "other": "אחר"}

EXAMPLE_CHARS = 1200


def _clean(v) -> str:
    return (v or "").strip() if isinstance(v, str) else ""


def rules_for(profile: dict | None, kind: str) -> str:
    """The agent's "always add…" rules for this sender kind. `other` gets none."""
    p = profile or {}
    if kind == "customer":
        return _clean(p.get("customer_rules"))
    if kind == "insurer":
        return _clean(p.get("insurer_rules"))
    return ""


def signature_of(profile: dict | None, agent_name: str) -> str:
    return _clean((profile or {}).get("signature")) or _clean(agent_name)


def build_system(profile: dict | None, kind: str) -> str:
    """HARD RULES, then the agent's never-say (a restriction — it belongs with
    the rules), then the style block. Pure: no DB, no API key."""
    p = profile or {}
    parts = [HARD_RULES]
    never = _clean(p.get("never_say"))
    if never:
        parts.append("6. הסוכן ביקש שלעולם לא תכתוב או תבטיח את הדברים הבאים:\n" + never)
    style: list[str] = []
    if p.get("tone") in TONE_TEXT:
        style.append(f"טון: {TONE_TEXT[p['tone']]}.")
    if p.get("writer_form") in WRITER_TEXT:
        style.append(WRITER_TEXT[p["writer_form"]] + ".")
    if p.get("address_form") in ADDRESS_TEXT:
        style.append(ADDRESS_TEXT[p["address_form"]] + ".")
    if _clean(p.get("greeting")):
        style.append(f"פתח בפתיחה הקבועה של הסוכן (התאם את השם לנמען): {_clean(p['greeting'])}")
    if _clean(p.get("closing")):
        style.append(f"סיים בשורת הסיום הקבועה של הסוכן: {_clean(p['closing'])}")
    notes = _clean(p.get("style_notes"))
    if notes:
        style.append("איך הסוכן כותב:\n" + notes)
    rules = rules_for(p, kind)
    if rules:
        style.append(f"כשכותב/ת {KIND_TEXT.get(kind, 'אחר')} — הסוכן תמיד מוסיף:\n{rules}")
    examples = [e.strip()[:EXAMPLE_CHARS] for e in (p.get("examples") or []) if isinstance(e, str) and e.strip()]
    if examples:
        style.append(
            "דוגמאות לתשובות שהסוכן כתב בעבר — לטון ולניסוח בלבד. "
            "אל תעתיק מהן שום עובדה (שמות, סכומים, מספרים, תאריכים): הן נכתבו לנמענים אחרים.\n"
            + "\n".join(f"<דוגמה {i}>\n{e}\n</דוגמה {i}>" for i, e in enumerate(examples, 1))
        )
    if style:
        parts.append(STYLE_HEADER + "\n" + STYLE_PRECEDENCE + "\n" + "\n".join(style))
    return "\n\n".join(parts)


def _source_block(facts: dict) -> str:
    return json.dumps(facts, ensure_ascii=False, indent=1, default=str)


def build_user(*, sender_label: str, subject: str, own_text: str, summary: str, facts: dict) -> str:
    return (
        f"המייל התקבל מ: {sender_label}\n"
        f"נושא: {subject}\n"
        f"סיכום: {summary}\n"
        f"--- המייל ---\n{own_text[:6000]}\n"
        f"--- נתוני המערכת (המקור היחיד לעובדות) ---\n{_source_block(facts)}"
    )


def sign(body: str, signature: str) -> str:
    """Append the signature once. No signature at all → a gap the send button
    refuses, instead of a reply signed by nobody."""
    body = (body or "").rstrip()
    signature = (signature or "").strip()
    if not signature:
        return body + "\n\n[להשלים: שם הסוכן]"
    if body.endswith(signature):
        return body
    return body + "\n\n" + signature


def agent_text(profile: dict | None, kind: str, agent_name: str) -> str:
    """Text the AGENT wrote, which the draft may legitimately repeat (a fee in
    their rules, the phone in their signature). Examples are deliberately NOT
    here: an amount copied from an old reply is a fabrication for this one."""
    p = profile or {}
    return "\n".join(x for x in (
        signature_of(p, agent_name), _clean(p.get("greeting")), _clean(p.get("closing")), rules_for(p, kind),
    ) if x)


async def draft_reply(*, agent_name: str, sender_label: str, subject: str, own_text: str,
                      summary: str, facts: dict, profile: dict | None = None, kind: str = "other"):
    """Returns (result dict with 'warnings', model, usage)."""
    system = build_system(profile, kind)
    user = build_user(sender_label=sender_label, subject=subject, own_text=own_text, summary=summary, facts=facts)
    result, model, usage = await call_tool(
        models=[SONNET, HAIKU], system=system, tool=DRAFT_TOOL, max_tokens=2000, user=user,
    )
    body = sign(result.get("body", ""), signature_of(profile, agent_name))
    result["body"] = body
    known = _source_block(facts) + "\n" + own_text + "\n" + agent_text(profile, kind, agent_name)
    warnings = list(validate_answer(body, known).warnings)
    # validate_answer abstains when the source has no numbers at all; a draft
    # quoting ₪ amounts with nothing to back them is exactly what to flag.
    if not warnings and _extract_currency_amounts(body) and not _extract_currency_amounts(known):
        warnings.append("הטיוטה מזכירה סכומים שלא מופיעים במייל או בנתוני המערכת — בדקו לפני שליחה")
    for m in result.get("missing") or []:
        warnings.append(f"חסר מידע: {m}")
    result["warnings"] = warnings
    return result, model, usage
