"""הר הביטוח request queue — enqueue (the agent's click), claim/finish (the worker's run), finalize.

One active `harbituach` PortalRun per user. The run logs in ONCE (one OTP) and drains every
pending request of the user through "כניסה לתיק נוסף"; a request added while the run is live
is picked up by it. When a run ends, any request still pending with no run gets a fresh run,
so nothing is stranded — unless the run died before serving anyone (login/OTP failure), in which
case the pending requests fail with the same reason instead of looping forever.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from sqlalchemy import select, update

from app.models.harb_request import FINAL, OPEN, HarbRequest
from app.models.portal_credential import PortalCredential
from app.models.portal_run import PortalRun

logger = logging.getLogger(__name__)

KIND = "harbituach"
ACTIVE_RUN = ("pending", "running", "awaiting_otp", "downloading", "parsing")
WORKER_FRESH = timedelta(seconds=90)


class HarbGateError(Exception):
    """A gate refused the request — message is Hebrew, shown to the agent as is."""


async def credential(db, user_id) -> PortalCredential | None:
    return (await db.execute(select(PortalCredential).where(
        PortalCredential.user_id == user_id, PortalCredential.portal_kind == KIND,
        PortalCredential.is_active.is_(True)))).scalar_one_or_none()


async def worker_online(db, user_id) -> bool:
    from app.models.worker_heartbeat import WorkerHeartbeat
    from app.config import settings
    if getattr(settings, "WORKER_MODE", False):
        return True
    last = (await db.execute(select(WorkerHeartbeat.last_seen).where(
        WorkerHeartbeat.user_id == user_id).order_by(WorkerHeartbeat.last_seen.desc()).limit(1))).scalar_one_or_none()
    return bool(last and datetime.utcnow() - last <= WORKER_FRESH)


async def active_run(db, user_id) -> PortalRun | None:
    return (await db.execute(select(PortalRun).join(PortalCredential, PortalCredential.id == PortalRun.credential_id)
                             .where(PortalRun.user_id == user_id, PortalCredential.portal_kind == KIND,
                                    PortalRun.status.in_(ACTIVE_RUN))
                             .order_by(PortalRun.started_at.desc()).limit(1))).scalars().first()


async def open_request(db, user_id, idn: str) -> HarbRequest | None:
    return (await db.execute(select(HarbRequest).where(
        HarbRequest.user_id == user_id, HarbRequest.customer_id_number == idn,
        HarbRequest.status.in_(OPEN)).limit(1))).scalar_one_or_none()


STALE_MSG = "השליפה נקטעה (העובד או השרת הופעלו מחדש) — נסו שוב"


async def repair_stale(db, user_id) -> int:
    """Close open requests whose run ended without finalize — the worker's pending reaper and the
    server-start reaper fail runs directly. Without this the customer stays "open" forever (every
    new fetch refused) and the chat follower polls a request that will never move. Commits."""
    live = await active_run(db, user_id)
    rows = (await db.execute(select(HarbRequest).where(
        HarbRequest.user_id == user_id, HarbRequest.status.in_(OPEN)))).scalars().all()
    fixed = 0
    for r in rows:
        run = await db.get(PortalRun, r.portal_run_id) if r.portal_run_id else None
        dead = (run is not None and run.status not in ACTIVE_RUN) or (run is None and live is None)
        if r.status == "pending" and run is not None and run.status == "success" and live is None:
            dead = True        # a success that never got to finalize: nothing will pick this up
        if dead:
            r.status, r.error, r.completed_at = "failed", (run.error_message if run and run.status != "success" and run.error_message else STALE_MSG)[:500], datetime.utcnow()
            fixed += 1
    if fixed:
        await db.commit()
    return fixed


async def check_gates(db, user_id, idn: str) -> PortalCredential:
    """Same gates for the proposal card and for /act. Raises HarbGateError (Hebrew)."""
    await repair_stale(db, user_id)
    cred = await credential(db, user_id)
    if not cred:
        raise HarbGateError("עוד לא הוגדרו פרטי כניסה להר הביטוח — מוסיפים אותם בהגדרות → אוטומציה → הר הביטוח.")
    if not await worker_online(db, user_id):
        raise HarbGateError("העובד המקומי לא מחובר כרגע — הר הביטוח נשלף מהמחשב שלך בישראל. "
                            "ודא שהמחשב דלוק ומחובר ונסה שוב.")
    if await open_request(db, user_id, idn):
        raise HarbGateError("כבר יש שליפה פתוחה מהר הביטוח ללקוח הזה — התוצאה תגיע לכאן כשתסתיים.")
    await check_limits(db, user_id, idn)
    return cred


# a fetch that reached the site counts; one that died at login (wrong password, no SMS) does not
COUNTED = ("done", "not_found", *OPEN)


async def check_limits(db, user_id, idn: str) -> None:
    from sqlalchemy import func
    from app.config import settings
    day = datetime.utcnow() - timedelta(hours=24)
    base = select(func.count()).select_from(HarbRequest).where(HarbRequest.user_id == user_id)
    queued = (await db.execute(base.where(HarbRequest.status.in_(OPEN)))).scalar_one()
    if queued >= settings.HARB_MAX_QUEUE:
        raise HarbGateError(f"כבר {queued} שליפות מחכות בתור — נחכה שיסתיימו לפני שמוסיפים עוד.")
    today = (await db.execute(base.where(HarbRequest.created_at >= day, HarbRequest.status.in_(COUNTED)))).scalar_one()
    if today >= settings.HARB_DAILY_LIMIT:
        raise HarbGateError(f"הגעת למכסה של {settings.HARB_DAILY_LIMIT} שליפות מהר הביטוח ב-24 שעות — אפשר להמשיך מחר.")
    mine = (await db.execute(base.where(HarbRequest.customer_id_number == idn, HarbRequest.created_at >= day,
                                        HarbRequest.status.in_(COUNTED)))).scalar_one()
    if mine >= settings.HARB_CUSTOMER_DAILY_LIMIT:
        raise HarbGateError(f"הלקוח הזה כבר נשלף {mine} פעמים ב-24 השעות האחרונות — הנתונים בהר הביטוח לא משתנים כל כך מהר; אפשר שוב מחר.")


async def last_fetch(db, user_id, idn: str) -> HarbRequest | None:
    return (await db.execute(select(HarbRequest).where(
        HarbRequest.user_id == user_id, HarbRequest.customer_id_number == idn, HarbRequest.status == "done")
        .order_by(HarbRequest.completed_at.desc().nullslast()).limit(1))).scalar_one_or_none()


def refetch_question(req: HarbRequest, name: str | None) -> str:
    """'נשלף היום ב-10:42 — לשלוף שוב?' — the agent decides whether a fresh login + SMS is worth it."""
    from zoneinfo import ZoneInfo
    at = (req.completed_at or req.created_at).replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Asia/Jerusalem"))
    days = (datetime.now(ZoneInfo("Asia/Jerusalem")).date() - at.date()).days
    when = (f"היום ב-{at:%H:%M}" if days == 0 else f"אתמול ב-{at:%H:%M}" if days == 1
            else f"לפני {days} ימים ({at:%d/%m/%Y})")
    who = name or f"ת.ז {req.customer_id_number}"
    return (f"התיק הביטוחי של {who} כבר נשלף מהר הביטוח {when} ({req.policies_count or 0} כיסויים). "
            "לשלוף שוב? (שליפה נוספת = כניסה וקוד SMS נוספים; אחריה אראה מה השתנה)")


async def enqueue(db, user, idn: str, birth: date, issued: date, name: str | None = None) -> HarbRequest:
    """The agent's click. Creates the request, and a run only if none is live. Commits."""
    cred = await check_gates(db, user.id, idn)
    req = HarbRequest(user_id=user.id, customer_id_number=idn, customer_name=(name or None),
                      birth_date=birth, id_issue_date=issued, status="pending")
    db.add(req)
    await db.flush()
    run = await active_run(db, user.id)
    if run is None:
        run = PortalRun(user_id=user.id, credential_id=cred.id, status="pending")
        db.add(run)
        await db.flush()
        req.portal_run_id = run.id
    await db.commit()
    return req


