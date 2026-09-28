"""Monthly cycle (מחזור) — the ONLY way an agent's portal automation runs.

    signup ──► Production tab LOCKED ──► first 21st 06:00 ──► cycle batch (נפרעים M-1)
                 (rest of app open)        │
                                           ├─ production source MANUAL (until the מסלקה
                                           │  feed is live): upload opens once the cycle
                                           │  batch finished, for month M-1 only
                                           └─ production source MASLAKA: the 2100 lands
                                              on the 15th, nothing to upload

Rules (see docs/ARCHITECTURE.md "Monthly cycle"):
- A cycle fires on settings.CYCLE_DAY at CYCLE_HOUR, Asia/Jerusalem. Its period is
  the month BEFORE the cycle month (21/10 → September).
- A user's FIRST cycle is ALWAYS the cycle of the month after signup (signed 19/9 →
  21/10). Before it, only the Production tab is locked — never the rest of the app.
- A שיוך form SUBMITTED before MASLAKA_CUTOFF_DAY of month M → first automatic מסלקה
  production on MASLAKA_DAY of month M+1 (after the cutoff: M+2). A cycle uses the
  מסלקה as its production source when that date is on/before the cycle month's
  MASLAKA_DAY.
- A cycle batch is queued `pending` for the agent's local worker and NEVER runs
  inline on Railway. If the worker is offline it simply waits (it is exempt from
  orphan reaping while pending) and the worker claims it when it comes online.
- Every agent-facing event is a CycleNotification row (idempotent per
  user+kind+period), emailed once and shown once in the UI.

Everything date-related is a pure function of an injected `now` so the scenarios
are unit-testable (tests/test_cycle_service.py).
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)

IL = ZoneInfo("Asia/Jerusalem")

# Mirrors api/portal_automation.WORKER_LIVE_WINDOW_S (kept local: a service must
# not import an API module).
WORKER_LIVE_WINDOW_S = 90
# Don't cry "worker offline" the second the batch is created — the worker polls
# every 5s, give it a moment.
WORKER_WAITING_GRACE = timedelta(minutes=5)

TERMINAL_BATCH = {"success", "partial", "failed"}

HEBREW_MONTHS = [
    "", "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
    "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר",
]


def utc_now() -> datetime:
    """Aware UTC "now" for the cycle code — CYCLE_NOW_OVERRIDE when a local
    simulation sets it, the real clock otherwise."""
    if settings.CYCLE_NOW_OVERRIDE:
        return datetime.fromisoformat(settings.CYCLE_NOW_OVERRIDE).astimezone(timezone.utc)
    return datetime.now(timezone.utc)


# ─────────────────────────── pure date math ────────────────────────────────

def _add_months(y: int, m: int, k: int) -> tuple[int, int]:
    idx = y * 12 + (m - 1) + k
    return idx // 12, idx % 12 + 1


def _to_il(ts: datetime) -> datetime:
    """DB timestamps are naive UTC; make them aware Israel time."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(IL)


def cycle_moment(y: int, m: int) -> datetime:
    """The aware Israel-time instant the (y, m) cycle fires."""
    return datetime(y, m, settings.CYCLE_DAY, settings.CYCLE_HOUR, tzinfo=IL)


def launch_cycle() -> tuple[int, int]:
    y, m = settings.CYCLE_LAUNCH.split("-")
    return int(y), int(m)


def cycle_period(y: int, m: int) -> date:
    """Reporting month a cycle downloads: the month before the cycle month."""
    py, pm = _add_months(y, m, -1)
    return date(py, pm, 1)


def latest_cycle(now: datetime) -> tuple[int, int]:
    """(y, m) of the most recent cycle whose moment is <= now."""
    il = _to_il(now)
    y, m = il.year, il.month
    if il < cycle_moment(y, m):
        y, m = _add_months(y, m, -1)
    return y, m


