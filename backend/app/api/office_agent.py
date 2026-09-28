"""The office agent ("סוכן המשרד", services/office_agent.py): one brief that
speaks for the Mail Agent + the collection agent, and a short ask box.
Actions go through the existing mail-agent / collection-agent endpoints."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_paid_user
from app.models.user import User
from app.services import office_agent as svc

router = APIRouter()


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=500)


@router.get("")
async def get_brief(db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    return await svc.brief(db, user)


@router.get("/narrate")
async def get_narrate(db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    """Nifra Agent's written brief: greeting + ≤5 lines, each optionally tied to a card's action."""
    return await svc.narrate(db, user)


@router.post("/ask")
async def ask(body: AskIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    return {"answer": await svc.ask(db, user, body.question)}


@router.get("/map")
async def map_page(path: str = "index.md", db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    """One page of the agent's data map (services/data_map) — what the AI reads."""
    from fastapi.responses import PlainTextResponse
    from app.services import data_map
    ctx = await data_map.load(db, user)
    return PlainTextResponse(data_map.render(ctx, path), media_type="text/markdown; charset=utf-8")
