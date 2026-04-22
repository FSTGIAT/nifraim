from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.portal_link import CustomerPortalLink
from app.models.record import ClientRecord
from app.models.upload import FileUpload
from app.api.deps import get_current_user, get_portal_session
from app.schemas.portal import (
    PortalLinkCreate, PortalLinkOut,
    PortalAccessRequest, PortalAccessResponse,
    PortalDashboardData, PortalHistoryResponse,
    PortalChatRequest,
)
from app.services.portal_service import (
    create_portal_link, get_agent_links, revoke_link, verify_portal_access, get_portal_dashboard,
    get_portal_history,
)
from app.services.auth_service import create_portal_token
from app.services.email_service import send_portal_email

router = APIRouter()


@router.post("/generate", response_model=PortalLinkOut)
async def generate_link(
    body: PortalLinkCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    link = await create_portal_link(
        db=db,
        user_id=user.id,
        customer_id_number=body.customer_id_number,
        customer_name=body.customer_name,
        password=body.password,
        expires_days=body.expires_days,
        customer_email=body.customer_email,
    )
    return link


@router.get("/links", response_model=list[PortalLinkOut])
async def list_links(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_agent_links(db, user.id)


@router.delete("/{token}")
async def delete_link(
    token: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    success = await revoke_link(db, user.id, token)
    if not success:
        raise HTTPException(status_code=404, detail="Link not found")
    return {"ok": True}


@router.post("/{token}/access", response_model=PortalAccessResponse)
async def access_portal(
    token: str,
    body: PortalAccessRequest,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint — customer enters password to get a session."""
    link = await verify_portal_access(db, token, body.password)
    if not link:
        raise HTTPException(status_code=401, detail="סיסמה שגויה או קישור לא פעיל")
    session_token = create_portal_token(token, str(link.user_id))
    return PortalAccessResponse(
        session_token=session_token,
        customer_name=link.customer_name,
        expires_at=link.expires_at,
    )


@router.get("/{token}/dashboard", response_model=PortalDashboardData)
async def get_dashboard(
    token: str,
    link: CustomerPortalLink = Depends(get_portal_session),
    db: AsyncSession = Depends(get_db),
):
    """Protected by portal JWT — returns customer dashboard data."""
    data = await get_portal_dashboard(db, link.user_id, link.customer_id_number)
    if not data:
        raise HTTPException(status_code=404, detail="לא נמצאו נתונים עבור לקוח זה")
    return data


@router.get("/{token}/history", response_model=PortalHistoryResponse)
async def get_history(
    token: str,
    link: CustomerPortalLink = Depends(get_portal_session),
    db: AsyncSession = Depends(get_db),
):
    """Get snapshot history for trend charts."""
    snapshots = await get_portal_history(db, link.id)
    return {"snapshots": snapshots}


@router.post("/{token}/chat")
async def portal_chat(
    token: str,
    body: PortalChatRequest,
    link: CustomerPortalLink = Depends(get_portal_session),
    db: AsyncSession = Depends(get_db),
):
    """AI chat for portal customers — streams SSE responses."""
    from app.services.portal_ai_service import stream_portal_chat, check_rate_limit

    if not check_rate_limit(token):
        raise HTTPException(status_code=429, detail="הגעת למגבלת ההודעות. נסה שוב מאוחר יותר.")

    dashboard_data = await get_portal_dashboard(db, link.user_id, link.customer_id_number)
    if not dashboard_data:
        raise HTTPException(status_code=404, detail="לא נמצאו נתונים")

    history = [{"role": m.role, "content": m.content} for m in body.history]

    return StreamingResponse(
        stream_portal_chat(dashboard_data, body.question, history),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{token}/send-email")
async def send_email(
    token: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send portal link email to the customer."""
    result = await db.execute(
        select(CustomerPortalLink).where(
            CustomerPortalLink.token == token,
            CustomerPortalLink.user_id == user.id,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    if not link.customer_email:
        raise HTTPException(status_code=400, detail="לא הוזנה כתובת אימייל ללקוח")

    portal_url = f"https://nifraim-production.up.railway.app/portal/{link.token}"
    try:
        await send_portal_email(
            to_email=link.customer_email,
            customer_name=link.customer_name,
            portal_url=portal_url,
            password="(הסיסמה שנקבעה בעת יצירת הקישור)",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה בשליחת אימייל: {str(e)}")
    return {"ok": True}


@router.get("/customer-info/{id_number}")
async def get_customer_info(
    id_number: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Agent endpoint — auto-fill customer name and email when generating a link."""
    # Find from active production file
    prod_result = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user.id,
            FileUpload.is_production == True,
        )
    )
    prod_upload = prod_result.scalar_one_or_none()
    if not prod_upload:
        return {"name": "", "email": ""}

    id_stripped = str(id_number or "").lstrip("0") or "0"
    record_result = await db.execute(
        select(ClientRecord).where(
            ClientRecord.user_id == user.id,
            ClientRecord.upload_id == prod_upload.id,
            or_(
                ClientRecord.id_number == id_number,
                ClientRecord.id_number == id_stripped,
                func.ltrim(ClientRecord.id_number, "0") == id_stripped,
            ),
        ).limit(1)
    )
    record = record_result.scalar_one_or_none()
    if not record:
        return {"name": "", "email": ""}

    name = " ".join(p for p in [record.first_name or "", record.last_name or ""] if p).strip()
    return {"name": name, "email": record.client_email or ""}