def next_cycle(now: datetime) -> tuple[int, int]:
    """(y, m) of the first cycle whose moment is > now."""
    return _add_months(*latest_cycle(now), 1)


def first_cycle_for(signup: datetime) -> tuple[int, int]:
    """(y, m) of the user's first cycle: ALWAYS the cycle of the month after
    signup, whatever the day. Signed 19/9 → 21/10 (September נפרעים), which is
    exactly the month the מסלקה's first production (15/10) describes. Running
    21/9 instead would fetch August נפרעים with no production to match."""
    il = _to_il(signup)
    return _add_months(il.year, il.month, 1)


def maslaka_first_auto(submitted_at: datetime | None) -> date | None:
    """The date the first automatic מסלקה production lands, from the שיוך
    SUBMISSION date: the monthly 2100 goes out between the 24th and the cutoff
    (27th), and the מסלקה answers on the 15th of the next month. So before the
    cutoff → 15th of M+1 (signed 19/9 → 15/10, September production), on/after
    it → 15th of M+2."""
    if submitted_at is None:
        return None
    il = _to_il(submitted_at)
    offset = 1 if il.day < settings.MASLAKA_CUTOFF_DAY else 2
    y, m = _add_months(il.year, il.month, offset)
    return date(y, m, settings.MASLAKA_DAY)


def maslaka_deadline(now: datetime) -> date:
    """The last day a שיוך submitted from `now` on still makes the NEXT 15th:
    the day before the cutoff (26th) this month, or next month's once today is
    already on/after the cutoff."""
    il = _to_il(now)
    y, m = il.year, il.month
    if il.day >= settings.MASLAKA_CUTOFF_DAY:
        y, m = _add_months(y, m, 1)
    return date(y, m, settings.MASLAKA_CUTOFF_DAY - 1)


def production_source_for_cycle(y: int, m: int, maslaka_first: date | None) -> str:
    """'maslaka' when the מסלקה production for this cycle's period has landed by
    the cycle month's MASLAKA_DAY, else 'manual'."""
    if maslaka_first is not None and maslaka_first <= date(y, m, settings.MASLAKA_DAY):
        return "maslaka"
    return "manual"


def month_label(d: date) -> str:
    return f"{HEBREW_MONTHS[d.month]} {d.year}"


# ─────────────────────────── per-user state ────────────────────────────────

@dataclass
class CycleState:
    locked: bool                        # Production tab locked (pre-first-cycle)
    prelaunch: bool                     # before CYCLE_LAUNCH — legacy behaviour
    first_cycle_at: str                 # ISO, aware IL
    next_cycle_at: str                  # ISO, aware IL
    next_period: str                    # ISO date — what the next cycle downloads
    current_period: str | None          # ISO date — latest fired cycle's period (None while locked)
    current_period_label: str | None
    cycle_batch_id: str | None
    cycle_batch_status: str | None      # pending | running | success | partial | failed | None
    worker_waiting: bool                # pending cycle batch, worker offline
    production_source: str              # manual | maslaka (for the current cycle)
    manual_upload_open: bool
    needs_production_upload: bool       # manual source, open, and nothing uploaded yet
    maslaka_status: str                 # maslaka_agent_links.status or not_started
    maslaka_first_auto: str | None      # ISO date
    signup_at: str | None = None        # ISO, aware IL — when the agent signed up
    maslaka_submitted_at: str | None = None   # ISO, aware IL
    maslaka_approved_at: str | None = None    # ISO, aware IL
    maslaka_deadline: str | None = None       # ISO date — last day that still makes the next 15th
    maslaka_if_submitted_now: str | None = None  # ISO date — the 15th a submission today would give
    manual_run_allowed: bool = False    # admin, or legacy button before CYCLE_LAUNCH


async def _maslaka_link(db: AsyncSession, user_id: uuid.UUID):
    from app.models.maslaka_agent_link import MaslakaAgentLink
    return (await db.execute(
        select(MaslakaAgentLink).where(MaslakaAgentLink.user_id == user_id)
    )).scalar_one_or_none()


