"""Nifraim LOCAL WORKER — runs the portal automation on the agent's Israeli
machine while Railway stays the UI/DB/brain.

Why: Israeli insurer portals geo-block Railway's foreign IP, and the Bright Data
proxy's no-KYC mode blocks the login POST. A worker running here (real IL IP)
reaches every insurer directly — no proxy, no KYC. See memory
`railway_ip_geoblocked_insurers`.

How it works:
  • The web UI's "download" buttons enqueue jobs (PortalRun / PortalRunBatch =
    "pending"); with WORKER_MODE=true on Railway, Railway does NOT execute them.
  • This worker polls the PROD DB, claims the oldest pending job, and runs it
    locally via the SAME run_automation / run_batch code. Results ingest to prod.
  • OTPs still arrive in prod `otp_inbox` via the phone-forward webhook; this
    worker (pointed at the prod DB) consumes them — fully hands-free.
  • A heartbeat row (worker_heartbeats) lets the site show online/offline.

Config (env, with fallback to the local .env next to this file's repo root):
  DATABASE_URL              prod async URL (postgresql+asyncpg://…railway)
  PORTAL_CRED_FERNET_KEY    to decrypt stored portal passwords
  WORKER_USER_EMAIL         which agent this worker serves (default below)
  WORKER_POLL_SECONDS       job poll interval (default 5)

Run:  python local_worker.py
"""
import os
import socket
import asyncio
import logging
import subprocess
import time as _time
from datetime import datetime
from pathlib import Path

# When THIS worker process started — a UI update request newer than this means
# "you're running stale code, pull + restart".
_STARTED_AT = datetime.utcnow()
# True while a batch/run is actively executing. The heartbeat loop's self-update
# (os.execv re-exec) must NOT fire mid-run — that tears down the live browser and
# fails every in-flight portal. We defer the update until the run finishes.
_BUSY = False
# True only while THIS machine owns the account's heartbeat row. A second PC installed
# for the same login stands by instead of claiming jobs (see _beat / _stand_by).
_OWNS = False
# Deploy branch fallback if the checkout is on a detached HEAD.
_DEPLOY_BRANCH = "claude/automate-otp-login-fCKdi"

# ── Load secrets from the repo-root .env for any field the launching env omits ──
_ROOT = Path(__file__).resolve().parent.parent  # repo root (/.../test)
_env = {}
_env_file = _ROOT / ".env"
if _env_file.exists():
    # utf-8-sig strips a UTF-8 BOM if present. Windows PowerShell 5.1's
    # `Set-Content -Encoding UTF8` writes a BOM, which would corrupt the FIRST
    # key (﻿DATABASE_URL → unreadable → worker can't boot → never connects).
    for _line in _env_file.read_text(encoding="utf-8-sig").splitlines():
        _s = _line.strip().lstrip("﻿")
        if _s and not _s.startswith("#") and "=" in _s:
            _k, _v = _s.split("=", 1)
            _env[_k.strip().lstrip("﻿")] = _v.strip().strip('"').strip("'")

if not os.environ.get("DATABASE_URL") and _env.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = _env["DATABASE_URL"]
# Push JWT_SECRET (required by Settings) into the env so config loads even if
# pydantic mis-reads a BOM'd .env — env vars take precedence over the file.
if not os.environ.get("JWT_SECRET") and _env.get("JWT_SECRET"):
    os.environ["JWT_SECRET"] = _env["JWT_SECRET"]
os.environ.setdefault("DATABASE_URL_SYNC", os.environ.get("DATABASE_URL", "").replace("+asyncpg", ""))
os.environ.setdefault("PORTAL_CRED_FERNET_KEY", _env.get("PORTAL_CRED_FERNET_KEY", ""))
os.environ["IL_RESIDENTIAL_PROXY"] = ""   # direct from this IL machine — no proxy
os.environ["IL_HAREL_PROXY"] = ""

