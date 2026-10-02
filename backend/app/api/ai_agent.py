"""Nifra AI v2 — one streamed endpoint for the in-app chat and the Nifra Agent ask box.

POST /api/ai/agent → text/event-stream of `data: {...}` lines (services/agent/loop.py).
The session is opened INSIDE the stream: FastAPI closes yield-dependencies before
a StreamingResponse body runs, so the request's own session can't be used here.
"""
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import get_paid_user
from app.database import async_session
from app.models.user import User

router = APIRouter()


class Turn(BaseModel):
    role: str
    text: str = Field(default="", max_length=4000)


class AgentIn(BaseModel):
    question: str = Field(min_length=1, max_length=800)
    history: list[Turn] = Field(default_factory=list, max_length=20)
    mentions: list[dict] = Field(default_factory=list, max_length=10)
    view_context: str | None = Field(default=None, max_length=6000)   # what the agent is looking at
    surface: str = Field(default="chat", pattern="^(chat|panel)$")      # panel = Nifra Agent (plain text only)


@router.post("/agent")
async def agent(body: AgentIn, user: User = Depends(get_paid_user)):
    user_id = user.id

    async def gen():
        from app.services.agent.loop import run
        async with async_session() as db:
            u = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
            try:
                async for ev in run(db, u, body.question, [t.model_dump() for t in body.history], body.mentions, view_context=body.view_context, surface=body.surface):
                    yield f"data: {json.dumps(ev, ensure_ascii=False, default=str)}\n\n"
            except Exception as e:  # noqa: BLE001
                import logging
                logging.getLogger("uvicorn.error").warning("NIFRA-AGENT failed: %r", e)
                yield f"data: {json.dumps({'text': 'לא הצלחתי לענות כרגע — נסו שוב בעוד רגע.'}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'done': True, 'lane': 'error'})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
