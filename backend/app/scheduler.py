import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import async_session
from app.services.subscription_service import process_renewals

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def run_renewals():
    """Wrapper to create DB session and run renewal processing."""
    try:
        async with async_session() as db:
            stats = await process_renewals(db)
            logger.info(f"Scheduled renewal complete: {stats}")
    except Exception as e:
        logger.error(f"Scheduled renewal failed: {e}")


def start_scheduler():
    """Start the background scheduler. Run daily at 06:00 Israel time."""
    scheduler.add_job(
        run_renewals,
        CronTrigger(hour=6, minute=0, timezone="Asia/Jerusalem"),
        id="process_renewals",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — renewals will run daily at 06:00 IST")


def stop_scheduler():
    """Shutdown the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
