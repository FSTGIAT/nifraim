"""User-to-user direct messages.

⚠️ **This is the one module in the app that deliberately reads across the
`user_id` tenancy boundary.** Everywhere else, every query filters by the
current user's id (see docs/ARCHITECTURE.md §7). The messenger has to let one
user see another exists, so `/contacts` and `/search` join `users` without that
filter. That is by design, and the exposure is bounded by:

  * `ContactOut` is a strict whitelist — never `email` / `phone` / `company_name`.
  * `/search` requires >= 2 chars and matches a PREFIX only (no leading `%`),
    so the directory can't be enumerated or scraped as a substring oracle.
  * `/contacts` returns only people you already have a conversation with.

Auth is `get_current_user`, not `get_paid_user`: `is_active` means "subscription
paid", and a lapsed agent must still be able to receive and reply, or every
thread they're in becomes a dead end.

Transport is polling — there is no WebSocket anywhere in this app.
"""
import re
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_, case
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.dm_conversation import DmConversation, ordered_pair
from app.models.dm_message import DmMessage
from app.models.dm_presence import DmPresence, PRESENCE_WINDOW_S
from app.schemas.messenger import (
    ContactOut, MessageOut, MessageCreate, ThreadPage, PollOut, HeartbeatOut,
    MAX_BODY_LEN, PREVIEW_LEN,
)

router = APIRouter()

# Send throttle. Counted in the DB rather than an in-process bucket because
# Railway runs multiple uvicorn workers — a per-process counter would let a
# sender do N-workers times the intended rate.
RATE_LIMIT_WINDOW_S = 10
RATE_LIMIT_MAX_SENDS = 5

MIN_SEARCH_LEN = 2
SEARCH_LIMIT = 20
ONLINE_LIMIT = 24

# Everything except \n and \t. Stops a body from smuggling terminal escapes or
# NULs through the API into a log or a downstream consumer.
_CONTROL_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


def _initial(full_name: str | None, username: str) -> str:
    source = (full_name or '').strip() or username
    return source[:1].upper() if source else '?'


def _is_online(last_seen: datetime | None) -> bool:
    if last_seen is None:
        return False
    return (datetime.utcnow() - last_seen).total_seconds() <= PRESENCE_WINDOW_S


def _sanitize_body(raw: str) -> str:
    body = _CONTROL_RE.sub('', raw or '').strip()
    if not body:
        raise HTTPException(status_code=422, detail="ההודעה ריקה")
    return body[:MAX_BODY_LEN]


def _msg_out(m: DmMessage, client_id: str | None = None) -> MessageOut:
    return MessageOut(
        id=str(m.id),
        seq=m.seq,
        sender_id=str(m.sender_id),
        recipient_id=str(m.recipient_id),
        body=m.body,
        created_at=m.created_at.isoformat(),
        client_id=client_id,
    )


def _my_unread_col(me: uuid.UUID):
    return case(
        (DmConversation.user_a_id == me, DmConversation.a_unread_count),
        else_=DmConversation.b_unread_count,
    )


def _my_cleared_col(me: uuid.UUID):
    return case(
        (DmConversation.user_a_id == me, DmConversation.a_cleared_at),
        else_=DmConversation.b_cleared_at,
    )


def _mine(me: uuid.UUID):
    return or_(DmConversation.user_a_id == me, DmConversation.user_b_id == me)


def _my_cleared_at(conv: DmConversation, me: uuid.UUID) -> datetime | None:
    return conv.a_cleared_at if conv.user_a_id == me else conv.b_cleared_at


async def _total_unread(db: AsyncSession, me: uuid.UUID) -> int:
    result = await db.execute(
        select(func.coalesce(func.sum(_my_unread_col(me)), 0)).where(_mine(me))
    )
    return int(result.scalar() or 0)


async def _get_conversation(db: AsyncSession, me: uuid.UUID, other: uuid.UUID) -> DmConversation | None:
    a, b = ordered_pair(me, other)
    result = await db.execute(
        select(DmConversation).where(
            DmConversation.user_a_id == a, DmConversation.user_b_id == b
        )
    )
    return result.scalar_one_or_none()


async def _get_or_create_conversation(db: AsyncSession, me: uuid.UUID, other: uuid.UUID) -> DmConversation:
    conv = await _get_conversation(db, me, other)
    if conv:
        return conv

    a, b = ordered_pair(me, other)
    conv = DmConversation(user_a_id=a, user_b_id=b)
    db.add(conv)
    try:
        await db.flush()
    except IntegrityError:
        # Both participants sent their first message at the same instant; the
        # unique pair index rejected the loser. Re-read the winner's row.
        await db.rollback()
        conv = await _get_conversation(db, me, other)
        if conv is None:
            raise
    return conv


async def _resolve_other(db: AsyncSession, me: User, other_id: str) -> User:
    try:
        other_uuid = uuid.UUID(other_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="המשתמש לא נמצא")

    if other_uuid == me.id:
        raise HTTPException(status_code=400, detail="אי אפשר לשלוח הודעה לעצמך")

    result = await db.execute(select(User).where(User.id == other_uuid))
    other = result.scalar_one_or_none()
    if not other:
        raise HTTPException(status_code=404, detail="המשתמש לא נמצא")
    return other