def _maslaka_first_from_link(link) -> date | None:
    # "Signed" = the agent SUBMITTED the form (approval can come later). A
    # rejected form does not count.
    if link is None or link.status not in ("submitted", "approved"):
        return None
    return maslaka_first_auto(link.submitted_at or link.approved_at)


async def worker_live(db: AsyncSession, user_id: uuid.UUID, now_utc: datetime) -> bool:
    from app.models.worker_heartbeat import WorkerHeartbeat
    if settings.WORKER_MODE:
        return True
    last = (await db.execute(
        select(WorkerHeartbeat.last_seen).where(WorkerHeartbeat.user_id == user_id)
    )).scalar_one_or_none()
    return bool(last) and (now_utc - last).total_seconds() <= WORKER_LIVE_WINDOW_S


async def _cycle_batch(db: AsyncSession, user_id: uuid.UUID, period: date):
    from app.models.portal_run_batch import PortalRunBatch
    return (await db.execute(
        select(PortalRunBatch).where(
            PortalRunBatch.user_id == user_id,
            PortalRunBatch.trigger == "cycle",
            PortalRunBatch.cycle_period == period,
        )
    )).scalar_one_or_none()


async def _has_production_for(db: AsyncSession, user_id: uuid.UUID, period: date) -> bool:
    from app.models.upload import FileUpload
    n = (await db.execute(
        select(func.count(FileUpload.id)).where(
            FileUpload.user_id == user_id,
            FileUpload.is_production.is_(True),
            FileUpload.period_month == period,
        )
    )).scalar() or 0
    return n > 0


async def _has_any_production(db: AsyncSession, user_id: uuid.UUID) -> bool:
    from app.models.upload import FileUpload
    n = (await db.execute(
        select(func.count(FileUpload.id)).where(
            FileUpload.user_id == user_id,
            FileUpload.file_category == "production",
        )
    )).scalar() or 0
    return n > 0


async def _fresh_comparison_exists(db: AsyncSession, user_id: uuid.UUID, since_utc: datetime) -> bool:
    """A persisted comparison computed at/after `since_utc` (naive UTC)."""
    from app.models.commission_comparison import CommissionComparison
    since = since_utc.replace(tzinfo=timezone.utc)
    n = (await db.execute(
        select(func.count(CommissionComparison.id)).where(
            CommissionComparison.user_id == user_id,
            CommissionComparison.computed_at >= since,
        )
    )).scalar() or 0
    return n > 0


async def _latest_production_upload_at(db: AsyncSession, user_id: uuid.UUID, period: date):
    from app.models.upload import FileUpload
    return (await db.execute(
        select(func.max(FileUpload.uploaded_at)).where(
            FileUpload.user_id == user_id,
            FileUpload.is_production.is_(True),
            FileUpload.period_month == period,
        )
    )).scalar_one_or_none()


async def compare_now(user_id: uuid.UUID) -> None:
    """Compute + persist the merged comparison in its own session. Called right
    after a manual cycle-period production upload, and by the tick as the
    catch-all (מסלקה ingest, batch end). Never raises."""
    from app.database import async_session
    from app.services.comparison_orchestrator import compute_merged_comparison
    try:
        async with async_session() as db:
            merged = await compute_merged_comparison(db, user_id)
            if merged.get("skip_reason"):
                logger.info("cycle compare skipped for %s: %s", user_id, merged["skip_reason"])
    except Exception as e:  # noqa: BLE001
        logger.warning("cycle compare failed for %s: %s", user_id, e)


def manual_run_allowed(user, state: "CycleState") -> bool:
    """Agents never run automation by hand — the monthly cycle does (from the
    first cycle; before launch there are simply no runs). Only support
    (admins) may run on demand. Decided 2026-09-28: admin-only even pre-launch."""
    return bool(getattr(user, "is_admin", False))


