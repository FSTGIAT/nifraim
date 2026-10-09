"""Maslaka Gateway self-update — the server side (see services/maslaka/gateway_release.py).

Gateway (token-auth, GATEWAY_TOKEN):
  GET  /version/{token}   → what it may run: {deployed, released, pinned}
  GET  /bundle/{token}    → the release zip (whole app tree)
  POST /report/{token}    → what it runs + its state, every minute
Admin (Admin → תפעול):
  GET  /admin             → deployed · released · running + state
  POST /admin/release     → release the deployed version (the one human click)
  POST /admin/pin         → server-side kill switch
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user
from app.database import get_db
from app.models.gateway_state import GatewayState
from app.models.user import User
from app.services.maslaka import gateway_release

router = APIRouter()


async def _state(db: AsyncSession) -> GatewayState:
    row = await db.get(GatewayState, "main")
    if row is None:
        row = GatewayState(id="main", pinned=False)
        db.add(row)
        await db.flush()
    return row


def _require_token(token: str) -> None:
    if not gateway_release.token_ok(token):
        raise HTTPException(status_code=404, detail="not found")


@router.get("/version/{token}")
async def gateway_version(token: str, db: AsyncSession = Depends(get_db)):
    _require_token(token)
    st = await _state(db)
    await db.commit()
    return {"deployed": gateway_release.version(), "released": st.released_version, "pinned": st.pinned}


@router.get("/bundle/{token}")
async def gateway_bundle(token: str):
    _require_token(token)
    return Response(gateway_release.bundle(), media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="nifraim-gateway.zip"',
                             "X-Gateway-Version": gateway_release.version()})


class GatewayReport(BaseModel):
    running_version: str = Field(..., max_length=32)
    state: str = Field(..., max_length=40)
    detail: str | None = Field(default=None, max_length=4000)
    tick_ok: bool = False


@router.post("/report/{token}")
async def gateway_report(token: str, body: GatewayReport, db: AsyncSession = Depends(get_db)):
    _require_token(token)
    st = await _state(db)
    now = datetime.utcnow()
    st.running_version, st.state, st.detail, st.reported_at = body.running_version, body.state, body.detail, now
    if body.tick_ok:
        st.last_tick_ok_at = now
    await db.commit()
    return {"ok": True}


def _admin_view(st: GatewayState) -> dict:
    deployed = gateway_release.version()
    now = datetime.utcnow()
    return {
        "deployed": deployed,
        "released": st.released_version,
        "running": st.running_version,
        "pinned": st.pinned,
        "state": st.state,
        "detail": st.detail,
        "released_by": st.released_by,
        "released_at": st.released_at.isoformat() if st.released_at else None,
        "reported_at": st.reported_at.isoformat() if st.reported_at else None,
        "last_tick_ok_at": st.last_tick_ok_at.isoformat() if st.last_tick_ok_at else None,
        # silent for >5 min = the worker is down, whatever its last state said
        "online": bool(st.reported_at and (now - st.reported_at).total_seconds() < 300),
        "up_to_date": bool(st.running_version and st.running_version == deployed),
        "release_pending": bool(st.released_version and st.released_version != st.running_version),
    }


@router.get("/admin")
async def gateway_admin(db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    st = await _state(db)
    await db.commit()
    return _admin_view(st)


@router.post("/admin/release")
async def gateway_release_now(db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    st = await _state(db)
    if st.pinned:
        raise HTTPException(status_code=409, detail="הגייטוויי נעול — בטלו את הנעילה לפני שחרור.")
    st.released_version = gateway_release.version()
    st.released_by = admin.email
    st.released_at = datetime.utcnow()
    await db.commit()
    return _admin_view(st)


class PinIn(BaseModel):
    pinned: bool


@router.post("/admin/pin")
async def gateway_pin(body: PinIn, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    st = await _state(db)
    st.pinned = body.pinned
    await db.commit()
    return _admin_view(st)
