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

from sqlalchemy import case, func, select
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
# Persistent Chrome profiles (one dir per portal_kind) for plugins that set
# `use_persistent_profile` — a real on-disk profile so reCAPTCHA Enterprise
# cookies/reputation survive across runs (e.g. Mor). See base.py flags.
BROWSER_PROFILE_ROOT = PROJECT_ROOT / "data" / "browser_profiles"
# Dropped inside a persistent profile once a run has SUCCEEDED with it. Its absence
# — not the absence of the directory — is what makes a profile "cold": a failed
# first attempt creates the dir, and treating that as warm would skip the warm-up on
# exactly the retry that needs it.
WARM_MARKER = ".nifraim_warm"


def _worker_note(msg: str) -> None:
    """Best-effort one-line note to the worker-log endpoint so launch/browser
    diagnostics show up in Railway logs (WORKER-LOG …). No-op off-worker.

    WORKER_LOG_BASE/TOKEN may live only in the worker's .env (the VBS launcher
    starts python with no env vars), so fall back to reading that file."""
    import os
    import urllib.request

    base = (os.environ.get("WORKER_LOG_BASE", "") or "").rstrip("/")
    token = os.environ.get("WORKER_LOG_TOKEN", "") or ""
    if not (base and token):
        try:
            envf = PROJECT_ROOT / ".env"
            if envf.exists():
                for line in envf.read_text(encoding="utf-8", errors="ignore").splitlines():
                    s = line.strip()
                    if s.startswith("#") or "=" not in s:
                        continue
                    k, v = s.split("=", 1)
                    if k.strip() == "WORKER_LOG_BASE":
                        base = base or v.strip().rstrip("/")
                    elif k.strip() == "WORKER_LOG_TOKEN":
                        token = token or v.strip()
        except Exception:
            pass
    if not (base and token):
        return
    try:
        urllib.request.urlopen(
            urllib.request.Request(
                f"{base}/api/portal-automation/worker/log/{token}",
                data=msg.encode("utf-8"), method="POST",
            ),
            timeout=5,
        )
    except Exception:
        pass


# Standard Windows install locations for REAL Google Chrome — checked when the
# `channel="chrome"` lookup misses (e.g. a per-user install the worker's service
# account can't see via the registry). Harel's F5 edge rejects bundled Chromium,
# so finding a real browser matters.
import os as _os

_WIN_CHROME_EXES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    _os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    _os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
]


async def _launch_real_browser(pw, headless: bool, launch_args: list):
    """Launch preferring a REAL browser fingerprint. Order: Chrome channel →
    Chrome .exe (system + per-user) → Edge channel → bundled Chromium (last
    resort). Bundled Chromium is a known dead-end for Harel's F5 (errorcode
    19/22), so Edge (always present on Windows, real fingerprint) is tried first.
    Returns (browser, label)."""
    attempts = [("chrome", dict(channel="chrome"))]
    seen_exe = set()
    for p in _WIN_CHROME_EXES:
        if p and p not in seen_exe and _os.path.exists(p):
            seen_exe.add(p)
            attempts.append(("chrome-exe", dict(executable_path=p)))
    attempts.append(("msedge", dict(channel="msedge")))
    attempts.append(("chromium", dict()))
    last_exc = None
    for label, kw in attempts:
        try:
            browser = await pw.chromium.launch(
                headless=headless, args=launch_args, **kw
            )
            return browser, label
        except Exception as exc:
            last_exc = exc
            continue
    raise last_exc or RuntimeError("no browser could be launched")


