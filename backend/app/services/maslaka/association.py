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
from datetime import date, datetime
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

FONT_FILE = Path(__file__).resolve().parents[2] / "assets" / "fonts" / "Heebo.ttf"

# Overlay geometry, in PDF points from the bottom-left (A4: 595.32 × 841.92),
# for the 2-page `טופס בקשה – שיוך לבית תוכנה או בית סוכן` BLANK (vendored
# 2026-09-29). The form has no AcroForm fields, so it is a coordinate overlay.
# The digit boxes are vector paths — their positions below were READ from the
# PDF (pypdfium2 object bounds), not eyeballed: every row has a 13.25pt pitch.
#
# Always verify by rendering to PNG and LOOKING:
#     import pypdfium2 as pdfium
#     pdfium.PdfDocument("out.pdf")[0].render(scale=1.4).to_pil().save("out.png")
BOX_PITCH = 13.25
BOX_WIDTH = 13.2
# (left edge of the first box, bottom of the row) per digit row.
DIGIT_ROWS: dict[str, tuple[int, float, float]] = {       # name → (page, x0, y0)
    "agent_id": (0, 273.2, 616.3),          # מספר מזהה (ת"ז/ח.פ)
    "beit_tochna_id": (0, 235.3, 325.5),    # ח.פ/ת"ז בית תוכנה/בית סוכן
    "signer_id": (1, 301.6, 724.5),         # ת.ז of the signer, page 2
}
# Text anchors: (page, x, y, align). Right-aligned Hebrew sits on its line the
# way a hand would write it in an RTL form.
TEXT_ANCHORS: dict[str, tuple[int, float, float, str]] = {
    "agent_name": (0, 351.0, 646.0, "right"),        # שם סוכן/סוכנות/מעסיק/מייצג
    "beit_tochna_name": (0, 287.0, 355.5, "center"),  # שם בית תוכנה/בית סוכן
    "signer_name": (1, 489.0, 724.5, "center"),      # שם החותם
    "sign_date": (1, 237.0, 724.5, "center"),        # תאריך
}
# V ticks — the form says "סמן את המתאים בV". (page, centre x, centre y, size)
TICKS: dict[str, tuple[int, float, float, float]] = {
    "beit_tochna_checkbox": (0, 452.1, 412.8, 11.0),  # לבית תוכנה
    # Section 3, "האם לחבר בנוסף?". בנוסף keeps any association the agent
    # already has and ADDS Nifraim — the only choice that cannot disconnect
    # them from an existing בית תוכנה, so it is the one we fill.
    "connect_in_addition": (0, 499.3, 139.8, 10.0),
}
# The box the drawn signature is fitted into, bottom-anchored on the
# חתימת איש קשר ראשי line (page 2).
SIGNATURE_BOX = (1, 70.0, 723.0, 98.0, 40.0)   # page, x, y, w, h

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
    # A resubmission (after a rejection) is a new conversation: forget the last
    # reply so the watcher does not re-apply it to the new form.
    link.reply_message_id = None
    link.reply_received_at = None
    link.reply_subject = None
    link.reply_snippet = None
    link.decided_via = None
    if delivery_note:
        link.delivery_note = delivery_note
    await db.commit()