# ── Pin TEMP/TMP to a durable dir owned by the worker ────────────────────────
# When the worker is launched from inside MobaXterm, TEMP points at MobaXterm's
# ephemeral filesystem (…\Temp\Mxt251\mx86_64b\var\log\xwin\…) which gets cleaned
# mid-session. That vanishing dir produced ENOENT crashes — Playwright's
# `BrowserType.launch: mkdtemp …\xwin\playwright-artifacts` (e.g. the yelin run)
# and openpyxl's temp file during the batch-end merge. Force a stable temp root
# next to the worker install so every subprocess (browsers, pandas/openpyxl)
# inherits a path that survives the whole run.
try:
    _TMP = _ROOT / "worker_tmp"
    _TMP.mkdir(parents=True, exist_ok=True)
    for _k in ("TMP", "TEMP", "TMPDIR"):
        os.environ[_k] = str(_TMP)
    import tempfile as _tempfile
    _tempfile.tempdir = str(_TMP)
except Exception:
    pass  # fall back to the inherited TEMP rather than refuse to boot

# ── Remote diagnostics: POST startup + any fatal error to the server so support
# can "follow the log" via `railway logs` even when this worker can't reach the
# DB. Uses ONLY stdlib + the .env token, and is installed BEFORE the app imports
# so an import/config crash is still reported. ───────────────────────────────
import sys as _sys, socket as _sock, traceback as _tb, urllib.request as _ureq
_LOG_BASE = (_env.get("WORKER_LOG_BASE", "") or os.environ.get("WORKER_LOG_BASE", "")).rstrip("/")
_LOG_TOKEN = _env.get("WORKER_LOG_TOKEN", "") or os.environ.get("WORKER_LOG_TOKEN", "")

def _post_log(msg: str) -> None:
    if not (_LOG_BASE and _LOG_TOKEN):
        return
    try:
        data = f"[{_sock.gethostname()}] {msg}".encode("utf-8", "replace")[:4000]
        _ureq.urlopen(_ureq.Request(
            f"{_LOG_BASE}/api/portal-automation/worker/log/{_LOG_TOKEN}",
            data=data, method="POST"), timeout=15)
    except Exception:
        pass

def _excepthook(et, ev, tb):
    _post_log("FATAL: " + "".join(_tb.format_exception(et, ev, tb))[-3500:])
    _sys.__excepthook__(et, ev, tb)

_sys.excepthook = _excepthook
_post_log("worker process starting (importing app…)")

from sqlalchemy import func, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import async_session
from app.models.user import User
from app.models.portal_run import PortalRun
from app.models.portal_run_batch import PortalRunBatch
from app.models.worker_heartbeat import WorkerHeartbeat
from app.services.portal_automation.runner import run_automation
from app.services.portal_automation.batch_runner import run_batch

# Log to BOTH the console and a file (worker.log at repo root) so a hidden
# Scheduled Task still leaves a shareable record of any startup crash.
_LOG_FILE = str(_ROOT / "worker.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(_LOG_FILE, encoding="utf-8")],
)
log = logging.getLogger("nifraim-worker")

# Single-instance guard: bind a fixed localhost port as a lock. If another worker
# already holds it, exit cleanly — prevents two workers double-running jobs.
import socket as _slock
try:
    _SINGLETON = _slock.socket(_slock.AF_INET, _slock.SOCK_STREAM)
    _SINGLETON.bind(("127.0.0.1", 47615))
    _SINGLETON.listen(1)
except OSError:
    log.info("another Nifraim worker is already running — exiting this instance")
    raise SystemExit(0)

# Worker identity — resolved from the installed .env, NEVER hardcoded. The
# installer writes WORKER_LOG_TOKEN (the per-user phone-forward token) and
# WORKER_USER_EMAIL into the .env FILE; the VBS launcher starts python with no
# env vars, so these MUST be read from _env, not os.environ alone. There is no
# default account: a worker that can't say whom it serves refuses to start,
# rather than silently running another user's jobs and writing to their data.
WORKER_TOKEN = (_env.get("WORKER_LOG_TOKEN", "") or os.environ.get("WORKER_LOG_TOKEN", "")).strip()
USER_EMAIL = (_env.get("WORKER_USER_EMAIL", "") or os.environ.get("WORKER_USER_EMAIL", "")).strip()
POLL_S = float(os.environ.get("WORKER_POLL_SECONDS", "5"))
HEARTBEAT_S = 15
HOSTNAME = socket.gethostname()[:120]
# After this long without a beat, the heartbeat's owner is presumed dead and another
# machine may take the row. Must be ≥ the server's WORKER_LIVE_WINDOW_S (90s), or a
# second PC could seize a heartbeat the server still considers online.
OWNER_STALE_S = 90


