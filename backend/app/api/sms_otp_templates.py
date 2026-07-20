import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.sms_otp_template import SmsOtpTemplate
from app.schemas.sms_otp_template import (
    SmsOtpTemplateCreate,
    SmsOtpTemplateUpdate,
    SmsOtpTemplateOut,
)
from app.api.deps import get_current_user

router = APIRouter()

# Starter patterns. Matched (with IGNORE_CASE + DOT_MATCHES_ALL) against
# "sender + ' ' + body" on the device. These are GLOBAL and intentionally loose;
# replace/refine them with real pasted SMS examples. `is_block=True` rows DROP a
# code-bearing SMS even though fail-open would otherwise forward it.
DEFAULT_SMS_OTP_TEMPLATES = [
    # Migdal OTP says "פורטל apmaccess", NOT "מגדל" — anchor on apmaccess.
    {"company_name": "מגדל", "portal_kind": "migdal", "pattern": r"(מגדל|migdal|apmaccess).*\d{4,8}",
     "example": "שלום, סיסמת הכניסה לפורטל apmaccess היא 055543"},
    {"company_name": "הפניקס", "portal_kind": "phoenix", "pattern": r"(הפניקס|פניקס|fnx).*\d{4,8}"},
    # Phoenix's agent.fnx.co.il F5 terminal login SMS is brand-less: "הסיסמה:NNNNNN".
    # Without this it falls to the generic "כללי" tag (NULL) and loses the next-otp
    # tie-break to junk/other untagged codes. Anchored on the bare "הסיסמה:" form
    # (other insurers use "קוד אימות"/"הסיסמא הזמנית"/"מכלול"), so low false-positive.
    {"company_name": "הפניקס", "portal_kind": "phoenix", "pattern": r"הסיסמה\s*:\s*\d{4,8}",
     "example": "הסיסמה:086802"},
    {"company_name": "הראל", "portal_kind": "harel", "pattern": r"(הראל|harel).*\d{4,8}"},
    # "סיסמתך למכלול שלי: NNNNNN" is a SHARED OTP sender used by multiple insurers
    # (seen for both Harel and Phoenix) — its own template so either forwards,
    # labeled honestly as "מכלול" rather than guessing the company.
    {"company_name": "מכלול", "portal_kind": None, "pattern": r"מכלול.*\d{4,8}",
     "example": "סיסמתך למכלול שלי: 844844. הסיסמה אישית ואין להעבירה."},
    {"company_name": "מנורה", "portal_kind": "menora", "pattern": r"(מנורה|menora|menoranet).*\d{4,8}",
     "example": "שלום, הסיסמא הזמנית לחשבונך במנורה היא - 647087 @menoranet.menora.co.il #647087"},
    {"company_name": "כלל", "portal_kind": "clal", "pattern": r"(כלל|clal).*\d{4,8}",
     "example": "קוד האימות לחשבון האישי שלך הוא: 672428 תודה, כלל ביטוח ופיננסים"},
    # Real Altshuler OTP is CODE-FIRST ("שלום, NNNNNN הנו קוד האימות ... אלטשולר שחם"),
    # so a keyword-then-code pattern never tagged it (it forwarded only via fail-open,
    # untagged). Match the company name on EITHER side of the code. (match_otp_company
    # extracts the digits separately, so the company anchor is what matters.)
    {"company_name": "אלטשולר", "portal_kind": "altshuler",
     "pattern": r"(אלטשולר|altshuler).*\d{4,8}|\d{4,8}.*(אלטשולר|altshuler)",
     "example": "שלום, 707560 הנו קוד האימות החד פעמי שלך לכניסה לאתר אלטשולר שחם."},
    # Yelin Lapidot is also code-first ("NNNNNN קוד האימות ... ילין לפידות #NNNNNN").
    {"company_name": "ילין לפידות", "portal_kind": "yelin",
     "pattern": r"(ילין|yelin|yl-invest).*\d{4,8}|\d{4,8}.*(ילין|yelin|yl-invest)",
     "example": "209210 קוד האימות לשירותים דיגיטלים - ילין לפידות @online.yl-invest.co.il #209210"},
    # Analyst is code-first too — the digits land BEFORE the brand
    # ("…,NNNNNN הינו קוד אימות זמני לחשבונך באנליסט"), so the code-then-word
    # alternative is required, not optional. Captured live 2026-07-20.
    #
    # Tagging here is for CORRECTNESS, not labelling. Without this template the
    # analyst OTP only matched the generic "כללי" rule and landed UNTAGGED
    # (portal_kind=NULL) — sharing one bucket with junk SMS, e.g. a credit-card
    # statement the same day whose OTP_REGEX pulled "2026" out of the date
    # 15/07/2026. `next-otp` prefers an exact portal_kind over NULL, so an
    # untagged real code can lose to newer junk.
    {"company_name": "אנליסט", "portal_kind": "analyst",
     "pattern": r"(אנליסט|analyst).*\d{4,8}|\d{4,8}.*(אנליסט|analyst)",
     "example": "שלום, 565109 הינו קוד אימות זמני לחשבונך באנליסט. תוקף הקוד ל-20 דקות. @agent.analyst.co.il #565109"},
    # מיטב דש — bidirectional (Israeli OTP SMS are often code-first); anchor on
    # מיטב/meitav. Live OTP wording unverified (refine example after first run).
    # אנליסט — brand-anchored best guess (bidirectional: brand↔code). Refine or add a
    # brand-less variant once the real live SMS wording is captured (the Mor lesson —
    # some insurers' OTP text omits the brand entirely).
    {"company_name": "אנליסט", "portal_kind": "analyst",
     "pattern": r"(אנליסט|analyst).*\d{4,8}|\d{4,8}.*(אנליסט|analyst)"},
    {"company_name": "מיטב דש", "portal_kind": "meitav",
     "pattern": r"(מיטב|meitav|meitavdash).*\d{4,8}|\d{4,8}.*(מיטב|meitav)"},
    {"company_name": "הכשרה", "portal_kind": "hachshara", "pattern": r"(הכשרה|hachshara).*\d{4,8}"},
    {"company_name": "אקסלנס", "portal_kind": "excellence", "pattern": r"(אקסלנס|excellence).*\d{4,8}"},
    {"company_name": "איילון", "portal_kind": "ayalon", "pattern": r"(איילון|אילון|ayalon).*\d{4,8}"},
    # "מור" is a short token that appears inside other words — require a word
    # boundary (space / punctuation / digit follows) so we don't mis-tag.
    # Code may precede or follow the "מור" token — match either order (still
    # boundary-guarded so it won't fire inside a longer word). Live SMS unverified.
    {"company_name": "מור", "portal_kind": "mor", "pattern": r"(מור[\s\-:.,].*\d{4,8}|\d{4,8}.*מור[\s\-:.,]|more.?invest.*\d{4,8}|morefund.*\d{4,8})"},
    # Mor's REAL OTP text carries NO brand at all — live-captured 2026-07-14:
    #   "קוד אימות לאתר 514129"
    # so the brand-anchored rule above never fires and the code fell through to the
    # generic "כללי" catch-all → portal_kind NULL. An untagged code shares the bucket
    # with junk SMS and other companies' codes (newest wins), which is exactly how a
    # run-all batch consumes the wrong OTP. Anchor on the real wording — same fix as
    # Phoenix's brand-less "הסיסמה:NNNNNN" above.
    {"company_name": "מור", "portal_kind": "mor", "pattern": r"קוד\s*אימות\s*לאתר\s*\d{4,8}",
     "example": "קוד אימות לאתר 514129"},
    # Privacy block: personal bank 2FA — DROP even though it carries a code.
    {"company_name": "בנק", "portal_kind": None, "is_block": True, "pattern": r"בנק.*\d{4,8}"},
    # Generic OTP-context catch-all (company sent from a bare short code).
    {"company_name": "כללי", "portal_kind": None, "pattern": r"(קוד|אימות|סיסמ|חד.?פעמי|otp|verification|passcode).*\d{4,8}"},
]


