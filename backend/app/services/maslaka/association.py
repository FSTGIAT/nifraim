"""The agent ↔ בית תוכנה association — lifecycle, form pre-fill, delivery.

Nifraim is the מסלקה **בית תוכנה** (ח.פ 558638623). Before an agent may transact
through our single vault, the מסלקה must link that agent to our ח.פ, and that
link is created by a paper form the agent signs. This module owns the app side
of that process: hand the agent a pre-filled form, take the signed scan back,
deliver it, and record where they are.

**Not a ייפוי כוח.** Approving an association lets an agent transact at all; it
entitles them to no customer's data. That gate is event 1700, per customer.
"""

from __future__ import annotations

import io
import logging
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.maslaka_agent_link import (
    APPROVED, FORM_DOWNLOADED, NOT_STARTED, REJECTED, SUBMITTED,
    MaslakaAgentLink,
)
from app.utils.crypto import decrypt_bytes, encrypt_bytes

logger = logging.getLogger(__name__)

MASLAKA_KEY = "MASLAKA_ENCRYPTION_KEY"

def helpdesk_email() -> str:
    """The real מסלקה desk by default; overridable per-environment so a dev
    box cannot mail a regulator by accident."""
    return settings.MASLAKA_HELPDESK_EMAIL or "helpdesk@swiftness.co.il"


HELPDESK_EMAIL = "helpdesk@swiftness.co.il"   # display/default only

# Our fixed side of the form — the same for every agent, which is exactly why
# the app fills it rather than asking a non-technical agent to copy a ח.פ by
# hand into a regulator's form.
BEIT_TOCHNA_NAME = "Nifraim.com"
BEIT_TOCHNA_ID = "558638623"

ASSETS = Path(__file__).resolve().parents[2] / "assets" / "maslaka"
BLANK_FORM = ASSETS / "shiyuch_form_blank.pdf"

# Overlay positions, in PDF points from the bottom-left of page 1 (A4:
# 595.32 × 841.92). The form has ZERO AcroForm fields and its labels are a
# sliced scan, so there is nothing to anchor to programmatically — these are
# measured by eye against the blank and live here so calibration is one edit.
#
# CALIBRATED against the currently vendored blank (`בקשת שיוך לבית סוכן`, the
# 1-page text variant published at swiftness.co.il/agents). Measured from the
# label positions, which that variant exposes as real text:
#
#     שם הסוכן/סוכנות   y=645.7  x=431..506     ← fill to its LEFT (RTL)
#     מספר מזהה          y=615.5  x=458.6
#     שם בית הסוכן       y=499.9  x=393.3
#     ח.פ בית הסוכן      y=469.8  x=444.6
#
# ⚠️ These DO NOT transfer to the בית תוכנה variant — that one is a 2-page scan
# with different geometry and a checkbox this variant lacks. Recalibrate when it
# is vendored; that is the whole reason these live in one dict.
FIELD_POSITIONS: dict[str, tuple[float, float]] = {
    "agent_name": (300.0, 645.0),
    # Digit-box rows: (x of the FIRST box, baseline y). Measured by rendering
    # the form to PNG and looking at it — the first attempt put both numbers
    # below and left of their boxes, which extracting text could not reveal.
    "agent_id": (336.0, 620.0),
    # No בית-תוכנה/בית-סוכן choice exists on the 1-page variant; the tick is
    # drawn off-page so it cannot land somewhere misleading.
    "beit_tochna_checkbox": (-100.0, -100.0),
    "beit_tochna_name": (250.0, 497.0),
    "beit_tochna_id": (309.0, 474.0),
}

# Horizontal pitch of one digit box, in points, per row. The מסלקה prints these
# as a row of empty squares; a plain drawString packs the digits together at the
# left and they read as sitting outside the grid.
BOX_PITCH: dict[str, float] = {
    "agent_id": 11.4,
    "beit_tochna_id": 11.9,
}


class FormTemplateMissing(RuntimeError):
    """The blank מסלקה form has not been vendored. Deliberately fatal: serving
    an un-prefilled — or worse, a previously-completed — form is how one agent
    ends up holding another agent's name and signature."""


# ─── Lifecycle ─────────────────────────────────────────────────────────────
async def get_or_create_link(
    db: AsyncSession, *, user_id: uuid.UUID, agent_name: str | None = None,
) -> MaslakaAgentLink:
    """The row is created lazily on first look, so an agent who never opens the
    מסלקה tab carries no association state at all."""
    link = (await db.execute(
        select(MaslakaAgentLink).where(MaslakaAgentLink.user_id == user_id)
    )).scalar_one_or_none()
    if link is None:
        link = MaslakaAgentLink(
            user_id=user_id, status=NOT_STARTED, agent_name=agent_name,
        )
        db.add(link)
        await db.flush()
        await db.commit()
    return link