async def _resolve_user_id() -> object:
    """Resolve exactly which agent this worker serves. Prefer the phone-forward
    token (unique per user, authoritative), then the configured email. No
    fallback to a default account — an unidentifiable worker exits."""
    global USER_EMAIL
    async with async_session() as db:
        row = None
        if WORKER_TOKEN:
            row = (await db.execute(
                select(User.id, User.email).where(User.phone_forward_token == WORKER_TOKEN)
            )).first()
        if row is None and USER_EMAIL:
            row = (await db.execute(
                select(User.id, User.email).where(User.email == USER_EMAIL)
            )).first()
    if row is None:
        msg = "Worker identity unresolved — set WORKER_LOG_TOKEN or WORKER_USER_EMAIL in the worker .env"
        _post_log("FATAL: " + msg)
        raise SystemExit(msg)
    USER_EMAIL = row.email  # accurate logs even when resolved by token
    return row.id


async def _resolve_user_id_resilient() -> object:
    """Resolve identity, retrying THROUGH transient network failures.

    A DNS hiccup or an unreachable DB must never be fatal here. Nothing supervises
    this process — the installer launches it once from the Startup folder — so an
    exit is unrecoverable: the agent is silently offline until their next logon, and
    the worker can't even report why (its log channel needs DNS too). This shipped:
    a `socket.gaierror` on the DB host during a self-update re-exec left an agent
    disconnected with no diagnostics.

    Only an IDENTITY failure (the user genuinely isn't in the DB) refuses to start —
    that's a config error, and retrying it forever would spin.
    """
    delay = 5
    attempt = 0
    while True:
        attempt += 1
        try:
            uid = await _resolve_user_id()
            if attempt > 1:
                log.info("DB reachable again after %d attempts — starting", attempt)
                _post_log(f"recovered: DB reachable after {attempt} attempts — worker starting")
            return uid
        except SystemExit:
            raise                       # identity unresolved — config, not a blip
        except Exception as e:
            # Report the first failure and then only occasionally, so a long outage
            # doesn't flood the log channel (which may itself be down).
            if attempt == 1 or attempt % 10 == 0:
                _post_log(f"startup: DB unreachable ({type(e).__name__}: {e}) — retrying, attempt {attempt}")
            log.warning("startup: DB unreachable (%s: %s) — retry in %ss", type(e).__name__, e, delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)


async def _beat(uid, current_job: str | None = None, touch_job: bool = False) -> bool:
    """Upsert the heartbeat row, but ONLY if this machine owns it.

    Returns True if we hold the heartbeat, False if a DIFFERENT machine is live on
    this account (we are a rival and must stand by — see _stand_by).

    `worker_heartbeats` is UNIQUE on user_id: one row per USER, not per machine. So
    an agent who installed the worker on two PCs had both of them upserting the same
    row, and `hostname` simply flipped to whoever beat last (live: LAPTOP-1SS1D8M8 ↔
    DESKTOP-M443DUC). That is not cosmetic — both machines then poll and CAS-claim
    jobs, so a run can land on the PC that has no PowerTerm client or isn't elevated,
    and the "עדכן עובד" flag is consumed (and CLEARED) by whichever worker sees it
    first, leaving the other permanently on stale code.

    The guard is the ON CONFLICT ... WHERE clause, so ownership is decided atomically
    by Postgres rather than by a read-then-write race between two machines:
    take the row if it is already ours, or if its owner has gone stale (dead/off).
    """
    async with async_session() as db:
        # Stamp last_seen with the DATABASE clock, not this PC's — the server's
        # online/orphan checks compare it against DB-side utcnow, and a worker
        # machine with a fast clock (live: +5 min) looked "online" minutes after
        # being powered off, delaying stuck-batch recovery. Same clock-authority
        # principle as the OTP `otp_since` fix.
        now_sql = func.timezone("UTC", func.now())
        values = {"user_id": uid, "last_seen": now_sql, "hostname": HOSTNAME}
        set_ = {"last_seen": now_sql, "hostname": HOSTNAME}
        if touch_job:
            values["current_job"] = current_job
            set_["current_job"] = current_job
        mine_or_dead = or_(
            WorkerHeartbeat.hostname == HOSTNAME,
            WorkerHeartbeat.hostname.is_(None),
            WorkerHeartbeat.last_seen < now_sql - text(f"interval '{OWNER_STALE_S} seconds'"),
        )
        stmt = (
            pg_insert(WorkerHeartbeat)
            .values(id=__import__("uuid").uuid4(), **values)
            .on_conflict_do_update(index_elements=["user_id"], set_=set_, where=mine_or_dead)
            .returning(WorkerHeartbeat.hostname)
        )
        owned = (await db.execute(stmt)).first() is not None
        await db.commit()
        return owned


