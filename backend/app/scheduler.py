import asyncio
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import func, select

from app.config import settings
from app.database import async_session
from app.models.fund_track import FundTrack
from app.models.mailbox_config import MailboxConfig
from app.models.portal_credential import PortalCredential
from app.models.portal_run import PortalRun
from app.services.fund_scraper import update_fund_tracks
from app.services.mail_intake.poller import poll_mailbox
from app.services.subscription_service import process_renewals
from app.services.portal_automation.runner import run_automation
from app.services.maslaka import orchestration as maslaka_orchestration

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# Per credential. Matches runner.RUN_HARD_TIMEOUT_S — the Harel consolidated run
# now loops ALL accounts in the מספר-חשבון dropdown (production + נפרעים drills
# per account), so a multi-account user legitimately exceeds the old 300s.
PORTAL_RUN_TIMEOUT_S = 720

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


async def scrape_fund_tracks_job():
    """Open a session, run the mygemel scraper, commit. Wrapper for the cron."""
    try:
        async with async_session() as db:
            await update_fund_tracks(db)
    except Exception as e:
        logger.error(f"fund_tracks scrape job failed: {e}")


async def run_maslaka_poll() -> None:
    """System-wide clearinghouse poll: walk the vault inbox, ingest each XML,
    expire stale inquiries. No-ops gracefully on empty inbox / local mock.

    Gated by `MASLAKA_ENABLED` so a fresh deploy doesn't start hammering an
    unconfigured vault on day one."""
    if not settings.MASLAKA_ENABLED:
        return
    try:
        async with async_session() as db:
            stats = await maslaka_orchestration.poll_and_ingest(db, user_id=None)
            expired = await maslaka_orchestration.expire_stale_inquiries(db)
            if stats["scanned"] or expired:
                logger.info(
                    "maslaka.poll: scanned=%d feedback=%d holdings=%d unknown=%d errors=%d expired=%d",
                    stats["scanned"], stats["feedback_ingested"], stats["holdings_ingested"],
                    stats["unknown"], stats["errors"], expired,
                )
    except Exception as e:
        logger.error("maslaka.poll job failed: %s", e)


async def run_hachshara_mail_poll() -> None:
    """Pull the emailed Hachshara production zip from every connected mailbox.

    Gated by `HACHSHARA_MAIL_ENABLED` so a fresh deploy never polls an
    unconfigured mailbox. Each mailbox gets its own session and its own `try`:
    one locked Google account must not starve the other tenants. `poll_mailbox`
    itself never raises and applies its own backoff.

    Only microsoft/google are polled — an `other` (forwarding) mailbox is pushed
    to us by Resend and has nothing to pull.
    """
    if not settings.HACHSHARA_MAIL_ENABLED:
        return
    try:
        async with async_session() as db:
            result = await db.execute(
                select(MailboxConfig).where(
                    MailboxConfig.is_active.is_(True),
                    MailboxConfig.mail_host.in_(("microsoft", "google")),
                )
            )
            configs = result.scalars().all()
    except Exception as e:
        logger.error("hachshara_mail.poll: could not list mailboxes: %s", e)
        return

    total = 0
    for cfg in configs:
        try:
            async with async_session() as db:
                fresh = await db.get(MailboxConfig, cfg.id)
                if fresh:
                    total += await poll_mailbox(db, fresh)
        except Exception as e:
            logger.error("hachshara_mail.poll: mailbox %s failed: %s", cfg.id, e)
    if total:
        logger.info("hachshara_mail.poll: ingested %d file(s)", total)


async def run_maslaka_retention() -> None:
    """Daily retention sweep — null out `pension_raw_payloads.ciphertext` past
    `MASLAKA_RETENTION_DAYS`. Audit + lifecycle rows are preserved."""
    if not settings.MASLAKA_ENABLED:
        return
    try:
        async with async_session() as db:
            purged = await maslaka_orchestration.purge_old_payloads(db)
            if purged:
                logger.info("maslaka.retention: purged %d old raw payloads", purged)
    except Exception as e:
        logger.error("maslaka.retention job failed: %s", e)


