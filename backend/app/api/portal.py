from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.portal_link import CustomerPortalLink
from app.models.record import ClientRecord
from app.models.upload import FileUpload
from app.api.deps import get_current_user, get_portal_session
from app.api.production import _get_production_upload_ids
from app.schemas.portal import (
    PortalLinkCreate, PortalLinkOut, PortalSettingsUpdate,
    PortalAccessRequest, PortalAccessResponse,
    PortalDashboardData, PortalHistoryResponse,
    PortalChatRequest, AgentOfferIn, AgentOfferOut,
)
from app.models.agent_portal_offer import AgentPortalOffer, PortalOfferClick
from app.services.portal_view import (
    OFFER_CATALOG, apply_settings, apply_to_history, normalize_settings,
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
        settings=body.settings,
    )
    return link


# ── Setup wizard: offers (step 3) + per-link settings ─────────────────────

def _valid_offer_url(url: str) -> bool:
    try:
        u = urlparse(url.strip())
    except ValueError:
        return False
    return u.scheme == "https" and bool(u.netloc) and " " not in url.strip()


@router.get("/offers")
async def list_offers(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """The agent's saved offers + the catalogue of offer types + click counts."""
    rows = (await db.execute(
        select(AgentPortalOffer).where(AgentPortalOffer.user_id == user.id)
    )).scalars().all()
    clicks = dict((await db.execute(
        select(PortalOfferClick.service_key, func.count(PortalOfferClick.id))
        .join(CustomerPortalLink, CustomerPortalLink.id == PortalOfferClick.portal_link_id)
        .where(CustomerPortalLink.user_id == user.id)
        .group_by(PortalOfferClick.service_key)
    )).all())
    return {
        "catalog": [{"service_key": k, "title": t} for k, t in OFFER_CATALOG.items()],
        "offers": [
            AgentOfferOut(service_key=r.service_key, title=r.title, url=r.url,
                          is_active=r.is_active, clicks=clicks.get(r.service_key, 0))
            for r in rows
        ],
    }


@router.put("/offers")
async def save_offers(
    body: list[AgentOfferIn],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upsert the agent's offers. URLs must be https — they open from the
    customer's portal, so nothing else is accepted."""
    for o in body:
        if o.service_key not in OFFER_CATALOG:
            raise HTTPException(status_code=400, detail=f"שירות לא מוכר: {o.service_key}")
        if not _valid_offer_url(o.url):
            raise HTTPException(status_code=400, detail="הקישור חייב להתחיל ב-https://")
    existing = {
        r.service_key: r for r in (await db.execute(
            select(AgentPortalOffer).where(AgentPortalOffer.user_id == user.id)
        )).scalars().all()
    }
    for o in body:
        title = (o.title or "").strip()[:120] or OFFER_CATALOG[o.service_key]
        row = existing.get(o.service_key)
        if row:
            row.title, row.url, row.is_active = title, o.url.strip(), o.is_active
        else:
            db.add(AgentPortalOffer(user_id=user.id, service_key=o.service_key,
                                    title=title, url=o.url.strip(), is_active=o.is_active))
    await db.commit()
    return await list_offers(user=user, db=db)


@router.delete("/links/{token}")
async def delete_link_permanently(
    token: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a customer's portal link for good (the agent confirms first in
    the UI). Unlike DELETE /{token} (revoke — the row stays and shows as
    "מבוטל"), the link, its snapshots and its offer clicks are deleted and the
    customer disappears from the list. An active link stops working at once."""
    from sqlalchemy import delete as sa_delete
    from app.models.portal_snapshot import PortalSnapshot

    link = (await db.execute(
        select(CustomerPortalLink).where(
            CustomerPortalLink.token == token, CustomerPortalLink.user_id == user.id,
        )
    )).scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    # portal_snapshots → customer_portal_links has no ON DELETE CASCADE.
    await db.execute(sa_delete(PortalSnapshot).where(PortalSnapshot.portal_link_id == link.id))
    await db.delete(link)  # portal_offer_clicks cascade at the DB level
    await db.commit()
    return {"ok": True}


@router.patch("/links/{token}/settings", response_model=PortalLinkOut)
async def update_link_settings(
    token: str,
    body: PortalSettingsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    link = (await db.execute(
        select(CustomerPortalLink).where(
            CustomerPortalLink.token == token, CustomerPortalLink.user_id == user.id,
        )
    )).scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    link.settings = normalize_settings(body.settings)
    await db.commit()
    await db.refresh(link)
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
    """Protected by portal JWT — returns customer dashboard data, filtered to
    what the agent chose to share (portal_view)."""
    data = await get_portal_dashboard(db, link.user_id, link.customer_id_number)
    if not data:
        raise HTTPException(status_code=404, detail="לא נמצאו נתונים עבור לקוח זה")
    view = apply_settings(link.settings, data)
    s = view["settings"]

    offers = []
    if s["offers"]:
        rows = (await db.execute(
            select(AgentPortalOffer).where(
                AgentPortalOffer.user_id == link.user_id,
                AgentPortalOffer.service_key.in_(s["offers"]),
                AgentPortalOffer.is_active == True,  # noqa: E712
            )
        )).scalars().all()
        by_key = {r.service_key: r for r in rows if _valid_offer_url(r.url)}
        offers = [
            {"service_key": k, "title": by_key[k].title, "url": by_key[k].url}
            for k in s["offers"] if k in by_key
        ]
    view["offers"] = offers

    view["agent"] = None
    if s["sections"]["agent_card"]:
        agent = await db.get(User, link.user_id)
        if agent and (agent.full_name or agent.phone):
            view["agent"] = {"name": agent.full_name, "phone": agent.phone,
                             "company_name": agent.company_name}
    return view


@router.get("/{token}/history", response_model=PortalHistoryResponse)
async def get_history(
    token: str,
    link: CustomerPortalLink = Depends(get_portal_session),
    db: AsyncSession = Depends(get_db),
):
    """Get snapshot history for trend charts (scoped like the dashboard)."""
    snapshots = await get_portal_history(db, link.id)
    products = [s.pop("_products", []) for s in snapshots]
    return {"snapshots": apply_to_history(link.settings, snapshots, products)}


@router.post("/{token}/offers/{service_key}/click")
async def offer_click(
    token: str,
    service_key: str,
    link: CustomerPortalLink = Depends(get_portal_session),
    db: AsyncSession = Depends(get_db),
):
    """Log that the customer opened an offer. The card itself is a plain link,
    so this is fire-and-forget from the browser and never blocks navigation."""
    s = normalize_settings(link.settings) if link.settings is not None else None
    if not s or service_key not in s["offers"]:
        raise HTTPException(status_code=404, detail="Offer not found")
    db.add(PortalOfferClick(portal_link_id=link.id, service_key=service_key))
    await db.commit()
    return {"ok": True}


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

    if link.settings is not None and not normalize_settings(link.settings)["sections"]["ai_chat"]:
        raise HTTPException(status_code=403, detail="העוזר אינו זמין בפורטל זה")

    raw = await get_portal_dashboard(db, link.user_id, link.customer_id_number)
    if not raw:
        raise HTTPException(status_code=404, detail="לא נמצאו נתונים")
    # The chat sees only what the customer may see — a hidden premium must not
    # come back as an answer to "what's my premium?".
    dashboard_data = apply_settings(link.settings, raw)

    history = [{"role": m.role, "content": m.content} for m in body.history]

    return StreamingResponse(
        stream_portal_chat(dashboard_data, body.question, history),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{token}/send-email")
async def send_email(
    token: str,
    request: Request,
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

    # The app's own origin (the agent's browser sends it) — works on prod,
    # previews and localhost alike. Fallback: the request's own base URL.
    origin = (request.headers.get("origin") or str(request.base_url)).rstrip("/")
    portal_url = f"{origin}/portal/{link.token}"
    try:
        # The password is bcrypt-hashed — it can't be read back, so the email
        # says it comes from the agent separately (never a fake placeholder).
        await send_portal_email(
            to_email=link.customer_email,
            customer_name=link.customer_name,
            portal_url=portal_url,
            password=None,
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
    # Search EVERY active production upload, not one.
    #
    # `is_production` is not a singleton — several companies' files coexist by
    # design — so `scalar_one_or_none()` here raised MultipleResultsFound and
    # the endpoint answered 500. Measured locally: 4 active uploads, so the
    # auto-fill 500'd for any agent past their first company, which is every
    # real agent. It fires on blur of the ת"ז field, so the failure was silent
    # to the user: the name and email simply never filled in.
    #
    # Searching all of them is also more correct than picking one: a customer
    # can sit in any company's file, so a single-file lookup would miss them.
    empty_mix = {"savings": 0, "insurance": 0, "unknown": 0}
    upload_ids = await _get_production_upload_ids(db, user.id)
    if not upload_ids:
        return {"name": "", "email": "", "product_mix": empty_mix}

    id_stripped = str(id_number or "").lstrip("0") or "0"
    record_result = await db.execute(
        select(ClientRecord).where(
            ClientRecord.user_id == user.id,
            ClientRecord.upload_id.in_(upload_ids),
            or_(
                ClientRecord.id_number == id_number,
                ClientRecord.id_number == id_stripped,
                func.ltrim(ClientRecord.id_number, "0") == id_stripped,
            ),
        )
    )
    records = list(record_result.scalars().all())
    if not records:
        return {"name": "", "email": "", "product_mix": empty_mix}

    # Setup wizard: how many of this customer's products each scope keeps, so
    # the agent sees "this hides N products" before choosing (portal_view).
    from app.services.portal_view import product_category
    mix = dict(empty_mix)
    for r in records:
        cat = product_category(r.product_type)
        mix["savings" if cat in ("gemel_hishtalmut", "pension") else "insurance" if cat == "insurance" else "unknown"] += 1

    record = records[0]
    name = " ".join(p for p in [record.first_name or "", record.last_name or ""] if p).strip()
    email = next((r.client_email for r in records if r.client_email), "")
    return {"name": name, "email": email or "", "product_mix": mix}