async def _launch_real_persistent(pw, profile_dir, headless: bool, launch_args: list, context_kwargs: dict):
    """Persistent-profile twin of `_launch_real_browser` — same real-browser ladder.

    This used to be a bare `channel="chrome"` with a silent `except: → bundled
    Chromium` fallback. On a worker PC without Google Chrome (Edge-only Windows is
    common) EVERY persistent run therefore used bundled Chromium — whose UA-CH brand
    list says "Chromium" — and nothing in any log said so. That is precisely the
    fingerprint reCAPTCHA Enterprise punishes, and Mor/Meitav are the two portals
    gated by it. Try Edge (a real browser, always present on Windows) BEFORE falling
    back to Chromium, and return the label so the caller can log what actually ran.
    Returns (context, label)."""
    attempts = [("chrome", dict(channel="chrome"))]
    seen_exe = set()
    for p in _WIN_CHROME_EXES:
        if p and p not in seen_exe and _os.path.exists(p):
            seen_exe.add(p)
            attempts.append(("chrome-exe", dict(executable_path=p)))
    attempts.append(("msedge", dict(channel="msedge")))
    attempts.append(("chromium", dict()))
    last_exc = None
    for label, kw in attempts:
        try:
            context = await pw.chromium.launch_persistent_context(
                str(profile_dir), headless=headless, args=launch_args,
                **kw, **context_kwargs,
            )
            return context, label
        except Exception as exc:
            last_exc = exc
            continue
    raise last_exc or RuntimeError("no persistent browser could be launched")

OTP_WAIT_TIMEOUT_S = 300   # 5 minutes — the phone forwarder (Doze/battery-opt) often
# batches SMS so codes land at ~250-260s; 240s was clipping them by seconds (e.g. the
# 2026-06-30 batch: meitav's code arrived 17s after a 240s timeout). The real fix is the
# goAsync immediate-forward APK on the phone; this widens the catch window as a safety net.
OTP_POLL_INTERVAL_S = 1.0
# 12 min per run. Must exceed the worst legit run: a cold reCAPTCHA profile's login
# retries (Mor/Meitav reload+warm, ~250s) + the 300s OTP wait + download. No-OTP portals
# still fail fast at the 300s OTP timeout, so this only buys headroom for genuinely-slow
# logins — never hangs longer.
RUN_HARD_TIMEOUT_S = 720

# A HEADED browser needs an interactive desktop. When the worker PC sleeps, locks,
# or its session is disconnected mid-run, Chrome exits a second or two after the
# page loads and Playwright reports "Target page, context or browser has been
# closed" — never a net::ERR_*, which is what a network drop looks like. Observed
# only ever on headed plugins (hachshara, meitav, mor), never a headless one.
# One clean relaunch recovers a transient loss; a genuinely absent desktop still
# fails, loudly, on the second attempt.
BROWSER_DEATH_RETRIES = 1
BROWSER_SETTLE_S = 7

# Files a force-killed / crashed Chromium strands in a persistent profile. The
# NEXT launch exits immediately when it finds one, so a single crash makes every
# later run of that portal fail identically until the lock is cleared by hand.
_PROFILE_SINGLETONS = ("SingletonLock", "SingletonCookie", "SingletonSocket")


def _browser_died(exc: Exception) -> bool:
    """True when the browser PROCESS is gone, as opposed to the network being
    down (net::ERR_*) or a locator timing out. Only this class of failure is
    worth relaunching for."""
    s = str(exc)
    return ("has been closed" in s or "Target closed" in s
            or "Browser closed" in s or "Target page, context or browser" in s)


def _clear_profile_singletons(profile_dir) -> None:
    """Drop stale Singleton* locks before reusing a persistent profile."""
    for name in _PROFILE_SINGLETONS:
        try:
            (profile_dir / name).unlink()
            logger.info("cleared stale %s in %s", name, profile_dir)
        except FileNotFoundError:
            pass
        except OSError as e:
            logger.warning("could not clear %s: %s", name, e)


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


