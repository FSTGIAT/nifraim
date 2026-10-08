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
from app.services.fund_scraper import update_fund_tracks
from app.services.mail_intake.poller import poll_mailbox
from app.services.subscription_service import process_renewals
from app.services.maslaka import orchestration as maslaka_orchestration

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


async def scrape_fund_tracks_job():
    """Open a session, run the mygemel scraper, commit. Wrapper for the cron."""
    try:
        async with async_session() as db:
            await update_fund_tracks(db)
    except Exception as e:
        logger.error(f"fund_tracks scrape job failed: {e}")


async def sync_fund_market_job():
    """Official גמל-נט / פנסיה-נט / ביטוח-נט (data.gov.il) → fund_market_monthly.
    Daily on the 1st–15th: the regulator publishes a month 1–2 months late, on no
    fixed day. A run with nothing new upserts the same rows (idempotent) — cheap."""
    try:
        from app.services import fund_market
        async with async_session() as db:
            await fund_market.sync(db)
    except Exception as e:
        logger.error(f"fund_market sync job failed: {e}")


async def run_maslaka_poll() -> None:
    """System-wide clearinghouse poll: walk the vault inbox, ingest each XML,
    expire stale inquiries. No-ops gracefully on empty inbox / local mock.

    Gated by `MASLAKA_ENABLED` so a fresh deploy doesn't start hammering an
    unconfigured vault on day one, AND by `MASLAKA_VAULT_HOST` so only the Gateway
    VM polls. On Railway the inbox path resolves to an empty container directory,
    so a poll there would report "scanned 0" forever while real feedback sat
    unread in the Gateway's IN folder — a green light over a dead exchange."""
    if not (settings.MASLAKA_ENABLED and settings.MASLAKA_VAULT_HOST):
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


async def run_maslaka_auto_subscriptions() -> None:
    """Daily: every approved agent who consented to automatic monthly production
    gets a subscription (2100) for any body that has appeared in their records.
    Only creates `pending` rows — the Gateway sends them — so it runs on the API
    host (not gated by MASLAKA_VAULT_HOST)."""
    if not settings.MASLAKA_ENABLED:
        return
    try:
        async with async_session() as db:
            n = await maslaka_orchestration.ensure_all_monthly_subscriptions(db)
            if n:
                logger.info("maslaka.auto_subscriptions: opened %d monthly subscription(s)", n)
    except Exception:
        logger.exception("maslaka.auto_subscriptions failed")


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
    - Monthly cycle tick: hourly on the hour (queues the 21st cycle batches,
      catch-up, cycle notifications).
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
    # Monthly cycle (מחזור) — the ONLY trigger of portal automation. Hourly on
    # the hour: at CYCLE_HOUR on CYCLE_DAY it queues every paid user's cycle
    # batch for their worker; every other tick is idempotent catch-up (app was
    # down at 06:00, portal logins added mid-month) + notifications.
    # The old per-credential `tick_portal_schedules` is RETIRED: it ran single
    # runs inline on Railway (geo-blocked, no merge) and bypassed the cycle.
    from app.services.cycle_service import run_cycle_tick
    scheduler.add_job(
        run_cycle_tick,
        CronTrigger(minute=0, timezone="Asia/Jerusalem"),
        id="monthly_cycle_tick",
        replace_existing=True,
        misfire_grace_time=30 * 60,
        coalesce=True,
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
    scheduler.add_job(
        sync_fund_market_job,
        CronTrigger(day="1-15", hour=7, minute=10, timezone="Asia/Jerusalem"),
        id="sync_fund_market",
        replace_existing=True,
        misfire_grace_time=6 * 60 * 60,
        coalesce=True,
    )
    # Pension clearinghouse — only fires when MASLAKA_ENABLED is on, so safe
    # to register unconditionally.
    scheduler.add_job(
        run_maslaka_auto_subscriptions,
        CronTrigger(hour=6, minute=20, timezone="Asia/Jerusalem"),
        id="maslaka_auto_subscriptions",
        replace_existing=True,
        misfire_grace_time=6 * 60 * 60,
        coalesce=True,
    )
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
    # מסלקה שיוך approval — watches submitted agents' inboxes for the helpdesk's
    # answer. Gated by MASLAKA_APPROVAL_WATCH_ENABLED.
    if settings.MASLAKA_APPROVAL_WATCH_ENABLED:
        from app.services.maslaka.approval_watch import run_approval_watch
        scheduler.add_job(
            run_approval_watch,
            IntervalTrigger(minutes=settings.MASLAKA_APPROVAL_WATCH_MINUTES),
            id="maslaka_approval_watch",
            replace_existing=True,
        )
    # AI mail agent — polls watched senders, triages + drafts. The job itself
    # returns early when MAIL_AGENT_ENABLED is off.
    from app.services.mail_agent.intake import purge_old_bodies, run_mail_agent_poll
    scheduler.add_job(
        run_mail_agent_poll,
        IntervalTrigger(minutes=settings.MAIL_AGENT_POLL_MINUTES),
        id="mail_agent_poll",
        replace_existing=True,
        # First check shortly after boot, not a full interval later — otherwise
        # every deploy/restart leaves new mail unread for MAIL_AGENT_POLL_MINUTES.
        next_run_time=datetime.now(timezone.utc) + timedelta(seconds=30),
    )
    # Agreement requests: follow insurers' replies to the wizard's "please send
    # my commission agreement" emails; a PDF reply is loaded to the shelf.
    from app.services.agreement_requests import run_agreement_request_poll
    scheduler.add_job(
        run_agreement_request_poll,
        IntervalTrigger(minutes=15),
        id="agreement_request_poll",
        replace_existing=True,
    )
    # Collection agent: follow insurers' replies to the unpaid-commission mails
    # the agent approved (services/collection_agent.py).
    from app.services.collection_agent import run_collection_poll
    scheduler.add_job(
        run_collection_poll,
        IntervalTrigger(minutes=15),
        id="collection_poll",
        replace_existing=True,
    )
    # Policy documents → doc_chunks. הר הביטוח fetches are written by the agent's local worker,
    # which never loads the embedding model; the cloud indexes them here (services/policies).
    from app.services.policies.embeddings import sweep as policies_sweep
    scheduler.add_job(
        policies_sweep,
        IntervalTrigger(minutes=2),
        id="policies_index_sweep",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        purge_old_bodies,
        CronTrigger(hour=3, minute=40, timezone="Asia/Jerusalem"),
        id="mail_agent_retention",
        replace_existing=True,
    )
    scheduler.start()
    asyncio.create_task(_refresh_funds_if_stale())
    logger.info(
        "Scheduler started — renewals 06:00 IST, monthly cycle tick hourly :00, "
        "fund scrape Sun 06:30 IST, maslaka poll every %dmin, maslaka retention 03:00 IST",
        settings.MASLAKA_POLL_INTERVAL_MINUTES,
    )


def stop_scheduler():
    """Shutdown the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