async def _approved_hostname(uid) -> str | None:
    """The machine this account is PINNED to, or None when unpinned."""
    try:
        async with async_session() as db:
            return (await db.execute(
                select(WorkerHeartbeat.approved_hostname).where(WorkerHeartbeat.user_id == uid)
            )).scalar_one_or_none()
    except Exception:
        return None


async def _park_wrong_machine(uid, approved: str) -> None:
    """This PC is not the account's approved machine — do nothing, forever.

    Never beat (that would claim the heartbeat row and make the site show THIS
    machine as the agent's worker) and never claim a job. An unpinned account is
    unaffected; only a pinned one refuses strangers. Keep re-checking so the pin can
    be moved from the UI without touching this PC.
    """
    said = False
    while True:
        if not said:
            log.error("this machine (%s) is not the approved worker for this account "
                      "(approved: %s) — refusing to run", HOSTNAME, approved)
            _post_log(
                f"REFUSING TO RUN: '{HOSTNAME}' is not this account's approved worker "
                f"('{approved}'). This PC holds someone else's token — uninstall the "
                f"worker here, or change the approved machine."
            )
            said = True
        await asyncio.sleep(60)
        current = await _approved_hostname(uid)
        if not current or current == HOSTNAME:
            _post_log(f"approved machine is now '{current or 'any'}' — resuming on {HOSTNAME}")
            return


async def _rival_hostname(uid) -> str:
    """Who currently holds this account's heartbeat (when it isn't us)."""
    try:
        async with async_session() as db:
            return (await db.execute(
                select(WorkerHeartbeat.hostname).where(WorkerHeartbeat.user_id == uid)
            )).scalar_one_or_none() or "?"
    except Exception:
        return "?"


async def _stand_by(uid) -> None:
    """Another machine is live on this account. Wait — do NOT beat and do NOT claim.

    Beating would steal the row back and start a flip-flop; claiming would let two
    machines run the same agent's portals at once (double downloads, and one stealing
    the other's OTP out of the shared inbox). We simply idle until the incumbent goes
    stale (powered off / crashed), then take over on the next beat.
    """
    rival = await _rival_hostname(uid)
    log.warning("another worker (%s) is live for this account — standing by", rival)
    _post_log(f"STANDBY: worker '{rival}' is already live for this account; "
              f"'{HOSTNAME}' will not claim jobs while it is up. "
              f"Two machines are installed for one login — uninstall the one you don't use.")
    while True:
        await asyncio.sleep(30)
        if await _beat(uid):                       # incumbent went stale → we own it now
            log.info("previous worker went offline — taking over")
            _post_log(f"took over from '{rival}' (it went offline) — {HOSTNAME} is now the worker")
            return


def _download_and_extract_bundle() -> bool:
    """RE-DOWNLOAD the worker code bundle from the server and extract it over the
    repo root — the SAME delivery the installer used (the worker is a downloaded
    bundle, NOT a git checkout). The zip is prefixed with `backend/`, so extracting
    at _ROOT lands files exactly where they belong. Returns True on success.
    .env / venv / data are NOT in the bundle, so creds & downloads are untouched."""
    base = (_env.get("WORKER_LOG_BASE", "") or os.environ.get("WORKER_LOG_BASE", "")).rstrip("/")
    token = _env.get("WORKER_LOG_TOKEN", "") or os.environ.get("WORKER_LOG_TOKEN", "")
    if not (base and token):
        log.warning("no WORKER_LOG_BASE/TOKEN — cannot download bundle")
        return False
    import io as _io, zipfile as _zip
    url = f"{base}/api/portal-automation/worker/bundle/{token}"
    data = _ureq.urlopen(_ureq.Request(url), timeout=180).read()
    with _zip.ZipFile(_io.BytesIO(data)) as z:
        z.extractall(str(_ROOT))
    log.info("worker bundle (%d bytes) extracted to %s", len(data), _ROOT)
    return True