async def _db_utc_now(db: AsyncSession) -> datetime:
    """Return 'now' from the DATABASE clock as naive UTC.

    The OTP window is `otp_inbox.received_at >= otp_since`. `received_at` is
    stamped by the phone-forward webhook running on the SERVER (Railway) with
    `datetime.utcnow()`. `otp_since`, however, is captured in the WORKER process
    — which for most users is their own Windows PC in Israel, whose wall clock
    is NOT guaranteed to be NTP-synced. A worker clock running even a minute
    fast makes `otp_since` land in the future relative to every incoming code,
    so `received_at >= otp_since` discards the real OTP and the run waits the
    full timeout for a code that already arrived (live: kikohib's worker ran
    ~5 min fast → Harel code 019182 arrived +11s but was filtered out).

    Anchoring `otp_since` to the DB clock (same authority as `received_at`)
    removes the worker's local clock from the comparison entirely, so OTP
    matching is correct regardless of the worker machine's time settings.
    """
    return await db.scalar(select(func.timezone("UTC", func.now())))


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
    raise OtpTimeout(
        f"לא התקבל קוד OTP תוך {OTP_WAIT_TIMEOUT_S // 60} דקות. ודאו שהטלפון דולק "
        f"ושאפליקציית Nifraim SMS מעבירה את הקוד, ונסו שוב."
    )


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
    # Give a rejected-login plugin a MEASURED fact instead of a guess: when did
    # THIS SAME credential last succeed? A recent success rules out "wrong
    # פרטים" outright (a stale/typo'd credential doesn't intermittently start
    # working), which matters for score-based gates like Mor's reCAPTCHA
    # Enterprise where the server's own error body is a generic 400 that can't
    # itself distinguish cause. See mor.py::_classify and memory `portal_mor`.
    plugin.cred_last_run_status = cred.last_run_status
    plugin.cred_last_run_at = cred.last_run_at

    password = decrypt(cred.encrypted_password)

    download_dir = DOWNLOAD_ROOT / str(run.id)
    screenshot_path = SCREENSHOT_ROOT / f"{run.id}.png"

    # Lazy import — playwright is heavy and only loaded inside an actual run.
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        # Per-portal anti-bot fingerprint controls (see base.py). Defaults keep
        # every existing portal on the shared headless + UA-override path.
        headed = getattr(plugin, "headed", False)
        native = getattr(plugin, "native_fingerprint", False)
        persist = getattr(plugin, "use_persistent_profile", False)

        # Israeli insurer WAFs geo-block Railway's foreign datacenter IP. Route
        # geo-blocked portals through an IL residential proxy when one is set;
        # otherwise (or for direct-OK portals like Migdal) connect directly.
        # Hoisted above the launch so a persistent context can receive it too.
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

        # `--disable-blink-features=AutomationControlled` is applied to EVERY
        # plugin, native-fingerprint included.
        #
        # It used to be dropped for native plugins, on the theory that the flag
        # "is itself a bot tell to reCAPTCHA Enterprise". That conflated two very
        # different mechanisms:
        #   • THE FLAG tells Chrome not to set `navigator.webdriver` in the first
        #     place. The result is a browser that genuinely reports
        #     webdriver=false — indistinguishable from any normal Chrome,
        #     because there is nothing left over to detect.
        #   • THE JS PATCH below (defineProperty on navigator.webdriver) fakes
        #     the same value after the fact and IS detectable — the property
        #     descriptor and getter.toString() both give it away.
        # Only the second is a tell. Dropping both left Mor and meitav — the two
        # native plugins, and the only two reCAPTCHA-score-gated portals —
        # advertising `navigator.webdriver === true`, the single most heavily
        # weighted automation signal there is.
        #
        # Measured on kikohib's worker 2026-07-20, Mor login rejected:
        #     probe_token_len=1316  webdriver=True
        #     recaptcha_hdr=len1316  req={licenseId=len8, identity=len9, phoneNumber=len10}
        #     -> 400 {"resultCode":"Bad Request"}
        # i.e. Google minted a full token and we sent it; a complete, correctly
        # shaped request was refused. Nothing about the payload was left to fix,
        # which puts the score itself in the frame — and webdriver=true is the
        # one automation signal still being broadcast.
        #
        # Blast radius is exactly mor + meitav: every other plugin is non-native
        # and was already getting this flag.
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            # Containers default to a tiny 64MB /dev/shm; Chrome fills it and the
            # tab/renderer crashes (Railway "Crashed!" during a batch). Write
            # shared memory to /tmp. Container fix; no TLS/JA3 change.
            "--disable-dev-shm-usage",
            "--disable-gpu",
        ]

        # Context kwargs shared by both launch paths. A native-fingerprint plugin
        # lets real Chrome send its own UA + Client-Hints — a pinned UA that
        # disagrees with the engine version sinks the reCAPTCHA Enterprise score
        # (proven against Mor). The override path keeps the Real-Chrome UA + UA-CH
        # brand list that Harel's edge uses to tell real-Chrome from Chromium.
        context_kwargs = dict(
            proxy=context_proxy,
            # The IL residential proxy (Bright Data) terminates TLS with its own
            # CA → ERR_CERT_AUTHORITY_INVALID. Accept it ONLY through the proxy
            # (the `-k` equivalent); direct connections keep full TLS validation.
            ignore_https_errors=bool(context_proxy),
            accept_downloads=True,
            viewport={"width": 1366, "height": 768},
            locale="he-IL",
        )
        if native:
            context_kwargs["extra_http_headers"] = {
                "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
            }
        else:
            context_kwargs["user_agent"] = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            )
            context_kwargs["extra_http_headers"] = {
                "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
                "sec-ch-ua": '"Google Chrome";v="124", "Chromium";v="124", "Not-A.Brand";v="99"',
                "sec-ch-ua-platform": '"Windows"',
                "sec-ch-ua-mobile": "?0",
            }

        # Prefer real Google Chrome over bundled Chromium — its TLS/JA3
        # fingerprint matches a real browser (Harel's edge bounces Chromium to
        # F5 APM errorcode=19/22). Falls back to chromium when chrome is absent.
        browser = None
        if persist:
            # A real on-disk profile (one dir per portal_kind) so reCAPTCHA
            # Enterprise cookies/reputation survive across runs. launch_persistent_context
            # IS the context (no separate browser object).
            profile_dir = BROWSER_PROFILE_ROOT / cred.portal_kind
            # Is this profile UNPROVEN with the portal? A profile with no Google
            # cookies and no site reputation is what reCAPTCHA Enterprise scores
            # hardest, and the plugin can warm it before its one submit (a rejected
            # submit lowers the score, so warming must happen BEFORE the first one,
            # never as a retry).
            #
            # "Warm" is defined as A RUN HAS SUCCEEDED on this profile — not as "the
            # directory exists". A failed first attempt creates the directory, so
            # existence would declare the profile warm precisely when it is at its
            # coldest, and the second attempt would skip the warm-up and fail the
            # same way.
            warm_marker = profile_dir / WARM_MARKER
            profile_was_cold = not warm_marker.exists()
            profile_dir.mkdir(parents=True, exist_ok=True)
            # A crashed Chrome strands SingletonLock here; without this, every
            # subsequent run of this portal dies on arrival, forever.
            _clear_profile_singletons(profile_dir)
            context, _blabel = await _launch_real_persistent(
                pw, profile_dir, not headed, launch_args, context_kwargs
            )
            plugin.profile_was_cold = profile_was_cold
            logger.info(
                "Run %s (%s): persistent browser=%s cold_profile=%s",
                run.id, cred.portal_kind, _blabel, profile_was_cold,
            )
            # Surface it to Railway logs. 'chromium' on a reCAPTCHA-gated portal
            # (Mor/Meitav) means the PC has no real Chrome/Edge and the run is
            # fighting the bot score with the worst possible fingerprint — that is
            # a machine-setup fault, not a code fault, and it must be visible.
            _worker_note(
                f"run {str(run.id)[:8]} {cred.portal_kind}: persistent browser={_blabel}"
                f"{' COLD-PROFILE' if profile_was_cold else ''}"
            )
        else:
            browser, _blabel = await _launch_real_browser(
                pw, not headed, launch_args
            )
            logger.info(
                "Run %s (%s): launched browser=%s", run.id, cred.portal_kind, _blabel
            )
            # Surface the real browser choice to Railway logs — a Harel run on
            # bundled 'chromium' will get bounced by F5, so this tells us at a
            # glance whether the worker found real Chrome/Edge.
            _worker_note(
                f"run {str(run.id)[:8]} {cred.portal_kind}: browser={_blabel}"
            )
            context = await browser.new_context(**context_kwargs)

        # Hide `navigator.webdriver` for the override path. Skipped for a native
        # fingerprint — real Chrome already reports a consistent surface and the
        # patch is itself detectable by reCAPTCHA Enterprise.
        if not native:
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
            # Anchor the OTP wait BEFORE login(). Several portals (menora,
            # phoenix_nifraim) SMS the code the instant credentials submit —
            # which happens DURING login(), before it returns (it also waits for
            # the OTP screen to render). Anchoring AFTER login() raced: the SMS
            # often landed in otp_inbox a few seconds before the anchor, so the
            # `received_at >= since` filter discarded it and the run waited the
            # full timeout for a code that had already arrived (live: menora
            # 028997 arrived 6s into the run, never consumed). Capturing here
            # includes the whole login window; cross-company theft is still
            # prevented by per-company SMS-template tagging in _wait_for_otp.
            otp_since = await _db_utc_now(db)
            await plugin.login(page, cred.username, password)

            if plugin.requires_otp:
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
                otp_since2 = (await _db_utc_now(db)) - timedelta(seconds=30)
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
            # A "successful" run can still lose data three silent ways: a
            # best-effort leg failed inside the plugin (partial_errors), a
            # downloaded file failed to ingest, or it ingested with an
            # unrecognized format (category "general" — which the batch merge
            # ignores entirely). Collect all three onto the run so they surface
            # in the activity log / batch summary instead of vanishing (live:
            # batch 93a796ac merged a נפרעים file missing אלטשולר + כלל גמל
            # while every run showed green).
            issues: list[str] = list(getattr(plugin, "partial_errors", None) or [])
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
                    #
                    # Carry the exception TYPE and the failing source line. The
                    # message used to be `str(err)[:120]` only, which for a bare
                    # `invalid literal for int() with base 10: 'NaN'` (live
                    # 2026-07-20, אלטשולר) named neither the file it came from
                    # nor the line — the same text can be raised from a dozen
                    # places. The parser was verified fine against a real copy of
                    # that report (detect_format → altshuler, 134 records), so the
                    # fault is somewhere past parse, and without a frame there is
                    # nothing to look at. One line of traceback turns the next
                    # occurrence from a hunt into a lookup.
                    import traceback as _tb
                    _frames = _tb.extract_tb(ingest_err.__traceback__)
                    _where = ""
                    if _frames:
                        _f = _frames[-1]
                        _where = f" @ {_f.filename.split('/')[-1]}:{_f.lineno} in {_f.name}()"
                    logger.warning(
                        "Ingest failed for %s (run %s): %s", path.name, run.id,
                        _tb.format_exc()[-1500:],
                    )
                    _worker_note(
                        f"run {str(run.id)[:8]} {cred.portal_kind}: INGEST FAIL {path.name} "
                        f"{type(ingest_err).__name__}: {str(ingest_err)[:100]}{_where}"
                    )
                    issues.append(
                        f"{path.name}: הקליטה נכשלה — "
                        f"{type(ingest_err).__name__}: {str(ingest_err)[:100]}{_where}"
                    )
                    continue
                if upload.file_category not in ("production", "commission"):
                    # Downloaded fine, but no parser signature matched (fmt
                    # "unknown" → category "general"). The rows are junk NULLs
                    # and the batch merge skips the category — without this note
                    # the data is simply gone.
                    issues.append(
                        f"{path.name}: הפורמט לא זוהה ({_fmt}) — לא ייכלל בקבצים המאוחדים"
                    )
                    # Ship the file's first raw rows to Railway (WORKER-LOG) —
                    # the file exists only on the worker's disk, and the real
                    # header row is exactly what's needed to add the missing
                    # parser signature without asking the user for the file.
                    try:
                        import io as _io
                        import pandas as _pd
                        _head = _pd.read_excel(
                            _io.BytesIO(content), header=None, nrows=3
                        ).astype(str).values.tolist()
                    except Exception:
                        _head = []
                    _worker_note(
                        f"run {str(run.id)[:8]} {cred.portal_kind}: UNPARSED "
                        f"{path.name} fmt={_fmt} head={_head}"[:1800]
                    )
                if first_upload_id is None:
                    first_upload_id = upload.id
                    first_filename = path.name
                ingested.append((upload.id, upload.file_category, upload.company_source))

            if files and not ingested:
                # Files were downloaded but NONE persisted — that's a failed
                # run, not a quiet success with an empty upload list.
                raise RuntimeError("אף קובץ שהורד לא נקלט: " + " | ".join(issues)[:300])

            run.downloaded_filename = first_filename
            run.upload_id = first_upload_id
            await _set_status(
                db, run, status="success",
                error=("הושלם חלקית: " + " | ".join(issues))[:500] if issues else None,
                finished=True,
            )

            # This profile has now carried a real login through to a download, so it
            # has the cookies/reputation the next run inherits — stop warming it.
            if getattr(plugin, "use_persistent_profile", False):
                try:
                    (BROWSER_PROFILE_ROOT / cred.portal_kind / WARM_MARKER).write_text("ok")
                except Exception as exc:
                    logger.warning("could not mark %s profile warm: %s", cred.portal_kind, exc)

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
            if browser is not None:  # None on the persistent-context path
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

            otp1_since = await _db_utc_now(db)
            await _set_status(db, run, status="awaiting_otp", stage="otp")
            otp1 = await _wait_for_otp(
                db, run, cred.user_id, otp1_since, portal_kind=cred.portal_kind
            )
            await plugin.submit_otp(page, otp1)

            # Step 2: navigate to settings, submit new phone → OTP #2 to OLD phone.
            await _set_status(db, run, status="downloading", stage="phone_update")
            await plugin.change_contact_phone(page, new_phone)

            # Step 3: wait for OTP #2 and confirm.
            otp2_since = await _db_utc_now(db)
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
            if browser is not None:  # None on the persistent-context path
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