async def mark_approved(db: AsyncSession, link: MaslakaAgentLink) -> None:
    link.status = APPROVED
    link.approved_at = datetime.utcnow()
    link.rejected_reason = None
    await db.commit()
    # The agent consented (on the שיוך form step) to monthly production reports:
    # open them now — approval is the moment the מסלקה lets us ask.
    from app.services.maslaka import orchestration
    if orchestration.auto_production_on(link):
        await orchestration.ensure_monthly_subscriptions(db, link.user_id)


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
def build_prefilled_form(
    *,
    agent_name: str,
    agent_id_number: str,
    signer_name: str | None = None,
    signer_id_number: str | None = None,
    signature_png: bytes | None = None,
    sign_date: date | None = None,
) -> bytes:
    """Overlay the agent's details onto the מסלקה's own blank form.

    Not a re-typeset copy: this draws on top of THEIR document, because a
    regulator's form re-created from a screenshot is a form they may refuse.

    With `signature_png` it is the finished, signed form — name, ת.ז, date and
    signature on page 2 — the thing that is emailed to the helpdesk. Without
    it, page 2 is left for a hand.
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

    pages: dict[int, list] = {0: [], 1: []}

    def text(key: str, value: str, *, hebrew: bool, size: float = 11) -> None:
        pg, x, y, align = TEXT_ANCHORS[key]
        pages[pg].append(("text", x, y, align, _shape_hebrew(value) if hebrew else value,
                          font if hebrew else "Helvetica", size))

    def digits(key: str, value: str) -> None:
        pg, x0, y0 = DIGIT_ROWS[key]
        pages[pg].append(("digits", x0, y0, value))

    def tick(key: str) -> None:
        pg, cx, cy, size = TICKS[key]
        pages[pg].append(("tick", cx, cy, size))

    text("agent_name", agent_name, hebrew=True)
    digits("agent_id", agent_id_number)
    # לבית תוכנה — always ticked; an agent joining Nifraim is never joining a
    # בית סוכן, and a mis-ticked box sends the association to the wrong entity.
    tick("beit_tochna_checkbox")
    text("beit_tochna_name", BEIT_TOCHNA_NAME, hebrew=False)
    digits("beit_tochna_id", BEIT_TOCHNA_ID)
    tick("connect_in_addition")

    if signature_png:
        text("signer_name", signer_name or agent_name, hebrew=True)
        digits("signer_id", signer_id_number or agent_id_number)
        text("sign_date", (sign_date or israel_today()).strftime("%d/%m/%Y"), hebrew=False)
        pages[SIGNATURE_BOX[0]].append(("signature", signature_png))

    for pg in (0, 1):
        for op in pages[pg]:
            _draw_op(c, op, font)
        c.showPage()
    c.save()
    packet.seek(0)

    overlay = PdfReader(packet)
    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        if i < len(overlay.pages):
            page.merge_page(overlay.pages[i])
        writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def _draw_op(c, op: tuple, font: str) -> None:
    kind = op[0]
    if kind == "text":
        _, x, y, align, value, face, size = op
        c.setFillColorRGB(0, 0, 0)
        c.setFont(face, size)
        {"right": c.drawRightString, "center": c.drawCentredString}.get(
            align, c.drawString)(x, y, value)
    elif kind == "digits":
        _, x0, y0, value = op
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica", 10.5)
        for i, ch in enumerate((value or "")[:9]):
            c.drawCentredString(x0 + i * BOX_PITCH + BOX_WIDTH / 2 + 0.7, y0 + 4.6, ch)
    elif kind == "tick":
        _, cx, cy, size = op
        # A hand-drawn V: short left stroke down to the base, long right stroke up.
        c.setStrokeColorRGB(0.05, 0.1, 0.35)
        c.setLineWidth(1.4)
        c.setLineCap(1)
        c.setLineJoin(1)
        h = size / 2
        p = c.beginPath()
        p.moveTo(cx - h * 0.85, cy + h * 0.05)
        p.lineTo(cx - h * 0.2, cy - h * 0.75)
        p.lineTo(cx + h * 0.95, cy + h * 0.95)
        c.drawPath(p, stroke=1, fill=0)
    elif kind == "signature":
        from reportlab.lib.utils import ImageReader

        _, x, y, w, h = SIGNATURE_BOX
        img = ImageReader(io.BytesIO(op[1]))
        iw, ih = img.getSize()
        scale = min(w / iw, h / ih)
        dw, dh = iw * scale, ih * scale
        # Centred on the line, sitting ON it (bottom-anchored), like ink.
        c.drawImage(img, x + (w - dw) / 2, y, dw, dh, mask="auto")


def israel_today() -> date:
    """The date the agent signed, in THEIR day — the server runs on UTC, and a
    form signed at 01:00 Israel time must not carry yesterday's date."""
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo("Asia/Jerusalem")).date()


