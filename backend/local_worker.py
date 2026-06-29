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
from datetime import datetime
from pathlib import Path

# When THIS worker process started — a UI update request newer than this means
# "you're running stale code, pull + restart".
_STARTED_AT = datetime.utcnow()
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

from sqlalchemy import select, update
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

USER_EMAIL = os.environ.get("WORKER_USER_EMAIL", "royg@nifraim.com")
POLL_S = float(os.environ.get("WORKER_POLL_SECONDS", "5"))
HEARTBEAT_S = 15
HOSTNAME = socket.gethostname()[:120]


async def _resolve_user_id() -> object:
    async with async_session() as db:
        uid = (await db.execute(select(User.id).where(User.email == USER_EMAIL))).scalar_one_or_none()
    if uid is None:
        raise SystemExit(f"No user with email {USER_EMAIL!r} in the database")
    return uid


async def _beat(uid, current_job: str | None = None, touch_job: bool = False):
    """Upsert the heartbeat row. By default only bumps last_seen (so it can run
    concurrently with a job without clobbering current_job); pass touch_job=True
    to also set current_job."""
    async with async_session() as db:
        values = {"user_id": uid, "last_seen": datetime.utcnow(), "hostname": HOSTNAME}
        set_ = {"last_seen": values["last_seen"], "hostname": HOSTNAME}
        if touch_job:
            values["current_job"] = current_job
            set_["current_job"] = current_job
        stmt = pg_insert(WorkerHeartbeat).values(
            id=__import__("uuid").uuid4(), **values
        ).on_conflict_do_update(index_elements=["user_id"], set_=set_)
        await db.execute(stmt)
        await db.commit()


async def _maybe_self_update(uid):
    """If the website's 'עדכן עובד' button was pressed (update_requested_at newer
    than this process's start), git-pull the deploy branch and re-exec so the new
    code loads — the user never touches git or the machine. NON-FATAL: a failed
    pull still restarts on the existing code."""
    async with async_session() as db:
        row = (await db.execute(
            select(WorkerHeartbeat).where(WorkerHeartbeat.user_id == uid)
        )).scalar_one_or_none()
    req = getattr(row, "update_requested_at", None)
    if not req or req <= _STARTED_AT:
        return
    log.info("UI requested worker update (at %s) — pulling + restarting", req)
    _post_log(f"update requested ({req}) — git pull + re-exec")
    # Clear the flag FIRST so we don't loop after re-exec.
    try:
        async with async_session() as db:
            await db.execute(
                update(WorkerHeartbeat).where(WorkerHeartbeat.user_id == uid)
                .values(update_requested_at=None)
            )
            await db.commit()
    except Exception as e:
        log.warning("could not clear update flag: %s", e)
    # Pull the latest code on whatever branch this checkout tracks (.env / venv /
    # data are gitignored, so reset --hard never touches creds or downloads).
    try:
        branch = subprocess.check_output(
            ["git", "-C", str(_ROOT), "rev-parse", "--abbrev-ref", "HEAD"],
            text=True, timeout=30,
        ).strip()
        if not branch or branch == "HEAD":
            branch = _DEPLOY_BRANCH
            subprocess.run(["git", "-C", str(_ROOT), "checkout", branch], timeout=60)
        subprocess.run(["git", "-C", str(_ROOT), "fetch", "origin"], timeout=120)
        subprocess.run(["git", "-C", str(_ROOT), "reset", "--hard", f"origin/{branch}"], timeout=120)
        log.info("worker code updated to origin/%s — re-executing", branch)
    except Exception as e:
        log.warning("self-update git pull failed (%s) — re-executing on existing code", e)
    _post_log("re-executing worker with updated code")
    # Replace this process image with a fresh one running the pulled code.
    os.execv(_sys.executable, [_sys.executable, str(Path(__file__).resolve())])


async def _heartbeat_loop(uid):
    while True:
        try:
            await _beat(uid)
            await _maybe_self_update(uid)
        except Exception as e:
            log.warning("heartbeat failed: %s", e)
        await asyncio.sleep(HEARTBEAT_S)


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
    KERMIT), not a Playwright plugin — drive it via the orchestrator subprocess."""
    import subprocess, sys
    from pathlib import Path
    script = Path(__file__).resolve().parent / "scripts" / "windows" / "phoenix_terminal_run.py"
    log.info("dispatching phoenix_terminal orchestrator for run %s", rid)
    subprocess.run([sys.executable, str(script), str(rid)], timeout=1800)


async def main():
    uid = await _resolve_user_id()
    log.info("Nifraim worker started — host=%s user=%s poll=%ss", HOSTNAME, USER_EMAIL, POLL_S)
    await _beat(uid, current_job=None, touch_job=True)
    _post_log(f"worker ONLINE — user={USER_EMAIL} poll={POLL_S}s (DB heartbeat ok)")
    asyncio.create_task(_heartbeat_loop(uid))

    while True:
        try:
            bid = await _claim_pending_batch(uid)
            if bid is not None:
                log.info("▶ claimed batch %s — running all portals locally", bid)
                await _beat(uid, current_job=f"מריץ הורדה מכל החברות", touch_job=True)
                await run_batch(bid)
                await _beat(uid, current_job=None, touch_job=True)
                log.info("✔ batch %s done", bid)
                continue

            claimed = await _claim_pending_run(uid)
            if claimed is not None:
                rid, kind = claimed
                log.info("▶ claimed run %s (%s) — running locally", rid, kind)
                await _beat(uid, current_job="מריץ הורדת חברה", touch_job=True)
                if kind == "phoenix_terminal":
                    await _run_phoenix_terminal(rid)
                else:
                    await run_automation(rid)
                await _beat(uid, current_job=None, touch_job=True)
                log.info("✔ run %s done", rid)
                continue
        except Exception:
            log.exception("worker loop error (continuing)")

        await asyncio.sleep(POLL_S)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("worker stopped")