async def _run_inner_with_relaunch(db: AsyncSession, run: PortalRun) -> None:
    """Run the portal, relaunching ONCE if the browser process dies during login.

    Gated on `stage == "login"` deliberately. `_wait_for_otp` only runs after
    login() returns, so a death at this stage means no OTP was consumed and no
    file was downloaded — the run is safely repeatable. A death at `otp`,
    `download` or `parse` is NOT retried: it could burn a second OTP (insurers
    like Phoenix issue exactly one per session) or double-ingest a file.
    """
    for attempt in range(BROWSER_DEATH_RETRIES + 1):
        try:
            await _run_inner(db, run)
            return
        except Exception as e:
            exhausted = attempt >= BROWSER_DEATH_RETRIES
            if exhausted or not _browser_died(e) or (run.stage or "") != "login":
                raise
            note = (f"run {str(run.id)[:8]}: browser died during login ({e}) — "
                    f"relaunching once (attempt {attempt + 2})")
            logger.warning(note)
            _worker_note(note)
            await _set_status(db, run, status="running", stage="login")
            await asyncio.sleep(BROWSER_SETTLE_S)


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
            await asyncio.wait_for(_run_inner_with_relaunch(db, run),
                                   timeout=RUN_HARD_TIMEOUT_S)
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
            await _mirror_to_folded(db, cred)
            await db.commit()


