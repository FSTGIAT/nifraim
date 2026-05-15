import asyncio
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.database import async_session
from app.models.portal_credential import PortalCredential
from app.models.portal_run import PortalRun
from app.services.subscription_service import process_renewals
from app.services.portal_automation.runner import run_automation

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

PORTAL_RUN_TIMEOUT_S = 300  # per credential

# A credential is "due" when its last run was at least this many hours ago.
# Slightly under the natural cadence so a daily job at 09:00 still fires the
# next day even if the previous run took 30 minutes.
_DUE_THRESHOLDS_HOURS = {
    "daily": 23,
    "weekly": 24 * 7 - 1,
    "monthly": 24 * 30 - 1,
}


async def run_renewals():
    """Wrapper to create DB session and run renewal processing."""
    try:
        async with async_session() as db:
            stats = await process_renewals(db)
            logger.info(f"Scheduled renewal complete: {stats}")
    except Exception as e:
        logger.error(f"Scheduled renewal failed: {e}")


def _is_due(cred: PortalCredential, now: datetime) -> bool:
    threshold_hours = _DUE_THRESHOLDS_HOURS.get(cred.schedule_kind)
    if threshold_hours is None:
        return False
    if cred.last_run_at is None:
        return True
    return (now - cred.last_run_at) >= timedelta(hours=threshold_hours)


async def tick_portal_schedules():
    """Hourly scan: for every active credential whose cadence is due, create a
    PortalRun and fire the runner. Manual ('manual' schedule_kind) credentials
    are ignored.
    """
    try:
        now = datetime.utcnow()
        async with async_session() as db:
            cred_result = await db.execute(
                select(PortalCredential).where(
                    PortalCredential.is_active.is_(True),
                    PortalCredential.schedule_kind != "manual",
                )
            )
            creds = cred_result.scalars().all()
            due_creds = [c for c in creds if _is_due(c, now)]

            run_ids: list = []
            for cred in due_creds:
                run = PortalRun(
                    user_id=cred.user_id,
                    credential_id=cred.id,
                    status="pending",
                    started_at=now,
                )
                db.add(run)
                await db.flush()
                run_ids.append(run.id)
            if run_ids:
                await db.commit()

        if not run_ids:
            logger.debug("Scheduler tick: no due credentials")
            return
        logger.info(f"Scheduler tick: {len(run_ids)} portal run(s) queued")

        for run_id in run_ids:
            try:
                await asyncio.wait_for(run_automation(run_id), timeout=PORTAL_RUN_TIMEOUT_S)
            except asyncio.TimeoutError:
                logger.error(f"Scheduled portal run {run_id} timed out at scheduler level")
            except Exception as e:
                logger.error(f"Scheduled portal run {run_id} failed: {e}")

    except Exception as e:
        logger.error(f"Scheduler tick outer failure: {e}")


def start_scheduler():
    """Start the background scheduler.

    - Renewals: 06:00 IST daily.
    - Portal automation tick: every hour at minute 7 (offset to avoid the
      top of the hour where many other systems run).
    """
    scheduler.add_job(
        run_renewals,
        CronTrigger(hour=6, minute=0, timezone="Asia/Jerusalem"),
        id="process_renewals",
        replace_existing=True,
    )
    scheduler.add_job(
        tick_portal_schedules,
        CronTrigger(minute=7, timezone="Asia/Jerusalem"),
        id="tick_portal_schedules",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — renewals 06:00 IST, portal tick hourly :07")


def stop_scheduler():
    """Shutdown the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