async def user_cycle_state(db: AsyncSession, user, now: datetime | None = None) -> CycleState:
    now_utc = (now or utc_now()).astimezone(timezone.utc).replace(tzinfo=None)
    now_aware = now_utc.replace(tzinfo=timezone.utc)

    fy, fm = first_cycle_for(user.created_at or now_utc)
    first_at = cycle_moment(fy, fm)
    ny, nm = next_cycle(now_aware)
    # Admins (support) are never locked out of the Production tab, and neither
    # is an agent who already HAS production (signed up before the cycle system
    # shipped and uploaded) — locking would hide data they already use.
    locked = (
        now_aware < first_at
        and not getattr(user, "is_admin", False)
        and not await _has_any_production(db, user.id)
    )

    link = await _maslaka_link(db, user.id)
    maslaka_first = _maslaka_first_from_link(link)

    current_period = None
    batch = None
    source = "manual"
    manual_open = False
    needs_upload = False
    waiting = False
    prelaunch = False
    if not locked and latest_cycle(now_aware) < launch_cycle():
        # The cycle system hasn't fired its first cycle yet: an existing user
        # keeps today's behaviour (upload open, period detected from the file).
        prelaunch = True
        manual_open = True
    elif not locked:
        ly, lm = latest_cycle(now_aware)
        current_period = cycle_period(ly, lm)
        source = production_source_for_cycle(ly, lm, maslaka_first)
        batch = await _cycle_batch(db, user.id, current_period)
        if batch is not None and batch.status == "pending":
            waiting = (
                not await worker_live(db, user.id, now_utc)
                and now_utc - batch.started_at >= WORKER_WAITING_GRACE
            )
        # Manual upload opens after THIS cycle's automation ended. A user who had
        # no batch this cycle (no portal logins yet) is not held hostage to it.
        batch_done = batch is None or batch.status in TERMINAL_BATCH
        manual_open = source == "manual" and batch_done
        if manual_open:
            needs_upload = not await _has_production_for(db, user.id, current_period)

    return CycleState(
        locked=locked,
        prelaunch=prelaunch,
        first_cycle_at=first_at.isoformat(),
        next_cycle_at=cycle_moment(ny, nm).isoformat(),
        next_period=cycle_period(ny, nm).isoformat(),
        current_period=current_period.isoformat() if current_period else None,
        current_period_label=month_label(current_period) if current_period else None,
        cycle_batch_id=str(batch.id) if batch else None,
        cycle_batch_status=batch.status if batch else None,
        worker_waiting=waiting,
        production_source=source,
        manual_upload_open=manual_open,
        needs_production_upload=needs_upload,
        maslaka_status=link.status if link else "not_started",
        maslaka_first_auto=maslaka_first.isoformat() if maslaka_first else None,
        signup_at=_to_il(user.created_at).isoformat() if user.created_at else None,
        maslaka_submitted_at=_to_il(link.submitted_at).isoformat() if link and link.submitted_at else None,
        maslaka_approved_at=_to_il(link.approved_at).isoformat() if link and link.approved_at else None,
        maslaka_deadline=maslaka_deadline(now_aware).isoformat(),
        maslaka_if_submitted_now=maslaka_first_auto(now_utc).isoformat(),
    )


def state_dict(state: CycleState) -> dict:
    return asdict(state)


# ─────────────────────────── notifications ─────────────────────────────────