def _out(t: SmsOtpTemplate) -> SmsOtpTemplateOut:
    return SmsOtpTemplateOut(
        id=str(t.id),
        company_name=t.company_name,
        pattern=t.pattern,
        portal_kind=t.portal_kind,
        example=t.example,
        is_block=t.is_block,
        active=t.active,
        created_at=t.created_at,
    )


@router.get("", response_model=list[SmsOtpTemplateOut])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Templates are GLOBAL (shared across agents) — no user_id scoping.
    result = await db.execute(
        select(SmsOtpTemplate).order_by(
            SmsOtpTemplate.is_block, SmsOtpTemplate.company_name, SmsOtpTemplate.created_at.desc()
        )
    )
    return [_out(t) for t in result.scalars().all()]


@router.post("", response_model=SmsOtpTemplateOut)
async def create_template(
    data: SmsOtpTemplateCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    t = SmsOtpTemplate(
        company_name=data.company_name[:100],
        pattern=data.pattern[:500],
        portal_kind=data.portal_kind[:32] if data.portal_kind else None,
        example=data.example[:500] if data.example else None,
        is_block=data.is_block,
        active=data.active,
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return _out(t)


@router.put("/{template_id}", response_model=SmsOtpTemplateOut)
async def update_template(
    template_id: str,
    data: SmsOtpTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SmsOtpTemplate).where(SmsOtpTemplate.id == uuid.UUID(template_id))
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="תבנית לא נמצאה")

    if data.company_name is not None:
        t.company_name = data.company_name[:100]
    if data.pattern is not None:
        t.pattern = data.pattern[:500]
    if data.portal_kind is not None:
        t.portal_kind = data.portal_kind[:32] or None
    if data.example is not None:
        t.example = data.example[:500] or None
    if data.is_block is not None:
        t.is_block = data.is_block
    if data.active is not None:
        t.active = data.active

    await db.commit()
    await db.refresh(t)
    return _out(t)


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SmsOtpTemplate).where(SmsOtpTemplate.id == uuid.UUID(template_id))
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="תבנית לא נמצאה")
    await db.delete(t)
    await db.commit()
    return {"status": "deleted"}


@router.post("/seed", response_model=list[SmsOtpTemplateOut])
async def seed_templates(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Insert the starter template set (skips companies already present)."""
    result = await db.execute(select(SmsOtpTemplate))
    existing = {t.company_name for t in result.scalars().all()}

    created = []
    for entry in DEFAULT_SMS_OTP_TEMPLATES:
        if entry["company_name"] not in existing:
            t = SmsOtpTemplate(
                company_name=entry["company_name"],
                portal_kind=entry.get("portal_kind"),
                pattern=entry["pattern"],
                example=entry.get("example"),
                is_block=entry.get("is_block", False),
            )
            db.add(t)
            created.append(t)

    await db.commit()
    out = []
    for t in created:
        await db.refresh(t)
        out.append(_out(t))
    return out