async def _maybe_self_update(uid):
    """If the website's 'עדכן עובד' button was pressed (update_requested_at newer
    than this process's start), RE-DOWNLOAD the code bundle from the server (same
    way the installer delivers it — no git) and re-exec so the new code loads. The
    user never touches git or the machine. NON-FATAL: a failed download still
    restarts on the existing code."""
    async with async_session() as db:
        row = (await db.execute(
            select(WorkerHeartbeat).where(WorkerHeartbeat.user_id == uid)
        )).scalar_one_or_none()
    req = getattr(row, "update_requested_at", None)
    if not req:
        return

    async def _clear():
        try:
            async with async_session() as db:
                await db.execute(
                    update(WorkerHeartbeat).where(WorkerHeartbeat.user_id == uid)
                    .values(update_requested_at=None)
                )
                await db.commit()
        except Exception as e:
            log.warning("could not clear update flag: %s", e)

    if req <= _STARTED_AT:
        # Stale request (predates this process — we already restarted/updated since).
        # Clear it so the UI's "מתעדכן…"/update_pending doesn't stick forever.
        await _clear()
        return
    if _BUSY:
        # A batch/run is in progress. Re-exec now would close the live browser and
        # fail every in-flight portal (the exact bug that nuked a user's batch).
        # Leave the flag set (UI keeps showing "מתעדכן…" = queued) and apply it on
        # the next heartbeat after the run finishes.
        log.info("update requested but a run is in progress — deferring self-update until it finishes")
        _post_log("update requested — deferred until the current run finishes")
        return
    log.info("UI requested worker update (at %s) — downloading bundle + restarting", req)
    _post_log(f"update requested ({req}) — downloading bundle + re-exec")
    await _clear()  # clear FIRST so we don't loop after re-exec.
    try:
        _download_and_extract_bundle()
    except Exception as e:
        log.warning("bundle self-update failed (%s) — re-executing on existing code", e)
    _post_log("re-executing worker with updated code")
    # Replace this process image with a fresh one running the freshly-downloaded code.
    os.execv(_sys.executable, [_sys.executable, str(Path(__file__).resolve())])


async def _heartbeat_loop(uid):
    global _OWNS
    while True:
        try:
            # Re-check the pin every beat: setting it from the server must stop a
            # wrong machine that is ALREADY running, without anyone touching that PC.
            approved = await _approved_hostname(uid)
            if approved and approved != HOSTNAME:
                _OWNS = False
                await _park_wrong_machine(uid, approved)
            _OWNS = await _beat(uid)
            if _OWNS:
                # Only the OWNING worker self-updates: _maybe_self_update CLEARS the
                # update flag, so letting a standby machine consume it would leave the
                # machine that actually runs the jobs on stale code — silently.
                await _maybe_self_update(uid)
            else:
                await _stand_by(uid)                # blocks until the incumbent dies
                _OWNS = True
        except Exception as e:
            log.warning("heartbeat failed: %s", e)
        await asyncio.sleep(HEARTBEAT_S)