_EMAIL_COPY = {
    "worker_waiting": (
        "המחזור החודשי ממתין למחשב שלך",
        "ההורדה האוטומטית של {period} מוכנה לצאת לדרך, אבל המחשב שמריץ אותה לא מחובר כרגע. "
        "ברגע שהמחשב יודלק והעובד יתחבר — ההורדה תתחיל מעצמה. אין צורך לעשות דבר מעבר לזה.",
    ),
    "upload_production": (
        "הנפרעים של {period} הגיעו — העלה/י את קובץ הפרודוקציה",
        "ההורדה האוטומטית של הנפרעים ל{period} הסתיימה. כדי להשלים את ההשוואה, "
        "העלה/י בלשונית פרודוקציה את קובץ הפרודוקציה של {period} (מאתר המסלקה).",
    ),
    "cycle_failed": (
        "חלק מההורדות במחזור של {period} לא הושלמו",
        "המחזור החודשי של {period} הסתיים, אך לא כל החברות הורדו בהצלחה. "
        "הפרטים המלאים מופיעים בלשונית ההורדה האוטומטית.",
    ),
    "comparison_ready": (
        "השוואת הנפרעים של {period} מוכנה",
        "יש לנו גם את הפרודוקציה וגם את הנפרעים של {period} — ההשוואה מוכנה לצפייה בלשונית השוואת נפרעים.",
    ),
}


def notification_copy(kind: str, period: date) -> tuple[str, str]:
    title, body = _EMAIL_COPY[kind]
    label = month_label(period)
    return title.format(period=label), body.format(period=label)


