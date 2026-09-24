"""Watch submitted agents' inboxes for the מסלקה's answer to the שיוך form.

The form goes to the helpdesk from the agent's own mailbox (or from Nifraim with
the agent as Reply-To), so the answer lands in the agent's inbox — which, when
they connected it, we can read. For every link in `submitted`:

  1. search their inbox for mail FROM the helpdesk received after submission
     (`mail_intake.search` — stateless, never touches the Hachshara cursors);
  2. read only the NEW text of the reply — the quoted original contains our own
     "אודה לאישור השיוך", which must never count as an approval;
  3. rejection wording → `rejected` (reason = the reply); clear approval wording
     → `approved`; anything else → stay `submitted` but record that a reply
     arrived, so a person decides.

Every reply it matches is recorded on the link (message id, subject, date,
snippet) whether or not it could classify it — an automated approval nobody can
trace back to one email is harder to trust than a manual one.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

from sqlalchemy import select

from app.database import async_session
from app.models.mailbox_config import MailboxConfig
from app.models.maslaka_agent_link import SUBMITTED, MaslakaAgentLink
from app.services.mail_intake import MailIntakeError
from app.services.mail_intake.search import FoundMessage, find_messages_from

from . import association

logger = logging.getLogger(__name__)

APPROVED_WORDS = (
    "אושר", "אושרה", "אושרו", "מאושר", "מאושרת", "שויך", "שויכה", "שויכו", "משויך",
    "השיוך בוצע", "בוצע שיוך", "בוצע השיוך", "שיוך בוצע", "השיוך הושלם", "הושלם השיוך",
    "הבקשה בוצעה", "טופלה בהצלחה", "בוצע בהצלחה",
    "approved", "has been linked", "completed successfully",
)
# Checked FIRST: "לא אושר" contains "אושר".
REJECTED_WORDS = (
    "לא אושר", "לא אושרה", "נדחה", "נדחתה", "נדחית", "לא ניתן לשייך", "לא ניתן לבצע",
    "חסר", "חסרה", "חסרים", "חסרות", "לא תקין", "לא תקינה", "יש לתקן", "נא לתקן",
    "נא להשלים", "יש להשלים", "נא לשלוח שוב", "נא להעביר מחדש",
    "rejected", "declined", "missing", "incomplete",
)

# Where a reply's own text ends and the quoted original begins.
_QUOTE_START = re.compile(
    r"^\s*(>|-{3,}\s*(original message|הודעה מקורית)|_{8,}|"
    r"(from|מאת|sent|נשלח)\s*:|"
    r"‫?\s*(on|בתאריך)\s.+(wrote|כתב|כתבה|מאת).*$)",
    re.IGNORECASE,
)


def reply_text(text: str) -> str:
    """The reply's own words, with the quoted thread cut off."""
    out = []
    for line in (text or "").splitlines():
        if _QUOTE_START.match(line):
            break
        out.append(line)
    return "\n".join(out).strip()


def classify(text: str) -> str:
    """'rejected' | 'approved' | 'unclear' — from the reply's own text only."""
    t = " ".join(reply_text(text).lower().split())
    if not t:
        return "unclear"
    if any(w in t for w in REJECTED_WORDS):
        return "rejected"
    if any(w in t for w in APPROVED_WORDS):
        return "approved"
    return "unclear"


# Out-of-office / auto-replies never decide anything, even when they happen to
# contain "אושר". (Graph returns no headers here, so this is subject-based on
# both providers; IMAP additionally honours Auto-Submitted in search.py.)
_AUTO_REPLY = re.compile(
    r"(automatic reply|auto[- ]?reply|out of (the )?office|מענה אוטומטי|תשובה אוטומטית|"
    r"הודעה אוטומטית|אינני במשרד|מחוץ למשרד)",
    re.IGNORECASE,
)


def _is_auto_reply(msg: FoundMessage) -> bool:
    return msg.auto_submitted or bool(_AUTO_REPLY.search(msg.subject or ""))


def _is_our_own_mail(link: MaslakaAgentLink, msg: FoundMessage) -> bool:
    """The form we sent, seen in the inbox (dev: helpdesk == agent's address;
    also a CC-to-self). Matched by Message-ID, and by the untouched subject as a
    second guard in case a relay rewrote the ID."""
    if link.sent_message_id and msg.message_id == link.sent_message_id:
        return True
    return msg.subject.strip().startswith("בקשת שיוך לבית תוכנה")


async def check_link(db, link: MaslakaAgentLink, cfg: MailboxConfig) -> str | None:
    """Check one submitted agent. Returns the decision applied, or None."""
    since = (link.submitted_at or datetime.utcnow()) - timedelta(minutes=5)
    messages = await find_messages_from(db, cfg, sender=association.helpdesk_email(), since=since)
    replies = [m for m in messages if not _is_our_own_mail(link, m) and not _is_auto_reply(m)]
    if not replies:
        return None

    newest = replies[0]
    if newest.message_id and newest.message_id == link.reply_message_id:
        return None                                   # already recorded this one

    own = reply_text(newest.text)
    link.reply_message_id = newest.message_id[:255] or None
    link.reply_received_at = newest.received_at
    link.reply_subject = newest.subject[:500]
    link.reply_snippet = own[:2000] or newest.text[:2000]

    decision = classify(newest.text)
    if decision == "approved":
        link.decided_via = "mailbox"
        await association.mark_approved(db, link)
    elif decision == "rejected":
        link.decided_via = "mailbox"
        await association.mark_rejected(db, link, own[:500] or newest.subject)
    else:
        await db.commit()                            # recorded; a person decides
    logger.info(
        "maslaka.approval_watch: user=%s reply %s → %s",
        link.user_id, newest.message_id, decision,
    )
    return decision


async def run_approval_watch() -> None:
    """Scheduler entry point. One session and one `try` per agent: a locked
    mailbox must not starve the others."""
    try:
        async with async_session() as db:
            pairs = (await db.execute(
                select(MaslakaAgentLink.id, MailboxConfig.id)
                .join(MailboxConfig, MailboxConfig.user_id == MaslakaAgentLink.user_id)
                .where(
                    MaslakaAgentLink.status == SUBMITTED,
                    MailboxConfig.is_active.is_(True),
                    MailboxConfig.mail_host.in_(("google", "microsoft")),
                )
            )).all()
    except Exception as e:  # noqa: BLE001
        logger.error("maslaka.approval_watch: could not list submitted agents: %s", e)
        return

    for link_id, cfg_id in pairs:
        try:
            async with async_session() as db:
                link = await db.get(MaslakaAgentLink, link_id)
                cfg = await db.get(MailboxConfig, cfg_id)
                if link and cfg and link.status == SUBMITTED:
                    await check_link(db, link, cfg)
                    await db.commit()               # persists a rotated Graph token too
        except MailIntakeError as e:
            logger.warning("maslaka.approval_watch: mailbox error for link=%s: %s", link_id, e.code)
        except Exception:  # noqa: BLE001
            logger.exception("maslaka.approval_watch: failed for link=%s", link_id)