async def _reconcile_orphans(uid):
    """On startup, NO batch/run can legitimately be executing yet — this worker is
    the sole executor for the user and hasn't claimed anything. So any batch/run
    left non-terminal by a PREVIOUS worker that died/re-exec'd/crashed mid-run is an
    orphan. Fail them now so they don't block new downloads forever
    ("הורדה אוטומטית כבר פעילה") and don't show a phantom "running" in the UI."""
    msg = "הופסק עקב הפעלה מחדש של העובד"
    now = datetime.utcnow()
    try:
        async with async_session() as db:
            # A run that already produced an upload SUCCEEDED — its subprocess did the
            # work and simply hadn't stamped the row before we re-exec'd. Reaping it as
            # "failed" reports a lie about data that is sitting in the DB. Live: the
            # Phoenix terminal downloaded + ingested 261 production records, then the
            # agent's deferred "עדכן עובד" restarted the worker and this reaper marked
            # the run failed. Close it out as the success it was.
            await db.execute(
                update(PortalRun)
                .where(PortalRun.user_id == uid,
                       PortalRun.upload_id.is_not(None),
                       PortalRun.status.in_(["pending", "running", "awaiting_otp",
                                             "downloading", "parsing"]))
                .values(status="success", stage="parse", finished_at=now)
            )
            await db.execute(
                update(PortalRun)
                .where(PortalRun.user_id == uid,
                       PortalRun.upload_id.is_(None),
                       PortalRun.status.in_(["pending", "running", "awaiting_otp",
                                             "downloading", "parsing"]))
                .values(status="failed", error_message=msg, finished_at=now)
            )
            res = await db.execute(
                update(PortalRunBatch)
                .where(PortalRunBatch.user_id == uid,
                       PortalRunBatch.status.in_(["pending", "running"]))
                .values(status="failed", error_message=msg, finished_at=now,
                        current_run_id=None)
                .returning(PortalRunBatch.id)
            )
            n = len(res.fetchall())
            await db.commit()
        if n:
            log.info("reconciled %d orphaned batch(es)/runs on startup", n)
            _post_log(f"startup: cleared {n} orphaned batch(es) from a prior worker")
    except Exception as e:
        log.warning("orphan reconciliation failed (non-fatal): %s", e)


async def _claim_pending_batch(uid):
    """Atomically claim the oldest pending batch for this user. Returns its id or None."""
    async with async_session() as db:
        bid = (await db.execute(
            select(PortalRunBatch.id)
            .where(PortalRunBatch.user_id == uid, PortalRunBatch.status == "pending")
            .order_by(PortalRunBatch.started_at).limit(1)
        )).scalar_one_or_none()
        if bid is None:
            return None
        res = await db.execute(
            update(PortalRunBatch)
            .where(PortalRunBatch.id == bid, PortalRunBatch.status == "pending")
            .values(status="running").returning(PortalRunBatch.id)
        )
        await db.commit()
        return res.scalar_one_or_none()


async def _claim_pending_run(uid):
    """Atomically claim the oldest pending STANDALONE run (not a batch child).
    Returns (run_id, portal_kind) or None."""
    from app.models.portal_credential import PortalCredential
    async with async_session() as db:
        row = (await db.execute(
            select(PortalRun.id, PortalCredential.portal_kind)
            .join(PortalCredential, PortalCredential.id == PortalRun.credential_id)
            .where(PortalRun.user_id == uid, PortalRun.status == "pending",
                   PortalRun.batch_id.is_(None))
            .order_by(PortalRun.started_at).limit(1)
        )).first()
        if row is None:
            return None
        rid, kind = row
        res = await db.execute(
            update(PortalRun)
            .where(PortalRun.id == rid, PortalRun.status == "pending")
            .values(status="running").returning(PortalRun.id)
        )
        await db.commit()
        return (res.scalar_one_or_none(), kind)


async def _run_phoenix_terminal(rid):
    """Phoenix terminal production is a Windows-native flow (Edge + PowerTerm +
    KERMIT), not a Playwright plugin — drive it via the orchestrator subprocess.

    Runs in a THREAD: `subprocess.run` blocks, and this coroutine shares the event
    loop with `_heartbeat_loop`. Blocking it froze the heartbeat for the whole run
    (minutes), so the site showed the worker OFFLINE mid-download and the server's
    orphan reaper — fired by the agent's own UI polling after 3 min — failed the
    batch out from under a run that was working fine.
    """
    import subprocess, sys
    from pathlib import Path
    script = Path(__file__).resolve().parent / "scripts" / "windows" / "phoenix_terminal_run.py"
    log.info("dispatching phoenix_terminal orchestrator for run %s", rid)
    # utf-8 stdout regardless of how we're launched: under the hidden VBS launcher
    # (or any pipe) Windows would otherwise encode stdout as cp1255 and a single '→'
    # would abort the run with UnicodeEncodeError.
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    await asyncio.get_running_loop().run_in_executor(
        None, lambda: subprocess.run([sys.executable, str(script), str(rid)],
                                     timeout=1800, env=env)
    )


