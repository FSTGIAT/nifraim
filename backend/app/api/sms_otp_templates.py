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
    {"company_name": "אלטשולר", "portal_kind": "altshuler", "pattern": r"(אלטשולר|altshuler).*\d{4,8}"},
    {"company_name": "הכשרה", "portal_kind": "hachshara", "pattern": r"(הכשרה|hachshara).*\d{4,8}"},
    {"company_name": "אקסלנס", "portal_kind": "excellence", "pattern": r"(אקסלנס|excellence).*\d{4,8}"},
    {"company_name": "איילון", "portal_kind": "ayalon", "pattern": r"(איילון|אילון|ayalon).*\d{4,8}"},
    # "מור" is a short token that appears inside other words — require a word
    # boundary (space / punctuation / digit follows) so we don't mis-tag.
    {"company_name": "מור", "portal_kind": "mor", "pattern": r"(מור[\s\-:.,].*\d{4,8}|more.?invest.*\d{4,8}|morefund.*\d{4,8})"},
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