@router.post("/presence/heartbeat", response_model=HeartbeatOut)
async def heartbeat(
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark me online, and return my unread total.

    Returning `total_unread` here is what lets the collapsed dock pill keep its
    badge current on the 20s presence beat with no extra request.
    """
    result = await db.execute(select(DmPresence).where(DmPresence.user_id == me.id))
    row = result.scalar_one_or_none()
    if row:
        row.last_seen = datetime.utcnow()
    else:
        db.add(DmPresence(user_id=me.id, last_seen=datetime.utcnow()))
    try:
        await db.commit()
    except IntegrityError:
        # Two tabs raced the first insert; either one winning is fine.
        await db.rollback()

    return HeartbeatOut(total_unread=await _total_unread(db, me.id))


@router.get("/contacts", response_model=list[ContactOut])
async def contacts(
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """People I already have a conversation with, newest first.

    CROSS-USER READ (intentional — see module docstring). One flat query: the
    denormalized counters on dm_conversations avoid a COUNT per contact.
    """
    other_id = case(
        (DmConversation.user_a_id == me.id, DmConversation.user_b_id),
        else_=DmConversation.user_a_id,
    )

    stmt = (
        select(
            User.id, User.username, User.avatar_seed, User.full_name,
            DmPresence.last_seen,
            DmConversation.last_message_at,
            DmConversation.last_message_preview,
            DmConversation.last_sender_id,
            _my_unread_col(me.id).label("unread"),
        )
        .select_from(DmConversation)
        .join(User, User.id == other_id)
        .outerjoin(DmPresence, DmPresence.user_id == User.id)
        .where(
            _mine(me.id),
            # Hide conversations I cleared, until a newer message revives them.
            or_(
                _my_cleared_col(me.id).is_(None),
                DmConversation.last_message_at > _my_cleared_col(me.id),
            ),
        )
        .order_by(DmConversation.last_message_at.desc().nullslast())
    )
    rows = (await db.execute(stmt)).all()

    return [
        ContactOut(
            id=str(r.id),
            username=r.username,
            avatar_seed=r.avatar_seed,
            full_name=r.full_name,
            initial=_initial(r.full_name, r.username),
            online=_is_online(r.last_seen),
            unread=int(r.unread or 0),
            last_message_preview=r.last_message_preview,
            last_message_at=r.last_message_at.isoformat() if r.last_message_at else None,
            last_message_from_me=(r.last_sender_id == me.id),
        )
        for r in rows
    ]


@router.get("/search", response_model=list[ContactOut])
async def search(
    q: str = Query(..., min_length=0),
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Find someone by @username or name.

    CROSS-USER READ (intentional — see module docstring). PREFIX match only: a
    leading `%` would both defeat the index and let anyone dump the directory
    two characters at a time.
    """
    term = (q or '').strip().lstrip('@').lower()
    if len(term) < MIN_SEARCH_LEN:
        return []

    pattern = term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'

    stmt = (
        select(User.id, User.username, User.avatar_seed, User.full_name, DmPresence.last_seen)
        .select_from(User)
        .outerjoin(DmPresence, DmPresence.user_id == User.id)
        .where(
            User.id != me.id,
            User.is_active.is_(True),
            or_(User.username.like(pattern), User.full_name.ilike(pattern)),
        )
        .order_by((User.username == term).desc(), User.username.asc())
        .limit(SEARCH_LIMIT)
    )
    rows = (await db.execute(stmt)).all()

    return [
        ContactOut(
            id=str(r.id),
            username=r.username,
            avatar_seed=r.avatar_seed,
            full_name=r.full_name,
            initial=_initial(r.full_name, r.username),
            online=_is_online(r.last_seen),
        )
        for r in rows
    ]


@router.get("/online", response_model=list[ContactOut])
async def online_friends(
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Everyone who has the app open right now.

    CROSS-USER READ (intentional — see module docstring). Distinct from
    `/contacts`, which only knows people you have already messaged: this is how
    you discover that someone you've never talked to is around. Same whitelist,
    bounded by the presence window and a hard limit.
    """
    cutoff = datetime.utcnow() - timedelta(seconds=PRESENCE_WINDOW_S)

    stmt = (
        select(User.id, User.username, User.avatar_seed, User.full_name, DmPresence.last_seen)
        .select_from(DmPresence)
        .join(User, User.id == DmPresence.user_id)
        .where(
            User.id != me.id,
            User.is_active.is_(True),
            DmPresence.last_seen >= cutoff,
        )
        .order_by(DmPresence.last_seen.desc())
        .limit(ONLINE_LIMIT)
    )
    rows = (await db.execute(stmt)).all()

    return [
        ContactOut(
            id=str(r.id),
            username=r.username,
            avatar_seed=r.avatar_seed,
            full_name=r.full_name,
            initial=_initial(r.full_name, r.username),
            online=True,
        )
        for r in rows
    ]


@router.get("/threads/{other_id}/messages", response_model=ThreadPage)
async def thread_messages(
    other_id: str,
    before: int | None = Query(None, description="return messages with seq < this"),
    limit: int = Query(30, ge=1, le=100),
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    other = await _resolve_other(db, me, other_id)
    conv = await _get_conversation(db, me.id, other.id)
    if conv is None:
        return ThreadPage(messages=[], has_more=False)

    stmt = select(DmMessage).where(DmMessage.conversation_id == conv.id)

    # Anything from before I cleared this conversation is gone — for me.
    cleared = _my_cleared_at(conv, me.id)
    if cleared is not None:
        stmt = stmt.where(DmMessage.created_at > cleared)

    if before is not None:
        stmt = stmt.where(DmMessage.seq < before)
    stmt = stmt.order_by(DmMessage.seq.desc()).limit(limit + 1)

    rows = list((await db.execute(stmt)).scalars().all())
    has_more = len(rows) > limit
    rows = rows[:limit]
    rows.reverse()  # ascending for display

    return ThreadPage(messages=[_msg_out(m) for m in rows], has_more=has_more)


@router.post("/threads/{other_id}/messages", response_model=MessageOut)
async def send_message(
    other_id: str,
    data: MessageCreate,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    other = await _resolve_other(db, me, other_id)  # 400 on self-DM, 404 on unknown
    body = _sanitize_body(data.body)

    since = datetime.utcnow() - timedelta(seconds=RATE_LIMIT_WINDOW_S)
    recent = await db.execute(
        select(func.count()).select_from(DmMessage).where(
            DmMessage.sender_id == me.id, DmMessage.created_at > since
        )
    )
    if int(recent.scalar() or 0) >= RATE_LIMIT_MAX_SENDS:
        raise HTTPException(status_code=429, detail="האטו — נשלחו יותר מדי הודעות")

    conv = await _get_or_create_conversation(db, me.id, other.id)

    now = datetime.utcnow()
    msg = DmMessage(
        conversation_id=conv.id,
        sender_id=me.id,
        recipient_id=other.id,
        body=body,
        created_at=now,
    )
    db.add(msg)

    conv.last_message_at = now
    conv.last_message_preview = body[:PREVIEW_LEN]
    conv.last_sender_id = me.id
    # Bump the RECIPIENT's counter, never my own.
    if conv.user_a_id == other.id:
        conv.a_unread_count = (conv.a_unread_count or 0) + 1
    else:
        conv.b_unread_count = (conv.b_unread_count or 0) + 1

    await db.commit()
    await db.refresh(msg)  # pull the server-generated `seq`

    return _msg_out(msg, client_id=data.client_id)


@router.get("/poll", response_model=PollOut)
async def poll(
    since: int = Query(0, ge=0),
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """New messages addressed TO me since a cursor.

    Incoming only. Because my own sends never echo back, the client never has to
    dedupe a polled message against its own optimistic bubble.
    """
    stmt = (
        select(DmMessage)
        .where(DmMessage.recipient_id == me.id, DmMessage.seq > since)
        .order_by(DmMessage.seq.asc())
        .limit(200)
    )
    rows = list((await db.execute(stmt)).scalars().all())
    cursor = rows[-1].seq if rows else since

    return PollOut(
        messages=[_msg_out(m) for m in rows],
        cursor=cursor,
        total_unread=await _total_unread(db, me.id),
    )


@router.delete("/threads/{other_id}")
async def delete_thread(
    other_id: str,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete this conversation — FOR ME ONLY.

    The `dm_conversations` row and its messages are shared with the other person,
    so we never drop them: that would silently erase their history from under
    them. Instead we stamp MY side's `cleared_at`. Everything at or before it
    disappears from my contacts list and my thread; their view is untouched. If
    they message me again, the thread comes back with just the new message.
    """
    other = await _resolve_other(db, me, other_id)
    conv = await _get_conversation(db, me.id, other.id)
    if conv is None:
        return {"ok": True}

    now = datetime.utcnow()
    if conv.user_a_id == me.id:
        conv.a_cleared_at = now
        conv.a_unread_count = 0
        conv.a_last_read_at = now
    else:
        conv.b_cleared_at = now
        conv.b_unread_count = 0
        conv.b_last_read_at = now
    await db.commit()

    return {"ok": True, "total_unread": await _total_unread(db, me.id)}


@router.post("/threads/{other_id}/read")
async def mark_read(
    other_id: str,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    other = await _resolve_other(db, me, other_id)
    conv = await _get_conversation(db, me.id, other.id)
    if conv is None:
        return {"ok": True, "unread": 0}

    now = datetime.utcnow()
    if conv.user_a_id == me.id:
        conv.a_unread_count = 0
        conv.a_last_read_at = now
    else:
        conv.b_unread_count = 0
        conv.b_last_read_at = now
    await db.commit()

    return {"ok": True, "unread": 0}