async def main():
    global _BUSY, _OWNS
    uid = await _resolve_user_id_resilient()
    log.info("Nifraim worker started — host=%s user=%s poll=%ss", HOSTNAME, USER_EMAIL, POLL_S)

    # Announce a MACHINE FLIP. One login, two installed PCs — whichever is powered on
    # silently takes the batch, and they are NOT interchangeable: Phoenix's green
    # terminal needs the PowerTerm client, so a run that works on one machine dies on
    # the other for reasons no log ever mentioned. Live: kiko's runs alternated between
    # DESKTOP-M443DUC (works) and LAPTOP-1SS1D8M8 (no PowerTerm → terminal never opens)
    # and it read as flaky automation. Name it, loudly, at startup.
    # Is this account pinned to a specific machine? If so and it isn't us, stand down
    # BEFORE beating or claiming anything — a wrong machine must not even appear as
    # the agent's worker in the UI.
    approved = await _approved_hostname(uid)
    if approved and approved != HOSTNAME:
        await _park_wrong_machine(uid, approved)

    try:
        previous = await _rival_hostname(uid)
        if previous not in ("?", HOSTNAME):
            log.warning("worker machine changed: %s → %s", previous, HOSTNAME)
            _post_log(
                f"MACHINE CHANGED: this account's worker last ran on '{previous}', now "
                f"'{HOSTNAME}'. Two PCs are installed for one login — they are not "
                f"equivalent (Phoenix's terminal only works where PowerTerm is installed)."
            )
    except Exception:
        pass

    try:
        _OWNS = await _beat(uid, current_job=None, touch_job=True)
        if _OWNS:
            _post_log(f"worker ONLINE — user={USER_EMAIL} host={HOSTNAME} poll={POLL_S}s (DB heartbeat ok)")
        else:
            await _stand_by(uid)                   # a second PC on this login — wait our turn
            _OWNS = True
    except Exception as e:
        # The heartbeat loop retries forever; a blip on the FIRST beat must not
        # take the process down before that loop even starts.
        log.warning("first heartbeat failed (%s) — the heartbeat loop will retry", e)
    # Clear any batch/run a prior worker left mid-flight (crash/re-exec) so it can't
    # block new downloads or show a phantom "running".
    await _reconcile_orphans(uid)
    asyncio.create_task(_heartbeat_loop(uid))

    while True:
        try:
            if not _OWNS:
                # Another machine owns this account right now — never claim alongside
                # it, or both PCs run the same agent's portals and fight over the OTP.
                await asyncio.sleep(POLL_S)
                continue
            bid = await _claim_pending_batch(uid)
            if bid is not None:
                log.info("▶ claimed batch %s — running all portals locally", bid)
                await _beat(uid, current_job=f"מריץ הורדה מכל החברות", touch_job=True)
                _BUSY = True
                try:
                    await run_batch(bid)
                finally:
                    _BUSY = False
                await _beat(uid, current_job=None, touch_job=True)
                log.info("✔ batch %s done", bid)
                continue

            claimed = await _claim_pending_run(uid)
            if claimed is not None:
                rid, kind = claimed
                log.info("▶ claimed run %s (%s) — running locally", rid, kind)
                await _beat(uid, current_job="מריץ הורדת חברה", touch_job=True)
                _BUSY = True
                try:
                    if kind == "phoenix_terminal":
                        await _run_phoenix_terminal(rid)
                    else:
                        await run_automation(rid)
                finally:
                    _BUSY = False
                await _beat(uid, current_job=None, touch_job=True)
                log.info("✔ run %s done", rid)
                continue
        except Exception:
            log.exception("worker loop error (continuing)")

        await asyncio.sleep(POLL_S)


if __name__ == "__main__":
    # Supervisor. NOTHING else restarts this process — the installer launches it
    # once from the Startup folder (NifraimWorker.vbs), so any escape from main()
    # means the agent is silently offline until their next logon. Restart on every
    # unexpected error; only a deliberate SystemExit (identity unresolved, or another
    # worker already holds the singleton port) is allowed to end the process.
    _restart_delay = 5
    while True:
        try:
            asyncio.run(main())
            break                                   # main() returned — nothing to do
        except KeyboardInterrupt:
            log.info("worker stopped")
            break
        except SystemExit:
            raise                                   # config error — do not spin on it
        except Exception as e:
            log.exception("worker crashed — restarting in %ss", _restart_delay)
            _post_log(f"crashed ({type(e).__name__}: {e}) — restarting in {_restart_delay}s")
            _time.sleep(_restart_delay)
            _restart_delay = min(_restart_delay * 2, 60)
