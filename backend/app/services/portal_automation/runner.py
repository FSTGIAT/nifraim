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
import inspect
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.models.portal_credential import PortalCredential
from app.models.portal_run import PortalRun
from app.models.otp_inbox import OtpInbox
from app.services.portal_automation.companies import REGISTRY
from app.services.upload_ingest import ingest_file_bytes, schedule_post_ingest
from app.utils.crypto import decrypt

logger = logging.getLogger(__name__)


def _parse_proxy(proxy_url: str) -> dict | None:
    """Parse a proxy URL ("http://user:pass@host:port" or "http://host:port")
    into Playwright's proxy dict {server, username?, password?}. Returns None
    for an empty/invalid value so the caller connects directly. Credentials go
    in their own keys (Playwright wants the server WITHOUT inline auth)."""
    proxy_url = (proxy_url or "").strip()
    if not proxy_url:
        return None
    from urllib.parse import urlparse
    try:
        u = urlparse(proxy_url if "://" in proxy_url else f"http://{proxy_url}")
        if not u.hostname:
            return None
        server = f"{u.scheme or 'http'}://{u.hostname}"
        if u.port:
            server += f":{u.port}"
        out: dict = {"server": server}
        if u.username:
            out["username"] = u.username
        if u.password:
            out["password"] = u.password
        return out
    except Exception:
        logger.warning("Invalid IL_RESIDENTIAL_PROXY value; connecting directly")
        return None


PROJECT_ROOT = Path(__file__).resolve().parents[4]
DOWNLOAD_ROOT = PROJECT_ROOT / "data" / "portal_downloads"
SCREENSHOT_ROOT = PROJECT_ROOT / "data" / "portal_screenshots"

OTP_WAIT_TIMEOUT_S = 240   # 4 minutes — accommodates manual OTP relay through chat
OTP_POLL_INTERVAL_S = 1.0
RUN_HARD_TIMEOUT_S = 360


class OtpTimeout(TimeoutError):
    """Raised when no OTP arrives within OTP_WAIT_TIMEOUT_S. Distinct from
    asyncio's wait_for timeout so the caller can render a different error."""


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


async def _wait_for_otp(
    db: AsyncSession,
    run: PortalRun,
    user_id: uuid.UUID,
    since: datetime,
    portal_kind: str | None = None,
) -> str:
    """Poll otp_inbox for an OTP that arrived after `since`.

    `since` is captured the moment this run enters `awaiting_otp` (i.e. right
    after login submits and the portal sends the SMS), NOT when the PortalRun
    row was created. In a "run all" batch the credentials run back-to-back, so
    matching from row-creation time (`run.started_at`) could let a late OTP from
    the PREVIOUS portal be consumed by the NEXT run — leaving the real code
    unmatched and the run stuck on the OTP screen. Anchoring on `since` scopes
    each wait to the code its own login triggered.

    Company routing: incoming OTPs are tagged at insert time with the insurer's
    BASE company token (`otp_inbox.portal_kind`, e.g. "phoenix"). We derive the
    same base from the running credential and accept ONLY a code tagged for this
    company OR an untagged code (NULL — no template matched / generic), preferring
    the company-tagged one. This means a code that arrived for a DIFFERENT company
    is never consumed here — the core fix for cross-company OTP theft in a batch.
    The NULL fallback guarantees no regression: a portal without a seeded template
    still works exactly as before (time-based only).

    Matches rows scoped to the user OR broadcast (user_id IS NULL). Marks the
    consumed row to prevent reuse.
    """
    base = (portal_kind or "").split("_")[0] or None
    deadline = asyncio.get_event_loop().time() + OTP_WAIT_TIMEOUT_S
    while asyncio.get_event_loop().time() < deadline:
        stmt = (
            select(OtpInbox)
            .where(
                OtpInbox.consumed_at.is_(None),
                OtpInbox.otp_code.is_not(None),
                OtpInbox.received_at >= since,
                ((OtpInbox.user_id == user_id) | (OtpInbox.user_id.is_(None))),
            )
        )
        if base:
            # Accept this company's tagged code or an untagged one; reject codes
            # tagged for other companies. Prefer the exact-company match, then
            # newest. NOTE: a plain `(portal_kind == base).desc()` mis-sorts —
            # for an untagged row `NULL == base` is SQL NULL, which sorts FIRST
            # under DESC (NULLS FIRST), beating the real match. A CASE coalesces
            # the untagged/non-match rows to 0 so the exact company wins.
            stmt = stmt.where(
                (OtpInbox.portal_kind == base) | (OtpInbox.portal_kind.is_(None))
            ).order_by(
                case((OtpInbox.portal_kind == base, 1), else_=0).desc(),
                OtpInbox.received_at.desc(),
            )
        else:
            stmt = stmt.order_by(OtpInbox.received_at.desc())
        result = await db.execute(stmt.limit(1))
        row = result.scalar_one_or_none()
        if row:
            row.consumed_at = datetime.utcnow()
            row.portal_run_id = run.id
            await db.commit()
            return row.otp_code
        await asyncio.sleep(OTP_POLL_INTERVAL_S)
    raise OtpTimeout("לא התקבל קוד OTP תוך 90 שניות. הזן קוד ידנית או הפעל מחדש.")