class SignatureInvalid(ValueError):
    pass


def decode_signature(data_url: str) -> bytes:
    """The drawn signature, from the wizard's canvas, as a trimmed PNG.

    Trimmed to its ink so it can be scaled to the line — a signature drawn in
    the corner of a wide pad would otherwise print as a speck. Kept in memory
    only: it exists on disk solely inside the encrypted signed form.
    """
    import base64

    from PIL import Image

    prefix = "data:image/png;base64,"
    if not isinstance(data_url, str) or not data_url.startswith(prefix):
        raise SignatureInvalid("חתימה לא תקינה")
    if len(data_url) > 2_000_000:
        raise SignatureInvalid("החתימה גדולה מדי")
    try:
        raw = base64.b64decode(data_url[len(prefix):], validate=True)
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception as e:                                       # noqa: BLE001
        raise SignatureInvalid("חתימה לא תקינה") from e
    img = img.convert("RGBA")
    bbox = img.getchannel("A").getbbox()
    if not bbox or (bbox[2] - bbox[0]) < 20 or (bbox[3] - bbox[1]) < 8:
        raise SignatureInvalid("נא לחתום בתוך המסגרת")
    pad = 6
    img = img.crop((max(bbox[0] - pad, 0), max(bbox[1] - pad, 0),
                    min(bbox[2] + pad, img.width), min(bbox[3] + pad, img.height)))
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def normalize_id(value: str) -> str:
    """Same rule as `set_agent_identity`: digits only, a ת"ז keeps its leading
    zero."""
    digits = "".join(ch for ch in (value or "") if ch.isdigit())
    if not digits or len(digits) > 9:
        raise ValueError("מספר זהות חייב להכיל עד 9 ספרות")
    return digits.zfill(9)


def render_preview_pngs(pdf_bytes: bytes, *, scale: float = 1.6) -> list[bytes]:
    """The filled form as page images, for the wizard to SHOW the agent before
    sending. Images rather than an <iframe> of the PDF: mobile browsers
    (Android Chrome) render an embedded PDF as a blank box."""
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(pdf_bytes)
    pngs = []
    for i in range(len(doc)):
        buf = io.BytesIO()
        img = doc[i].render(scale=scale).to_pil()
        if i > 0:
            # Page 2 holds only the signature row under the letterhead; the
            # rest is blank paper that would push the signature out of view.
            img = img.crop((0, 0, img.width, int(img.height * 0.22)))
        img.save(buf, format="PNG", optimize=True)
        pngs.append(buf.getvalue())
    return pngs


def _register_hebrew_font() -> str:
    """Heebo (OFL), vendored under assets/fonts — the production image carries
    only the BUILT frontend, so the frontend's font files are not there to
    borrow. Falls back to Helvetica, which renders Hebrew as blanks — so the
    caller gets a visibly wrong form rather than a silently wrong one."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    name = "HeeboForm"
    if name in pdfmetrics.getRegisteredFontNames():
        return name
    for candidate in (
        FONT_FILE,
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
    is why only NAMES go through here — the ת"ז, ח.פ and date are drawn as
    plain Latin digits (the same trap as the visual-Hebrew parsers elsewhere in
    this repo, where reversing had to protect numeric runs)."""
    return (text or "")[::-1]