async def set_agent_identity(
    db: AsyncSession,
    link: MaslakaAgentLink,
    *,
    agent_id_number: str,
    agent_name: str,
    agent_licence_number: str | None = None,
) -> MaslakaAgentLink:
    """`agent_id_number` is what ends up in `MISPAR-MEZAHE-PONE` on the wire, so
    normalise it the same way the events builder does: digits only, and a ת"ז
    keeps its leading zero (043417252 is nine digits, not eight)."""
    digits = "".join(ch for ch in (agent_id_number or "") if ch.isdigit())
    if not digits:
        raise ValueError("מספר זהות חייב להכיל ספרות")
    if len(digits) <= 9:
        digits = digits.zfill(9)
    link.agent_id_number = digits
    link.agent_name = (agent_name or "").strip() or link.agent_name
    if agent_licence_number:
        link.agent_licence_number = agent_licence_number.strip()
    await db.commit()
    return link


async def mark_form_downloaded(db: AsyncSession, link: MaslakaAgentLink) -> None:
    # Only ever moves forward from the earliest state — re-downloading the form
    # after submitting must not walk the status backwards.
    if link.status == NOT_STARTED:
        link.status = FORM_DOWNLOADED
    link.form_downloaded_at = datetime.utcnow()
    await db.commit()


async def record_submission(
    db: AsyncSession,
    link: MaslakaAgentLink,
    *,
    pdf_bytes: bytes,
    filename: str,
    delivery_note: str | None = None,
) -> None:
    """Store the signed form encrypted and flip to `submitted`.

    The scan carries a signature and an identity document, so it is Fernet-
    encrypted with the same key as the raw wire payloads and never lands on disk.
    """
    link.signed_pdf = encrypt_bytes(pdf_bytes, key_env=MASLAKA_KEY)
    link.signed_pdf_filename = filename[:255]
    link.submitted_at = datetime.utcnow()
    link.status = SUBMITTED
    link.rejected_reason = None
    if delivery_note:
        link.delivery_note = delivery_note
    await db.commit()


async def mark_approved(db: AsyncSession, link: MaslakaAgentLink) -> None:
    link.status = APPROVED
    link.approved_at = datetime.utcnow()
    link.rejected_reason = None
    await db.commit()


async def mark_rejected(db: AsyncSession, link: MaslakaAgentLink, reason: str) -> None:
    """Back to `form_downloaded`, not a dead end: the agent corrects the form and
    sends it again."""
    link.status = REJECTED
    link.rejected_reason = (reason or "")[:500]
    await db.commit()


def read_signed_pdf(link: MaslakaAgentLink) -> bytes | None:
    if not link.signed_pdf:
        return None
    return decrypt_bytes(link.signed_pdf, key_env=MASLAKA_KEY)