async def _mirror_to_folded(db, cred: PortalCredential) -> None:
    """Copy this run's outcome onto the credentials this plugin folds in.

    A folded leg (harel_commissions, clal_nifraim, menora_nifraim, migdal_apm)
    is downloaded on the PARENT's authenticated session, so it never gets a
    PortalRun of its own and nothing ever wrote its `last_run_*`. Its card
    therefore sat at "ממתין" indefinitely — live 2026-07-20,
    `הראל — ריכוז תשלומי עמלות` read as never-run while having delivered 187
    rows / 142 clients, the largest Harel cohort in the merged נפרעים. The UI
    was telling the agent we had not fetched the very data we had.

    Best-effort and never raises: status cosmetics must not turn a successful
    download into a failed run.
    """
    try:
        from app.services.portal_automation.companies import REGISTRY

        folded = getattr(REGISTRY.get(cred.portal_kind), "folds", ()) or ()
        # Never mirror onto ourselves. The folded legs SUBCLASS their parent
        # portal (ClalNifraimPortal(ClalPortal)…), so without this a subclass
        # that forgets to override `folds = ()` inherits the parent's list and
        # self-references. The subclasses do override it — this is the belt.
        folded = tuple(k for k in folded if k != cred.portal_kind)
        if not folded:
            return
        rows = (await db.execute(
            select(PortalCredential).where(
                PortalCredential.user_id == cred.user_id,
                PortalCredential.portal_kind.in_(list(folded)),
            )
        )).scalars().all()
        for f in rows:
            f.last_run_at = cred.last_run_at
            f.last_run_status = cred.last_run_status
            f.last_error = cred.last_error
    except Exception as e:  # noqa: BLE001 — cosmetics must never fail a run
        logger.warning("could not mirror status to folded credentials: %s", e)
