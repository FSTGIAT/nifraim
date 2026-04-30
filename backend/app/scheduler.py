import asyncio
import logging
from datetime import datetime

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


async def run_renewals():
    """Wrapper to create DB session and run renewal processing."""
    try:
        async with async_session() as db:
            stats = await process_renewals(db)
            logger.info(f"Scheduled renewal complete: {stats}")
    except Exception as e:
        logger.error(f"Scheduled renewal failed: {e}")


async def run_scheduled_portal_automations():
    """Daily portal automation job — sequential per credential to keep RAM low.

    Iterates active credentials with schedule_enabled=True, creates a PortalRun
    for each, and awaits the runner. A per-credential timeout caps each run.
    """
    try:
        async with async_session() as db:
            cred_result = await db.execute(
                select(PortalCredential).where(
                    PortalCredential.schedule_enabled.is_(True),
                    PortalCredential.is_active.is_(True),
                )
            )
            creds = cred_result.scalars().all()

            run_ids: list = []
            for cred in creds:
                run = PortalRun(
                    user_id=cred.user_id,
                    credential_id=cred.id,
                    status="pending",
                    started_at=datetime.utcnow(),
                )
                db.add(run)
                await db.flush()
                run_ids.append(run.id)
            await db.commit()

        logger.info(f"Scheduled portal automation: {len(run_ids)} runs queued")

        for run_id in run_ids:
            try:
                await asyncio.wait_for(run_automation(run_id), timeout=PORTAL_RUN_TIMEOUT_S)
            except asyncio.TimeoutError:
                logger.error(f"Scheduled portal run {run_id} timed out at scheduler level")
            except Exception as e:
                logger.error(f"Scheduled portal run {run_id} failed: {e}")

    except Exception as e:
        logger.error(f"Scheduled portal automation outer failure: {e}")


def start_scheduler():
    """Start the background scheduler. Renewals 06:00 IST, portals 03:00 IST."""
    scheduler.add_job(
        run_renewals,
        CronTrigger(hour=6, minute=0, timezone="Asia/Jerusalem"),
        id="process_renewals",
        replace_existing=True,
    )
    scheduler.add_job(
        run_scheduled_portal_automations,
        CronTrigger(hour=3, minute=0, timezone="Asia/Jerusalem"),
        id="run_scheduled_portal_automations",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — renewals 06:00 IST, portal automations 03:00 IST")


def stop_scheduler():
    """Shutdown the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
