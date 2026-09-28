"""The collection agent ("סוכן גבייה", services/collection_agent.py): per insurer,
the customers whose commission didn't arrive, a draft mail the agent approves,
reply follow-up and one suggested next step. Nothing is sent without a click."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_paid_user
from app.models.user import User
from app.services import collection_agent as svc

router = APIRouter()


class CaseEdit(BaseModel):
    to_email: str | None = None
    contact_name: str | None = None
    subject: str | None = None
    body: str | None = None


@router.get("")
async def get_brief(db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    return await svc.brief(db, user)


@router.post("/refresh")
async def refresh(db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    await svc.refresh_cases(db, user)
    return await svc.brief(db, user)


def _404(e: LookupError):
    raise HTTPException(status_code=404, detail=str(e))


@router.patch("/cases/{case_id}")
async def edit_case(case_id: str, body: CaseEdit, db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    try:
        await svc.update_case(db, user, case_id, to_email=body.to_email, contact_name=body.contact_name,
                              subject=body.subject, body=body.body)
    except (LookupError, ValueError) as e:
        _404(LookupError(str(e)))
    return await svc.brief(db, user)


@router.post("/cases/{case_id}/send")
async def send_case(case_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    state = await svc.mailbox_state_for(db, user)
    if not state["can_send"]:
        raise HTTPException(status_code=409, detail=state["reason"] or "cannot_send")
    try:
        await svc.send_case(db, user, case_id)
    except LookupError as e:
        _404(e)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001 — the mailbox refused; the draft is kept
        raise HTTPException(status_code=502, detail=str(e)[:300])
    return await svc.brief(db, user)


@router.post("/cases/{case_id}/remind")
async def remind(case_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    try:
        await svc.send_reminder(db, user, case_id)
    except LookupError as e:
        _404(e)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(e)[:300])
    return await svc.brief(db, user)


@router.post("/cases/{case_id}/resolve")
async def resolve(case_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    try:
        await svc.resolve_case(db, user, case_id)
    except LookupError as e:
        _404(e)
    return await svc.brief(db, user)


@router.post("/check")
async def check_now(db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    await svc.poll_user(db, user)
    return await svc.brief(db, user)
