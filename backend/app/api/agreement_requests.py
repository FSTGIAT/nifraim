"""Agreement requests — the setup wizard's "מדף ההסכמים" step: email each
insurer from the agent's own mailbox asking for the commission agreement, and
follow the replies (services/agreement_requests.py)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_paid_user
from app.models.user import User
from app.services import agreement_requests as svc

router = APIRouter()


class SendItem(BaseModel):
    company: str
    email: str
    contact_name: str | None = None


class SendIn(BaseModel):
    items: list[SendItem]


@router.get("")
async def get_overview(db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    return await svc.overview(db, user)


@router.post("/send")
async def send(body: SendIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    state = await svc.mailbox_state(db, user.id)
    if not state["can_send"]:
        raise HTTPException(status_code=409, detail=state["reason"] or "cannot_send")
    items = [i.model_dump() for i in body.items][:40]
    results = await svc.send_requests(db, user, items)
    return {"results": results, **(await svc.overview(db, user))}


@router.post("/check")
async def check_now(db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    loaded = await svc.poll_user(db, user)
    return {"loaded": loaded, **(await svc.overview(db, user))}