async def claim_next(db, run: PortalRun) -> HarbRequest | None:
    """The run takes the oldest pending request of its user (its own first)."""
    req = (await db.execute(select(HarbRequest).where(
        HarbRequest.user_id == run.user_id, HarbRequest.status == "pending")
        .order_by((HarbRequest.portal_run_id == run.id).desc().nullslast(), HarbRequest.created_at)
        .limit(1).with_for_update(skip_locked=True))).scalars().first()
    if req is None:
        return None
    req.status, req.portal_run_id = "downloading", run.id
    await db.commit()
    return req


async def fail_request(db, req: HarbRequest, message: str, *, not_found: bool = False) -> None:
    req.status = "not_found" if not_found else "failed"
    req.error = (message or "")[:500]
    req.completed_at = datetime.utcnow()
    await db.commit()


async def finalize(db, run: PortalRun) -> None:
    """After the run ends (any outcome). Never raises."""
    try:
        reason = run.error_message or "השליפה מהר הביטוח נכשלה"
        served = (await db.execute(select(HarbRequest.id).where(
            HarbRequest.portal_run_id == run.id, HarbRequest.status.in_(FINAL)).limit(1))).first()
        # requests this run took but never finished
        await db.execute(update(HarbRequest).where(
            HarbRequest.portal_run_id == run.id, HarbRequest.status.in_(("running", "awaiting_otp", "downloading")))
            .values(status="failed", error=reason[:500], completed_at=datetime.utcnow()))
        pending = (await db.execute(select(HarbRequest).where(
            HarbRequest.user_id == run.user_id, HarbRequest.status == "pending"))).scalars().all()
        if pending:
            if run.status == "success" or served:
                # arrived after the drain → a fresh run (one login) serves them
                if await active_run(db, run.user_id) is None:
                    nxt = PortalRun(user_id=run.user_id, credential_id=run.credential_id, status="pending")
                    db.add(nxt)
                    await db.flush()
                    for r in pending:
                        r.portal_run_id = nxt.id
            else:
                # login/OTP never got through — the same failure would repeat; tell the agent
                for r in pending:
                    r.status, r.error, r.completed_at = "failed", reason[:500], datetime.utcnow()
        await db.commit()
    except Exception:  # noqa: BLE001
        logger.exception("harb: finalize run %s failed", getattr(run, "id", "?"))
        await db.rollback()


