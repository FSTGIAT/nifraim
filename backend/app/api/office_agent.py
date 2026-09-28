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


class Turn(BaseModel):
    role: str
    text: str = Field(max_length=4000)


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    history: list[Turn] = Field(default_factory=list, max_length=20)


class ActIn(BaseModel):
    kind: str  # email | meeting
    data: dict


@router.get("")
async def get_brief(db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    return await svc.brief(db, user)


@router.get("/narrate")
async def get_narrate(db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    """Nifra Agent's written brief: greeting + ≤5 lines, each optionally tied to a card's action."""
    return await svc.narrate(db, user)


@router.post("/ask")
async def ask(body: AskIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    return await svc.ask(db, user, body.question, [t.model_dump() for t in body.history])


@router.post("/act")
async def act(body: ActIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    """The agent approved a prepared email / meeting invite — send it from their mailbox."""
    from fastapi import HTTPException
    from app.services import agent_actions
    from app.services.mail_intake import MailIntakeError
    from app.services.mail_intake.send import NoSendableMailbox
    try:
        return await agent_actions.send(db, user, body.kind, body.data)
    except agent_actions.ActionError as e:
        raise HTTPException(400, str(e))
    except NoSendableMailbox:
        raise HTTPException(400, "not_connected")
    except MailIntakeError as e:
        raise HTTPException(502, str(e))


@router.get("/map")
async def map_page(path: str = "index.md", db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    """One page of the agent's data map (services/data_map) — what the AI reads."""
    from fastapi.responses import PlainTextResponse
    from app.services import data_map
    ctx = await data_map.load(db, user)
    return PlainTextResponse(data_map.render(ctx, path), media_type="text/markdown; charset=utf-8")
