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
    mentions: list[dict] = Field(default_factory=list, max_length=10)  # @-picked contacts


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
    return await svc.ask(db, user, body.question, [t.model_dump() for t in body.history], body.mentions)


@router.get("/contacts")
async def contacts(q: str = "", db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    """The @ search in the ask box: customers (name · ת.ז), insurer contacts, mail senders."""
    return await svc.contacts(db, user, q[:60])


@router.post("/act")
async def act(body: ActIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    """The agent approved a prepared email / meeting invite — send it from their mailbox."""
    from fastapi import HTTPException
    from app.services import agent_actions
    from app.services.mail_intake import MailIntakeError
    from app.services.mail_intake.send import NoSendableMailbox
    if body.kind == "harb":
        return await _act_harb(db, user, body.data)
    if body.kind == "maslaka":
        return await _act_maslaka(db, user, body.data)
    if body.kind == "call_task":
        return await _act_call_task(db, user, body.data)
    if body.kind == "collection":
        from app.services import collection_agent
        case_id = str(body.data.get("case_id") or "")
        try:
            case = (await collection_agent.send_reminder(db, user, case_id) if body.data.get("case_status") == "sent"
                    else await collection_agent.send_case(db, user, case_id))
        except ValueError as e:
            raise HTTPException(400, str(e))
        return {"ok": True, "status": case.status}
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


async def _act_call_task(db: AsyncSession, user: User, data: dict):
    """The agent approved "mark this call task done" (tools_calls.mark_call_task_done)."""
    from fastapi import HTTPException
    from app.api.calls import _own, set_task
    try:
        idx = int(data.get("task_index"))
    except (TypeError, ValueError):
        raise HTTPException(400, "bad_task")
    call = await _own(db, user, str(data.get("call_id") or ""))
    call.insights = set_task(call.insights, idx, True)
    await db.commit()
    return {"ok": True}


async def _act_harb(db: AsyncSession, user: User, data: dict):
    """The agent approved fetching a customer from הר הביטוח — the click is the consent the site's
    checkbox asks for. Re-checks every gate (credential, worker online, no open request), then queues
    it for the agent's local worker. The chat follows GET /api/policies/harb-requests/{id}."""
    from fastapi import HTTPException
    from app.services.policies import harb_jobs
    from app.services.policies.store import norm_id
    idn = norm_id(data.get("customer_id_number"))
    birth = harb_jobs.parse_user_date(data.get("birth_date"))
    issued = harb_jobs.parse_user_date(data.get("issue_date"))
    if not 5 <= len(idn) <= 9 or not birth or not issued:
        raise HTTPException(400, "חסרים ת.ז, תאריך לידה או תאריך הנפקה תקינים")
    try:
        req = await harb_jobs.enqueue(db, user, idn, birth, issued, data.get("customer_name"))
    except harb_jobs.HarbGateError as e:
        raise HTTPException(409, str(e))
    return {"ok": True, "harb_request_id": str(req.id), "customer_id_number": idn}


async def _act_maslaka(db: AsyncSession, user: User, data: dict):
    """The agent approved a מסלקה request Nifra Agent prepared. Same gates as the
    מסלקה tab's /api/maslaka/inquiry: MASLAKA_ENABLED + an approved שיוך."""
    from app.api.maslaka import _serialize_inquiry, require_association_approved, require_maslaka_enabled
    from app.services.maslaka import orchestration
    code = str(data.get("code") or "")
    if code != "9100":   # the only request the מסלקה tab sends (see tools_maslaka.propose_maslaka_request)
        from fastapi import HTTPException
        raise HTTPException(400, "bad_code")
    require_maslaka_enabled()
    await require_association_approved(db=db, user=user)
    from app.api.maslaka import consent_record
    from app.schemas.maslaka import ConsentIn
    raw = data.get("consent")
    try:
        consent = ConsentIn(**raw) if isinstance(raw, dict) else None
    except Exception:   # noqa: BLE001 — a malformed form is the agent's to fix
        from fastapi import HTTPException
        raise HTTPException(400, "פרטי טופס נספח א' לא תקינים — בדקו תאריכים, מיקוד ומוצר מוחרג.")
    inquiry = await orchestration.create_inquiry(
        db, user_id=user.id, customer_id_number=str(data.get("customer_id_number") or ""),
        customer_name=(data.get("customer_name") or None), action_code=code,
        consent=consent_record(consent),
    )
    return _serialize_inquiry(inquiry)