# ─── Form pre-fill ─────────────────────────────────────────────────────────
def build_prefilled_form(*, agent_name: str, agent_id_number: str) -> bytes:
    """Overlay the agent's details onto the מסלקה's own blank form.

    Not a re-typeset copy: this draws on top of THEIR document, because a
    regulator's form re-created from a screenshot is a form they may refuse.
    """
    if not BLANK_FORM.exists():
        raise FormTemplateMissing(
            f"blank form not vendored at {BLANK_FORM} — see assets/maslaka/README.md"
        )
    _assert_template_is_blank()

    from pypdf import PdfReader, PdfWriter
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    reader = PdfReader(str(BLANK_FORM))
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=A4)
    font = _register_hebrew_font()

    c.setFont(font, 11)
    c.drawString(*FIELD_POSITIONS["agent_name"], _shape_hebrew(agent_name))
    c.setFont("Helvetica", 10)
    _draw_boxed_digits(c, agent_id_number, *FIELD_POSITIONS["agent_id"],
                       pitch=BOX_PITCH["agent_id"])
    _draw_boxed_digits(c, BEIT_TOCHNA_ID, *FIELD_POSITIONS["beit_tochna_id"],
                       pitch=BOX_PITCH["beit_tochna_id"])
    c.setFont("Helvetica", 11)
    c.drawString(*FIELD_POSITIONS["beit_tochna_name"], BEIT_TOCHNA_NAME)
    # לבית תוכנה — always ticked; an agent joining Nifraim is never joining a
    # בית סוכן, and a mis-ticked box sends the association to the wrong entity.
    c.setFont("Helvetica-Bold", 12)
    c.drawString(*FIELD_POSITIONS["beit_tochna_checkbox"], "X")
    c.save()
    packet.seek(0)

    writer = PdfWriter()
    overlay = PdfReader(packet).pages[0]
    for i, page in enumerate(reader.pages):
        if i == 0:
            page.merge_page(overlay)
        writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def _register_hebrew_font() -> str:
    """Heebo ships with the frontend; reuse it rather than vendoring a second
    Hebrew font. Falls back to Helvetica, which renders Hebrew as blanks — so
    the caller gets a visibly wrong form rather than a silently wrong one."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    name = "HeeboForm"
    if name in pdfmetrics.getRegisteredFontNames():
        return name
    for candidate in (
        Path("/home/roygi/test/frontend/src/assets/fonts/Heebo-Regular.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ):
        if candidate.exists():
            try:
                pdfmetrics.registerFont(TTFont(name, str(candidate)))
                return name
            except Exception as e:                                # noqa: BLE001
                logger.warning("maslaka.association: font %s failed: %s", candidate, e)
    logger.warning("maslaka.association: no Hebrew font found — name will not render")
    return "Helvetica"


def _shape_hebrew(text: str) -> str:
    """reportlab has no bidi engine, so a Hebrew string is drawn left-to-right
    and comes out mirrored. Reversing gives the correct visual order for a plain
    run of Hebrew. Numbers inside the string would themselves be reversed, which
    is why only the NAME goes through here — the ת"ז and ח.פ are drawn as plain
    Latin digits (the same trap as the visual-Hebrew parsers elsewhere in this
    repo, where reversing had to protect numeric runs)."""
    return (text or "")[::-1]


# ─── Delivery ──────────────────────────────────────────────────────────────
async def deliver_to_helpdesk(
    *, link: MaslakaAgentLink, pdf_bytes: bytes, agent_email: str,
) -> str:
    """Email the signed form to the מסלקה helpdesk.

    Sent from our own address with the AGENT as `Reply-To`, so Swiftness's reply
    reaches the agent rather than a no-reply mailbox. Sending genuinely *as* the
    agent needs `Mail.Send` (M365, via their tenant admin) or Gmail SMTP — the
    existing mailbox integration is read-only by design (`Mail.Read, never
    Mail.ReadWrite`). That is Part B, a separate project.
    """
    from email.message import EmailMessage

    from app.services.email_service import send_raw_message

    subject = f"בקשת שיוך לבית תוכנה — {link.agent_name or ''} ת\"ז {link.agent_id_number or ''}"
    body = (
        f"שלום,\n\n"
        f"מצורפת בקשת שיוך לבית תוכנה חתומה.\n\n"
        f"שם הסוכן: {link.agent_name or ''}\n"
        f"מספר מזהה: {link.agent_id_number or ''}\n"
        f"בית תוכנה: {BEIT_TOCHNA_NAME} (ח.פ {BEIT_TOCHNA_ID})\n\n"
        f"נא לאשר את השיוך. לתשובה ניתן להשיב למייל זה — התשובה תגיע ישירות לסוכן.\n\n"
        f"תודה,\n{BEIT_TOCHNA_NAME}\n"
    )

    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM_EMAIL or "no-reply@nifraim.com"
    msg["To"] = helpdesk_email()
    if agent_email:
        msg["Reply-To"] = agent_email
    msg["Subject"] = subject
    msg.set_content(body)
    msg.add_attachment(
        pdf_bytes, maintype="application", subtype="pdf",
        filename=link.signed_pdf_filename or "shiyuch.pdf",
    )
    await send_raw_message(msg)
    return helpdesk_email()


def _template_filled_text() -> str:
    """Text in the template that can only have come from a FILLED copy.

    An earlier version of this flagged *any* extractable text, on the reasoning
    that the blank is a pure scan. That was wrong: Swiftness also publish
    text-based variants whose own labels extract as ~600 characters, so the rule
    would have rejected a perfectly good blank. What never appears on a blank is
    OUR side of the form — `Nifraim.com` and ח.פ 558638623 are written in by the
    agent, so their presence is the actual signal that this is someone's
    completed copy. Measured 2026-09-24: the file first supplied as "clean" came
    back as `משה היב כהן / Nifraim.com / 24/09/2026`.
    """
    try:
        from pypdf import PdfReader

        text = "".join((pg.extract_text() or "") for pg in PdfReader(str(BLANK_FORM)).pages)
        hits = [m for m in (BEIT_TOCHNA_NAME, BEIT_TOCHNA_ID) if m in text]
        return " / ".join(hits)
    except Exception as e:                                       # noqa: BLE001
        logger.warning("maslaka.association: cannot inspect template: %s", e)
        return ""


def _assert_template_is_blank() -> None:
    """Refuse to serve a template that already has someone's details on it.

    Without this, dropping a completed form at the template path hands EVERY
    agent another agent's name and signature — and this repo deploys the working
    tree, so a placeholder committed for local calibration ships to production.
    `MASLAKA_ALLOW_FILLED_TEMPLATE=true` opts out for coordinate work on a dev
    box; it must never be set anywhere real.
    """
    if getattr(settings, "MASLAKA_ALLOW_FILLED_TEMPLATE", False):
        logger.warning(
            "maslaka.association: serving a NON-BLANK template because "
            "MASLAKA_ALLOW_FILLED_TEMPLATE is set. Local calibration only."
        )
        return
    found = _template_filled_text()
    if found:
        raise FormTemplateMissing(
            f"the vendored form is NOT blank — it already contains {found!r}, "
            "which only a completed copy carries. Serving it would leak one "
            "agent's details to another. Replace it with the blank from Swiftness."
        )


def _draw_boxed_digits(c, digits: str, x: float, y: float, *, pitch: float) -> None:
    """One digit per printed box, advancing by the grid's own pitch.

    The boxes are part of the scanned/printed form, so nothing aligns them for
    us — the digits have to be stepped manually or they bunch up at the left and
    read as written outside the grid.
    """
    for i, ch in enumerate(digits or ""):
        c.drawString(x + i * pitch, y, ch)
