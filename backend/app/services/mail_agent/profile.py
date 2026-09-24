"""The agent's writing-style profile: load/save, and "learn from my sent mail".

Learning reads ONLY the agent's own sent replies TO senders on their
watch-list, keeps only the reply's own words (quoted thread cut off), and asks
the AI to describe the style. The examples it returns are the agent's texts
verbatim, picked by index — the model never rewrites them.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mail_agent_profile import ADDRESS_FORMS, TONES, WRITER_FORMS, MailAgentProfile
from app.models.mail_watch_sender import MailWatchSender
from app.models.mailbox_config import MailboxConfig
from app.services.maslaka.approval_watch import reply_text
from app.utils.crypto import decrypt, encrypt

from .llm import HAIKU, SONNET, call_tool

KEY = "MAILBOX_ENCRYPTION_KEY"
TEXT_FIELDS = ("signature", "greeting", "closing", "customer_rules", "insurer_rules", "never_say", "style_notes")
MAX_EXAMPLES = 3
EXAMPLE_CHARS = 1200
LEARN_DAYS = 365
LEARN_MAX_REPLIES = 12


class NothingToLearn(RuntimeError):
    pass


def _examples(row: MailAgentProfile | None) -> list[str]:
    if not row or not row.encrypted_examples:
        return []
    try:
        data = json.loads(decrypt(row.encrypted_examples, key_env=KEY))
    except Exception:  # noqa: BLE001 — a rotated key must not break drafting
        return []
    return [x for x in data if isinstance(x, str)][:MAX_EXAMPLES]


def as_dict(row: MailAgentProfile | None) -> dict | None:
    """The profile as the prompt builder consumes it (None = no profile)."""
    if not row:
        return None
    d = {f: getattr(row, f) for f in TEXT_FIELDS}
    d.update(tone=row.tone, address_form=row.address_form, writer_form=row.writer_form, examples=_examples(row))
    return d


async def get_row(db: AsyncSession, user_id: uuid.UUID) -> MailAgentProfile | None:
    return await db.get(MailAgentProfile, user_id)


async def load(db: AsyncSession, user_id: uuid.UUID) -> dict | None:
    return as_dict(await get_row(db, user_id))


def sanitize(data: dict) -> dict:
    """Clamp an incoming (possibly unsaved) profile to what the prompt accepts."""
    out: dict = {}
    for f in TEXT_FIELDS:
        v = data.get(f)
        if isinstance(v, str):
            out[f] = v.strip()[:255 if f in ("greeting", "closing") else 4000] or None
    if data.get("tone") in TONES:
        out["tone"] = data["tone"]
    if data.get("address_form") in ADDRESS_FORMS:
        out["address_form"] = data["address_form"]
    if data.get("writer_form") in WRITER_FORMS:
        out["writer_form"] = data["writer_form"]
    ex = data.get("examples")
    if isinstance(ex, list):
        out["examples"] = [e.strip()[:EXAMPLE_CHARS] for e in ex if isinstance(e, str) and e.strip()][:MAX_EXAMPLES]
    return out


def apply(row: MailAgentProfile, data: dict) -> None:
    clean = sanitize(data)
    for f in TEXT_FIELDS:
        if f in data:
            setattr(row, f, clean.get(f))
    for f in ("tone", "address_form", "writer_form"):
        if f in data:
            setattr(row, f, clean.get(f))
    if "examples" in data:
        ex = clean.get("examples") or []
        row.encrypted_examples = encrypt(json.dumps(ex, ensure_ascii=False), key_env=KEY) if ex else None


# ── learn from sent mail ───────────────────────────────────────────────────
LEARN_TOOL = {
    "name": "describe_style",
    "description": "How this insurance agent writes email, from their own sent replies.",
    "input_schema": {
        "type": "object",
        "properties": {
            "enough_material": {"type": "boolean",
                                "description": "False when these are not real personal replies (forwards, system output, lists) or too few to describe a style."},
            "style_notes": {"type": "array", "items": {"type": "string"},
                            "description": "3-6 short Hebrew bullets: length, register, typical phrases, structure. About HOW they write, never about specific customers or facts."},
            "tone": {"type": "string", "enum": list(TONES)},
            "address_form": {"type": "string", "enum": list(ADDRESS_FORMS)},
            "writer_form": {"type": "string", "enum": list(WRITER_FORMS),
                            "description": "The agent's own first person: male (אני יכול), female (אני יכולה), or we (אנחנו)."},
            "greeting": {"type": "string", "description": "Their usual opening line, generalised (no specific name). Empty if none."},
            "closing": {"type": "string", "description": "Their usual closing line before the signature. Empty if none."},
            "signature": {"type": "string", "description": "Their signature block as it appears (name, title, phone), or empty."},
            "example_indexes": {"type": "array", "items": {"type": "integer"},
                                "description": "1-3 indexes of genuine personal replies that best show their style. Never forwards, lists or machine output."},
        },
        "required": ["enough_material", "style_notes", "tone", "example_indexes"],
    },
}

LEARN_SYSTEM = (
    "אתה מנתח סגנון כתיבה. לפניך תשובות מייל שסוכן ביטוח ישראלי כתב בעצמו. "
    "תאר איך הוא כותב — אורך, רשמיות, פתיחה, סיום, ביטויים חוזרים — כך שאפשר יהיה לכתוב בשמו תשובות שנשמעות כמוהו. "
    "אל תכלול בתיאור שמות לקוחות, מספרים, סכומים או פרטים ספציפיים. כתוב בעברית."
)


_FORWARD = re.compile(r"(?im)^\s*-{3,}\s*(forwarded message|original message|הודעה שהועברה|הודעה מקורית)")
_FWD_SUBJECT = re.compile(r"(?i)^\s*(fwd?|fw|הועבר)\s*:")


def _own_words(text: str) -> str:
    return (reply_text(text) or "").strip()


def _is_reply(subject: str, own: str) -> bool:
    """A forward carries someone else's words, not the agent's voice."""
    return len(own) >= 20 and not _FWD_SUBJECT.match(subject or "") and not _FORWARD.search(own)


async def learn(db: AsyncSession, user_id: uuid.UUID) -> tuple[dict, str, object]:
    """Returns (suggestion, model, usage). Raises NothingToLearn when there is
    no sent reply to a watched sender to learn from."""
    from app.services.mail_intake.search import find_sent_to

    cfg = (await db.execute(select(MailboxConfig).where(MailboxConfig.user_id == user_id))).scalar_one_or_none()
    if not cfg or not cfg.is_active or cfg.mail_host not in ("google", "microsoft"):
        raise NothingToLearn("no_mailbox")
    matchers = list((await db.execute(
        select(MailWatchSender.address).where(MailWatchSender.user_id == user_id))).scalars().all())
    if not matchers:
        raise NothingToLearn("no_senders")
    sent = await find_sent_to(db, cfg, matchers=matchers, since=datetime.utcnow() - timedelta(days=LEARN_DAYS))
    replies: list[str] = []
    for m in sent:
        t = _own_words(m.text)
        if _is_reply(m.subject, t) and t not in replies:
            replies.append(t[:EXAMPLE_CHARS])
        if len(replies) >= LEARN_MAX_REPLIES:
            break
    if not replies:
        raise NothingToLearn("no_sent")
    user = "\n\n".join(f"<תשובה {i}>\n{t}\n</תשובה {i}>" for i, t in enumerate(replies, 1))
    result, model, usage = await call_tool(
        models=[SONNET, HAIKU], system=LEARN_SYSTEM, tool=LEARN_TOOL, max_tokens=1200, user=user,
    )
    if result.get("enough_material") is False:
        raise NothingToLearn("not_enough")
    picks = []
    for i in result.get("example_indexes") or []:
        if isinstance(i, int) and 1 <= i <= len(replies) and replies[i - 1] not in picks:
            picks.append(replies[i - 1])
    suggestion = sanitize({
        "style_notes": "\n".join(f"• {n.strip()}" for n in (result.get("style_notes") or []) if isinstance(n, str) and n.strip()),
        "tone": result.get("tone"), "address_form": result.get("address_form"),
        "writer_form": result.get("writer_form"),
        "greeting": result.get("greeting") or "", "closing": result.get("closing") or "",
        "signature": result.get("signature") or "",
        "examples": picks[:MAX_EXAMPLES],
    })
    suggestion["read_count"] = len(replies)
    return suggestion, model, usage