def effective_status(req: HarbRequest, run: PortalRun | None) -> str:
    """What the chat follower shows: the request's own final state, else its run's live stage."""
    if req.status in FINAL:
        return req.status
    if run is None:
        return req.status
    if run.status in ("failed", "timeout") and req.status != "pending":
        return "failed"          # run reaped/died without finalize (e.g. server restart)
    if run.status == "awaiting_otp" and req.status in ("pending", "running"):
        return "awaiting_otp"
    if run.status in ("running",) and req.status == "pending":
        return "running"
    return req.status


def parse_user_date(v) -> date | None:
    """Dates as agents type them: 22/05/1986 · 22.5.86 · 22-05-1986 · 22051986 · 1986-05-22.
    A date in the future or before 1900 is rejected (None) — never guessed."""
    import re
    from app.services.policies.harb_parser import parse_date
    s = str(v or "").strip()
    d = None
    if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", s):
        y, m, dd = (int(x) for x in s.split("-"))
        try:
            d = date(y, m, dd)
        except ValueError:
            d = None
    elif re.fullmatch(r"\d{8}", s):
        try:
            d = date(int(s[4:]), int(s[2:4]), int(s[:2]))
        except ValueError:
            d = None
    else:
        d = parse_date(s)
    if d is None or d > date.today() or d.year < 1900:
        return None
    return d
