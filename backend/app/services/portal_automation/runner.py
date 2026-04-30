"""Orchestrates a single portal automation run.

Lifecycle (mirrors PortalRun.status / PortalRun.stage):
    pending → running(login) → awaiting_otp(otp) → downloading(download) →
    parsing(parse) → success | failed | timeout

The runner takes a `run_id` (the PortalRun must already exist with status=pending),
opens its own DB session (since it's invoked from BackgroundTasks/scheduler), and
updates the run row throughout.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.portal_credential import PortalCredential
from app.models.portal_run import PortalRun
from app.models.otp_inbox import OtpInbox
from app.services.portal_automation.companies import REGISTRY
from app.services.upload_ingest import ingest_file_bytes
from app.utils.crypto import decrypt

logger = logging.getLogger(__name__)


PROJECT_ROOT = Path(__file__).resolve().parents[4]
DOWNLOAD_ROOT = PROJECT_ROOT / "data" / "portal_downloads"
SCREENSHOT_ROOT = PROJECT_ROOT / "data" / "portal_screenshots"

OTP_WAIT_TIMEOUT_S = 90
OTP_POLL_INTERVAL_S = 1.0
RUN_HARD_TIMEOUT_S = 180


async def _set_status(db: AsyncSession, run: PortalRun, *, status: str | None = None,
                      stage: str | None = None, error: str | None = None,
                      finished: bool = False, screenshot_path: str | None = None) -> None:
    if status is not None:
        run.status = status
    if stage is not None:
        run.stage = stage
    if error is not None:
        run.error_message = error[:500]
    if screenshot_path is not None:
        run.screenshot_path = screenshot_path
    if finished:
        run.finished_at = datetime.utcnow()
    await db.commit()


async def _wait_for_otp(db: AsyncSession, run: PortalRun, user_id: uuid.UUID) -> str:
    """Poll otp_inbox for an OTP that arrived after this run started.

    Matches rows scoped to the user OR broadcast (user_id IS NULL). Marks the
    consumed row to prevent reuse.
    """
    deadline = asyncio.get_event_loop().time() + OTP_WAIT_TIMEOUT_S
    while asyncio.get_event_loop().time() < deadline:
        result = await db.execute(
            select(OtpInbox)
            .where(
                OtpInbox.consumed_at.is_(None),
                OtpInbox.otp_code.is_not(None),
                OtpInbox.received_at >= run.started_at,
                ((OtpInbox.user_id == user_id) | (OtpInbox.user_id.is_(None))),
            )
            .order_by(OtpInbox.received_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row:
            row.consumed_at = datetime.utcnow()
            row.portal_run_id = run.id
            await db.commit()
            return row.otp_code
        await asyncio.sleep(OTP_POLL_INTERVAL_S)
    raise TimeoutError("OTP not received within 90s")


async def _run_inner(db: AsyncSession, run: PortalRun) -> None:
    cred_result = await db.execute(
        select(PortalCredential).where(PortalCredential.id == run.credential_id)
    )
    cred = cred_result.scalar_one()

    plugin_cls = REGISTRY.get(cred.portal_kind)
    if plugin_cls is None:
        raise RuntimeError(f"Unknown portal_kind: {cred.portal_kind}")
    plugin = plugin_cls()

    password = decrypt(cred.encrypted_password)

    download_dir = DOWNLOAD_ROOT / str(run.id)
    screenshot_path = SCREENSHOT_ROOT / f"{run.id}.png"

    # Lazy import — playwright is heavy and only loaded inside an actual run.
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        try:
            await _set_status(db, run, status="running", stage="login")
            await plugin.login(page, cred.username, password)

            await _set_status(db, run, status="awaiting_otp", stage="otp")
            otp = await _wait_for_otp(db, run, cred.user_id)
            await plugin.submit_otp(page, otp)

            await _set_status(db, run, status="downloading", stage="download")
            files = await plugin.download_reports(page, download_dir)
            if not files:
                raise RuntimeError("Plugin returned no downloaded files")

            await _set_status(db, run, status="parsing", stage="parse")
            first_filename: str | None = None
            first_upload_id: uuid.UUID | None = None
            for path in files:
                content = path.read_bytes()
                upload = await ingest_file_bytes(
                    db,
                    user_id=cred.user_id,
                    content=content,
                    filename=path.name,
                    password=plugin.report_password,
                    commit=False,  # commit happens once at the end
                )
                if first_upload_id is None:
                    first_upload_id = upload.id
                    first_filename = path.name

            run.downloaded_filename = first_filename
            run.upload_id = first_upload_id
            await _set_status(db, run, status="success", finished=True)
        except Exception:
            await plugin._safe_screenshot(page, screenshot_path)
            raise
        finally:
            await context.close()
            await browser.close()


async def run_automation(run_id: uuid.UUID) -> None:
    """Top-level entry point. Owns its own DB session and never raises."""
    async with async_session() as db:
        result = await db.execute(select(PortalRun).where(PortalRun.id == run_id))
        run = result.scalar_one_or_none()
        if run is None:
            logger.error(f"PortalRun {run_id} not found")
            return

        cred_result = await db.execute(
            select(PortalCredential).where(PortalCredential.id == run.credential_id)
        )
        cred = cred_result.scalar_one()

        try:
            await asyncio.wait_for(_run_inner(db, run), timeout=RUN_HARD_TIMEOUT_S)
            cred.last_run_status = "success"
            cred.last_error = None
        except asyncio.TimeoutError:
            await _set_status(db, run, status="timeout",
                              error=f"Run exceeded {RUN_HARD_TIMEOUT_S}s", finished=True)
            cred.last_run_status = "timeout"
            cred.last_error = f"Run exceeded {RUN_HARD_TIMEOUT_S}s"
        except TimeoutError as e:
            await _set_status(db, run, status="failed", error=str(e), finished=True)
            cred.last_run_status = "failed"
            cred.last_error = str(e)
        except Exception as e:
            logger.exception(f"PortalRun {run_id} failed")
            await _set_status(db, run, status="failed", error=str(e),
                              finished=True,
                              screenshot_path=str(SCREENSHOT_ROOT / f"{run_id}.png"))
            cred.last_run_status = "failed"
            cred.last_error = str(e)
        finally:
            cred.last_run_at = datetime.utcnow()
            await db.commit()