async def _send_cycle_email(to_email: str, name: str | None, kind: str, period: date) -> None:
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from app.services.email_service import FRONTEND_URL, send_raw_message

    title, body = notification_copy(kind, period)
    html = f"""
    <div dir="rtl" style="font-family: 'Heebo', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 32px; background: #ffffff; border-radius: 12px;">
        <h1 style="color: #181818; font-size: 22px; margin: 0 0 20px;">Nifraim</h1>
        <h2 style="color: #181818; font-size: 19px;">שלום{' ' + name if name else ''},</h2>
        <p style="color: #181818; font-size: 17px; font-weight: 600;">{title}</p>
        <p style="color: #3E3E3C; font-size: 15px; line-height: 1.8;">{body}</p>
        <div style="margin: 28px 0; text-align: center;">
            <a href="{FRONTEND_URL}/" style="display: inline-block; padding: 13px 30px; background: #181818; color: #ffffff; text-decoration: none; border-radius: 8px; font-size: 15px;">כניסה ל-Nifraim</a>
        </div>
        <hr style="border: none; border-top: 1px solid #DDDBDA; margin: 24px 0;" />
        <p style="color: #706E6B; font-size: 12px; text-align: center;">בברכה, Nifraim</p>
    </div>
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{title} — Nifraim"
    msg["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html", "utf-8"))
    await send_raw_message(msg)


async def notify(db: AsyncSession, user, kind: str, period: date) -> bool:
    """Insert the (user, kind, period) notification once; email it on first
    insert. Returns True when this call created it. Commits."""
    from app.models.cycle_notification import CycleNotification

    res = await db.execute(
        pg_insert(CycleNotification)
        .values(id=uuid.uuid4(), user_id=user.id, kind=kind, period=period, created_at=datetime.utcnow())
        .on_conflict_do_nothing(constraint="uq_cycle_notifications_user_kind_period")
        .returning(CycleNotification.id)
    )
    new_id = res.scalar_one_or_none()
    await db.commit()
    if new_id is None:
        return False
    try:
        await _send_cycle_email(user.email, getattr(user, "full_name", None), kind, period)
        row = await db.get(CycleNotification, new_id)
        if row is not None:
            row.emailed_at = datetime.utcnow()
            await db.commit()
    except Exception as e:  # noqa: BLE001 — the in-app modal still carries it
        logger.warning("cycle email %s to user %s failed: %s", kind, user.id, e)
    return True


# ─────────────────────────── the tick ──────────────────────────────────────

async def _has_active_credentials(db: AsyncSession, user_id: uuid.UUID) -> bool:
    from app.models.portal_credential import PortalCredential
    n = (await db.execute(
        select(func.count(PortalCredential.id)).where(
            PortalCredential.user_id == user_id,
            PortalCredential.is_active.is_(True),
        )
    )).scalar() or 0
    return n > 0


async def _queue_cycle_batch(db: AsyncSession, user_id: uuid.UUID, period: date) -> bool:
    """Queue this user's cycle batch for `period` (pending, for the worker).
    The partial unique index makes a double fire a no-op. Commits."""
    from app.models.portal_run_batch import PortalRunBatch

    res = await db.execute(
        pg_insert(PortalRunBatch)
        .values(
            id=uuid.uuid4(), user_id=user_id, status="pending", trigger="cycle",
            cycle_period=period, started_at=datetime.utcnow(),
            total=0, succeeded=0, failed=0,
        )
        .on_conflict_do_nothing(
            index_elements=["user_id", "cycle_period"],
            index_where=PortalRunBatch.trigger == "cycle",
        )
        .returning(PortalRunBatch.id)
    )
    created = res.scalar_one_or_none() is not None
    await db.commit()
    return created


async def _tick_user(db: AsyncSession, user, now_aware: datetime) -> None:
    now_utc = now_aware.astimezone(timezone.utc).replace(tzinfo=None)
    ly, lm = latest_cycle(now_aware)
    if (ly, lm) < launch_cycle():
        return  # the cycle system has not launched yet
    if (ly, lm) < first_cycle_for(user.created_at or now_utc):
        return  # still before this user's first cycle (Production tab locked)
    period = cycle_period(ly, lm)

    # 1. Queue the cycle batch. Also catches up: a user who added portal logins
    #    mid-month, or an app that was down at 06:00, gets it on the next tick.
    batch = await _cycle_batch(db, user.id, period)
    if batch is None and await _has_active_credentials(db, user.id):
        if await _queue_cycle_batch(db, user.id, period):
            logger.info("cycle %s: queued batch for user %s", period, user.id)
        batch = await _cycle_batch(db, user.id, period)

    # 2. Waiting for an offline worker → tell the agent (once per period).
    if (
        batch is not None and batch.status == "pending"
        and now_utc - batch.started_at >= WORKER_WAITING_GRACE
        and not await worker_live(db, user.id, now_utc)
    ):
        await notify(db, user, "worker_waiting", period)

    # 3. Cycle automation ended.
    link = await _maslaka_link(db, user.id)
    source = production_source_for_cycle(ly, lm, _maslaka_first_from_link(link))
    has_prod = await _has_production_for(db, user.id, period)
    if batch is not None and batch.status in TERMINAL_BATCH:
        if batch.status in ("partial", "failed"):
            await notify(db, user, "cycle_failed", period)
        if source == "manual" and not has_prod:
            await notify(db, user, "upload_production", period)

    # 4. Both sides exist for the period → make sure a comparison was computed
    #    AFTER both landed (covers the מסלקה ingest and any missed hook), and
    #    only then tell the agent it is ready.
    has_nifraim = batch is not None and batch.merged_commission_upload_id is not None
    if has_prod and has_nifraim:
        prod_at = await _latest_production_upload_at(db, user.id, period)
        since = max(t for t in (prod_at, batch.finished_at) if t is not None)
        if not await _fresh_comparison_exists(db, user.id, since):
            await compare_now(user.id)
        if await _fresh_comparison_exists(db, user.id, since):
            await notify(db, user, "comparison_ready", period)


async def run_cycle_tick(now: datetime | None = None) -> None:
    """Hourly (and at 06:00 on the cycle day). Idempotent end to end."""
    from app.database import async_session
    from app.models.user import User

    now_aware = now or utc_now()
    try:
        async with async_session() as db:
            users = (await db.execute(
                select(User).where(User.is_active.is_(True))
            )).scalars().all()
            for user in users:
                try:
                    await _tick_user(db, user, now_aware)
                except Exception as e:  # noqa: BLE001 — one user never blocks the rest
                    await db.rollback()
                    logger.error("cycle tick failed for user %s: %s", user.id, e)
    except Exception as e:  # noqa: BLE001
        logger.error("cycle tick outer failure: %s", e)