# ─── Delivery ──────────────────────────────────────────────────────────────
async def deliver_to_helpdesk(
    *, link: MaslakaAgentLink, pdf_bytes: bytes, agent_email: str,
) -> str:
    """Email the signed form to the מסלקה helpdesk; returns a description of
    where it went (the route shows it as `נשלח ל-<this>`).

    **From the agent's own mailbox** when they have connected one that can send
    (`mail_intake.send`) — the helpdesk corresponds with the agent, and its
    approval lands in the inbox Nifraim already watches. Otherwise from our
    `no-reply@` with the agent as `Reply-To`.

    A connected mailbox whose send FAILS raises rather than falling back: a
    silent fallback would tell the agent the form left their mailbox when it did
    not. The route has already stored the form, so nothing is lost.
    """
    from email.message import EmailMessage
    from email.utils import make_msgid

    from app.services.email_service import send_raw_message
    from app.services.mail_intake import MailIntakeError
    from app.services.mail_intake.send import NoSendableMailbox, send_as_agent

    to = helpdesk_email()   # always through the override seam — dev must never mail the regulator
    subject = f"בקשת שיוך לבית תוכנה — {link.agent_name or ''} ת\"ז {link.agent_id_number or ''}"
    details = (
        f"שם הסוכן: {link.agent_name or ''}\n"
        f"מספר מזהה: {link.agent_id_number or ''}\n"
        f"בית תוכנה: {BEIT_TOCHNA_NAME} (ח.פ {BEIT_TOCHNA_ID})\n\n"
    )

    def _compose(body: str) -> EmailMessage:
        msg = EmailMessage()
        # Our own ID, remembered on the link, so the approval watcher never reads
        # the form we sent as the helpdesk's answer (dev: helpdesk == agent inbox).
        msg["Message-ID"] = make_msgid(domain="nifraim.com")
        link.sent_message_id = msg["Message-ID"]
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        msg.add_attachment(
            pdf_bytes, maintype="application", subtype="pdf",
            filename=link.signed_pdf_filename or "shiyuch.pdf",
        )
        return msg

    # 1. The agent's own mailbox — written in the agent's voice.
    agent_msg = _compose(
        "שלום,\n\n"
        f"מצורפת בקשת שיוך לבית התוכנה {BEIT_TOCHNA_NAME}, חתומה.\n\n"
        + details
        + "אודה לאישור השיוך.\n\n"
        f"תודה,\n{link.agent_name or ''}\n"
    )
    try:
        if not settings.MASLAKA_SEND_AS_AGENT:
            raise NoSendableMailbox("send-as-agent disabled by MASLAKA_SEND_AS_AGENT")
        sender = await send_as_agent(link.user_id, agent_msg, display_name=link.agent_name)
        return f"{to}, מהתיבה שלכם {sender}"
    except NoSendableMailbox:
        pass
    except MailIntakeError as e:
        raise RuntimeError(
            "השליחה מתיבת המייל שלכם נכשלה"
            + (" — סיסמת האפליקציה לא התקבלה" if e.code == "bad_app_password" else "")
            + ". בדקו את חיבור תיבת המייל בהגדרות ונסו שוב."
        ) from e

    # 2. Fallback: Nifraim sends, the agent is Reply-To.
    msg = _compose(
        "שלום,\n\n"
        "מצורפת בקשת שיוך לבית תוכנה חתומה.\n\n"
        + details
        + "נא לאשר את השיוך. לתשובה ניתן להשיב למייל זה — התשובה תגיע ישירות לסוכן.\n\n"
        f"תודה,\n{BEIT_TOCHNA_NAME}\n"
    )
    msg["From"] = settings.SMTP_FROM_EMAIL or "no-reply@nifraim.com"
    if agent_email:
        msg["Reply-To"] = agent_email
    await send_raw_message(msg)
    return f"{to}, מ-Nifraim (לא מחוברת תיבת מייל שלכם)"


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


def template_is_servable() -> bool:
    """Can `build_prefilled_form` actually produce a form right now?

    Not the same as "the file exists" — a present-but-filled template is refused
    by the guard. The status endpoint reported `template_ready: true` off a bare
    `.exists()` while the download 503'd, which is exactly the dishonest-green
    the מסלקה tab's gate exists to avoid.
    """
    if not BLANK_FORM.exists():
        return False
    try:
        _assert_template_is_blank()
        return True
    except FormTemplateMissing:
        return False