async def _run_inner(
    db: AsyncSession,
    run: PortalRun,
    *,
    make_active: bool = True,
    defer_post_ingest: bool = False,
) -> list[tuple]:
    """Log in, pass OTP, download and ingest one credential's files.

    Returns the ingested files as ``(upload_id, file_category, company_source)``
    tuples. ``make_active=False`` holds production uploads non-active (batch
    path — the merged file becomes active later). ``defer_post_ingest=True``
    skips the per-file snapshot/summary/auto-compare hooks so the batch can
    fire them after aggregation. Defaults preserve the single-run behaviour.
    """
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
        # Prefer the real Google Chrome binary over bundled Chromium — the
        # TLS / JA3 fingerprint of bundled Chromium is detectable by edge
        # WAFs (Harel reroutes to F5 APM with errorcode=19/22 based on it),
        # while real Chrome's fingerprint matches what their browser sends.
        # Falls back to chromium when chrome isn't installed.
        try:
            browser = await pw.chromium.launch(
                channel="chrome",
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    # Containers default to a tiny 64MB /dev/shm; Chrome fills it
                    # and the tab/renderer crashes (Railway "Crashed!" during a
                    # batch). Write shared memory to /tmp instead. Standard
                    # container fix; does NOT change the TLS/JA3 fingerprint.
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
        except Exception:
            browser = await pw.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    # Containers default to a tiny 64MB /dev/shm; Chrome fills it
                    # and the tab/renderer crashes (Railway "Crashed!" during a
                    # batch). Write shared memory to /tmp instead. Standard
                    # container fix; does NOT change the TLS/JA3 fingerprint.
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
        # Israeli insurer WAFs geo-block Railway's foreign datacenter IP. Route
        # geo-blocked portals through an IL residential proxy when one is set;
        # otherwise (or for direct-OK portals like Migdal) connect directly.
        context_proxy = None
        if getattr(plugin, "needs_residential_proxy", True):
            # Per-portal zone selection: a portal whose insurer blocks the default
            # ISP zone's ASN (e.g. Harel) names a different zone var. Fall back to
            # the shared IL_RESIDENTIAL_PROXY when the portal-specific var is empty.
            proxy_env = getattr(plugin, "proxy_zone_env", "IL_RESIDENTIAL_PROXY")
            proxy_url = getattr(settings, proxy_env, "") or getattr(
                settings, "IL_RESIDENTIAL_PROXY", ""
            )
            context_proxy = _parse_proxy(proxy_url)
            if context_proxy and context_proxy.get("username"):
                # Pin ONE sticky residential IP for this whole run (login → OTP →
                # download must share an IP or the insurer WAF/F5-APM session
                # breaks). Bright Data: append `-session-<id>` to the username.
                # Per-run id → each run gets its own IP, no cross-run reuse.
                if "-session-" not in context_proxy["username"]:
                    context_proxy["username"] += f"-session-{run.id.hex[:12]}"
            if context_proxy:
                logger.info(
                    "Run %s (%s): routing via IL residential proxy %s",
                    run.id, cred.portal_kind, context_proxy.get("server"),
                )

        # Real-Chrome UA + viewport + locale so APM / WAF gates don't bounce
        # us based on the headless fingerprint.
        context = await browser.new_context(
            proxy=context_proxy,
            # The IL residential proxy (Bright Data) terminates TLS with its own
            # CA, so Playwright sees ERR_CERT_AUTHORITY_INVALID on the target's
            # HTTPS. Accept it ONLY when going through the proxy (the documented
            # `-k` equivalent); direct connections (e.g. Migdal) keep full TLS
            # validation. See memory `railway_ip_geoblocked_insurers`.
            ignore_https_errors=bool(context_proxy),
            accept_downloads=True,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 768},
            locale="he-IL",
            extra_http_headers={
                "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
                # Real Google Chrome's UA-CH brand list — Harel's edge
                # uses these to fingerprint real-Chrome vs Chromium.
                "sec-ch-ua": '"Google Chrome";v="124", "Chromium";v="124", "Not-A.Brand";v="99"',
                "sec-ch-ua-platform": '"Windows"',
                "sec-ch-ua-mobile": "?0",
            },
        )
        # Hide `navigator.webdriver` so bot detection doesn't flag the page.
        await context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'languages', {get: () => ['he-IL', 'he', 'en']});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            """
        )
        page = await context.new_page()
        try:
            await _set_status(db, run, status="running", stage="login")
            await plugin.login(page, cred.username, password)

            if plugin.requires_otp:
                # Anchor the OTP wait at this instant — login() just submitted,
                # which is what triggers the SMS. Only codes arriving from here
                # on belong to this run (see _wait_for_otp docstring).
                otp_since = datetime.utcnow()
                await _set_status(db, run, status="awaiting_otp", stage="otp")
                otp = await _wait_for_otp(
                    db, run, cred.user_id, otp_since, portal_kind=cred.portal_kind
                )
                await plugin.submit_otp(page, otp)

            # A consolidated multi-login plugin (e.g. Migdal mfte+apmaccess) can
            # call this to obtain a SECOND OTP after a second login inside
            # download_reports. It re-enters awaiting_otp with a FRESH `since`
            # (so it waits for the new code, not the already-consumed first one)
            # and routes by the same company key (cred.portal_kind).
            async def _request_otp_mid_download() -> str:
                # Backdate `since` by a buffer: a second-login SMS can arrive in
                # the 1-2s before this callback runs. Safe — the first code is
                # already consumed (consumed_at set) and matching is company-
                # routed, so the only unconsumed code in the window is this one.
                otp_since2 = datetime.utcnow() - timedelta(seconds=30)
                await _set_status(db, run, status="awaiting_otp", stage="otp_2")
                code = await _wait_for_otp(
                    db, run, cred.user_id, otp_since2, portal_kind=cred.portal_kind
                )
                await _set_status(db, run, status="downloading", stage="download")
                return code

            await _set_status(db, run, status="downloading", stage="download")
            # Only pass otp_provider / password to plugins that DECLARE them (or
            # accept **kwargs) — the other ~18 plugins keep their existing
            # signature and never see them. Avoids a TypeError without touching
            # every plugin. `password` lets a consolidated plugin log into a
            # SECOND no-OTP site with the same creds (e.g. Phoenix folds the SFE
            # vault production into the agentportal run).
            dl_kwargs = {"username": cred.username}
            _dl_params = inspect.signature(plugin.download_reports).parameters
            _accepts_kw = any(p.kind == p.VAR_KEYWORD for p in _dl_params.values())
            if "otp_provider" in _dl_params or _accepts_kw:
                dl_kwargs["otp_provider"] = _request_otp_mid_download
            if "password" in _dl_params or _accepts_kw:
                dl_kwargs["password"] = password
            files = await plugin.download_reports(page, download_dir, **dl_kwargs)
            if not files:
                raise RuntimeError("Plugin returned no downloaded files")

            await _set_status(db, run, status="parsing", stage="parse")
            first_filename: str | None = None
            first_upload_id: uuid.UUID | None = None
            # (upload_id, file_category, company_source)
            ingested: list[tuple] = []
            for path in files:
                content = path.read_bytes()
                try:
                    upload, _fmt = await ingest_file_bytes(
                        db,
                        user_id=cred.user_id,
                        content=content,
                        filename=path.name,
                        password=plugin.report_password,
                        commit=False,  # commit happens once at the end
                        make_active=make_active,
                    )
                except Exception as ingest_err:
                    # Don't let a single bad file kill the whole run — log and
                    # carry on with the remaining files. The other downloads
                    # still produced value.
                    logger.warning(
                        "Ingest failed for %s (run %s): %s", path.name, run.id, ingest_err
                    )
                    continue
                if first_upload_id is None:
                    first_upload_id = upload.id
                    first_filename = path.name
                ingested.append((upload.id, upload.file_category, upload.company_source))

            run.downloaded_filename = first_filename
            run.upload_id = first_upload_id
            await _set_status(db, run, status="success", finished=True)

            # Fire downstream hooks per file:
            #   production → portal snapshots + production summary
            #   commission → auto-comparison against the active production
            # Shared with the manual upload route — single dispatcher.
            # A batch defers these until after the merged files are built.
            if not defer_post_ingest:
                for upload_id, file_category, _company in ingested:
                    try:
                        schedule_post_ingest(cred.user_id, upload_id, file_category)
                    except Exception as e:
                        logger.warning(
                            "Post-ingest dispatch failed for upload %s: %s", upload_id, e
                        )
            return ingested
        except Exception:
            await plugin._safe_screenshot(page, screenshot_path)
            await plugin._dump_page_state(page, screenshot_path)
            raise
        finally:
            await context.close()
            await browser.close()


async def _phone_change_inner(db: AsyncSession, run: PortalRun, new_phone: str) -> None:
    cred_result = await db.execute(
        select(PortalCredential).where(PortalCredential.id == run.credential_id)
    )
    cred = cred_result.scalar_one()

    plugin_cls = REGISTRY.get(cred.portal_kind)
    if plugin_cls is None:
        raise RuntimeError(f"Unknown portal_kind: {cred.portal_kind}")
    plugin = plugin_cls()

    password = decrypt(cred.encrypted_password)
    screenshot_path = SCREENSHOT_ROOT / f"{run.id}.png"

    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        try:
            # Step 1: standard login → OTP #1 (still routes to OLD phone since
            # we haven't changed the contact yet).
            await _set_status(db, run, status="running", stage="login")
            await plugin.login(page, cred.username, password)

            otp1_since = datetime.utcnow()
            await _set_status(db, run, status="awaiting_otp", stage="otp")
            otp1 = await _wait_for_otp(
                db, run, cred.user_id, otp1_since, portal_kind=cred.portal_kind
            )
            await plugin.submit_otp(page, otp1)

            # Step 2: navigate to settings, submit new phone → OTP #2 to OLD phone.
            await _set_status(db, run, status="downloading", stage="phone_update")
            await plugin.change_contact_phone(page, new_phone)

            # Step 3: wait for OTP #2 and confirm.
            otp2_since = datetime.utcnow()
            await _set_status(db, run, status="awaiting_otp", stage="phone_confirm")
            otp2 = await _wait_for_otp(
                db, run, cred.user_id, otp2_since, portal_kind=cred.portal_kind
            )
            await plugin.confirm_contact_phone_change(page, otp2)

            cred.contact_phone_synced_to = new_phone
            await _set_status(db, run, status="success", finished=True)
        except Exception:
            await plugin._safe_screenshot(page, screenshot_path)
            await plugin._dump_page_state(page, screenshot_path)
            raise
        finally:
            await context.close()
            await browser.close()


async def run_phone_change(run_id: uuid.UUID, new_phone: str) -> None:
    """Orchestrate a one-time contact-phone migration for a credential.

    The PortalRun row should already exist with kind='phone_change' and
    status='pending'. Mirrors run_automation's error-handling shape.
    """
    async with async_session() as db:
        result = await db.execute(select(PortalRun).where(PortalRun.id == run_id))
        run = result.scalar_one_or_none()
        if run is None:
            logger.error("PortalRun %s not found", run_id)
            return

        cred_result = await db.execute(
            select(PortalCredential).where(PortalCredential.id == run.credential_id)
        )
        cred = cred_result.scalar_one()

        try:
            await asyncio.wait_for(_phone_change_inner(db, run, new_phone), timeout=RUN_HARD_TIMEOUT_S)
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
            logger.exception("Phone-change run %s failed", run_id)
            await _set_status(db, run, status="failed", error=str(e),
                              finished=True,
                              screenshot_path=str(SCREENSHOT_ROOT / f"{run_id}.png"))
            cred.last_run_status = "failed"
            cred.last_error = str(e)
        finally:
            cred.last_run_at = datetime.utcnow()
            await db.commit()


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
        except OtpTimeout as e:
            # OTP-specific timeout — distinct from the run-wide hard timeout.
            await _set_status(db, run, status="failed", error=str(e), finished=True)
            cred.last_run_status = "failed"
            cred.last_error = str(e)
        except asyncio.TimeoutError:
            await _set_status(db, run, status="timeout",
                              error=f"Run exceeded {RUN_HARD_TIMEOUT_S}s", finished=True)
            cred.last_run_status = "timeout"
            cred.last_error = f"Run exceeded {RUN_HARD_TIMEOUT_S}s"
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