# Refresh the ticker on startup if the latest scrape is older than this. The
# weekly cron only fires when the process is alive at exactly Sun 06:30 IST —
# dev `--reload` restarts and Railway redeploys routinely miss that window, so
# the ticker would otherwise stay frozen for weeks (it was stuck on מרץ/March
# from a 2026-05-15 scrape). Pension data publishes monthly, so a 7-day
# staleness threshold means every restart self-heals without re-scraping
# needlessly on quick restarts.
FUND_STALE_AFTER = timedelta(days=7)


async def _refresh_funds_if_stale():
    """One-shot fire on app start when fund_tracks have never been scraped OR
    the most recent scrape is older than FUND_STALE_AFTER. This makes the
    ticker self-heal on any deploy/restart instead of depending solely on the
    weekly cron firing while the process happens to be alive. Failures are
    non-fatal — logged and ignored.
    """
    try:
        async with async_session() as db:
            latest = (
                await db.execute(select(func.max(FundTrack.scraped_at)))
            ).scalar_one_or_none()
            if latest is not None and (datetime.now(timezone.utc) - latest) < FUND_STALE_AFTER:
                return
            reason = "never scraped" if latest is None else f"stale (last scrape {latest.isoformat()})"
            logger.info("fund_tracks: %s on startup, running scrape", reason)
            await update_fund_tracks(db)
    except Exception as e:
        logger.error(f"fund_tracks startup refresh failed: {e}")


def start_scheduler():
    """Start the background scheduler.

    - Renewals: 06:00 IST daily.
    - Portal automation tick: every hour at minute 7 (offset to avoid the
      top of the hour where many other systems run).
    - Fund-track scrape: weekly Sun 06:30 IST (offset from renewals so we
      don't double-schedule both at exactly 06:00). Pension data publishes
      monthly so weekly is plenty.
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
    scheduler.add_job(
        scrape_fund_tracks_job,
        CronTrigger(day_of_week="sun", hour=6, minute=30, timezone="Asia/Jerusalem"),
        id="scrape_fund_tracks",
        replace_existing=True,
        # If the process was briefly down at 06:30 (deploy/restart), still run
        # the job when it comes back within the grace window instead of waiting
        # a whole week; coalesce collapses multiple missed fires into one.
        misfire_grace_time=6 * 60 * 60,
        coalesce=True,
    )
    # Pension clearinghouse — only fires when MASLAKA_ENABLED is on, so safe
    # to register unconditionally.
    scheduler.add_job(
        run_maslaka_poll,
        IntervalTrigger(minutes=settings.MASLAKA_POLL_INTERVAL_MINUTES),
        id="maslaka_poll",
        replace_existing=True,
    )
    scheduler.add_job(
        run_maslaka_retention,
        CronTrigger(hour=3, minute=0, timezone="Asia/Jerusalem"),
        id="maslaka_retention",
        replace_existing=True,
    )
    # Hachshara production-by-email — only fires when HACHSHARA_MAIL_ENABLED is
    # on, so safe to register unconditionally.
    scheduler.add_job(
        run_hachshara_mail_poll,
        IntervalTrigger(minutes=settings.HACHSHARA_MAIL_POLL_INTERVAL_MINUTES),
        id="hachshara_mail_poll",
        replace_existing=True,
    )
    scheduler.start()
    asyncio.create_task(_refresh_funds_if_stale())
    logger.info(
        "Scheduler started — renewals 06:00 IST, portal tick hourly :07, "
        "fund scrape Sun 06:30 IST, maslaka poll every %dmin, maslaka retention 03:00 IST",
        settings.MASLAKA_POLL_INTERVAL_MINUTES,
    )


def stop_scheduler():
    """Shutdown the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
