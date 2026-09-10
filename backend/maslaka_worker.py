"""Nifraim MASLAKA GATEWAY WORKER — the outbound leg of the clearinghouse.

Runs ON the Maslaka Gateway VM (Windows Server, Israel Central, static IP
51.58.32.28), NOT on Railway. See `docs/ARCHITECTURE.md` §12 and
`.claude/plans/maslaka-gateway-claim-loop.md`.

Why this process exists
-----------------------
The מסלקה is a file-based vault exchange, and its Transporter agent syncs folders
on THIS machine. Railway cannot reach them. `POST /api/maslaka/inquiry` used to
enqueue the send as a FastAPI BackgroundTask, which runs on the host that served
the request — so the XML landed on a Railway container disk, `transport.send()`
reported success, and the row flipped to `submitted` with the request silently
lost. Invariant #3.

So the cloud now only CREATES rows. This worker claims them and does the transport.

What it does each tick
----------------------
  • claim `pending` inquiries (FOR UPDATE SKIP LOCKED) → build XML → vault OUT
  • every MASLAKA_POLL_INTERVAL_MINUTES: walk vault IN → ingest → archive,
    and expire inquiries past MASLAKA_INQUIRY_TIMEOUT_DAYS

What it deliberately does NOT do
--------------------------------
No heartbeat row, no hostname pinning, no orphan reconciler, no self-update
bundle. `local_worker.py` needs all of that because AGENTS own those machines —
two PCs per login, OTP contention, non-technical users. The Gateway is one box we
administer with `az vm run-command`. Copied from it: the claim-loop shape and the
supervisor restart wrapper.

Config (.env at the repo root next to this file's parent):
  DATABASE_URL              prod async URL (postgresql+asyncpg://…)
  JWT_SECRET                required by Settings
  MASLAKA_ENABLED=true      master switch — the vault is open
  MASLAKA_VAULT_HOST=true   THIS host owns the vault folders
  MASLAKA_ENCRYPTION_KEY    Fernet key for raw payloads
  MASLAKA_AGENT_NUMBER/_ID  our clearinghouse identity
  MASLAKA_LOCAL_{OUTBOX,INBOX,ARCHIVE}   ABSOLUTE paths to the Transporter's folders

Run:  cd backend && python maslaka_worker.py
"""
import asyncio
import logging
import os
import socket
import time as _time
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent          # repo root (/.../test)

# ── .env bootstrap ───────────────────────────────────────────────────────────
# Mirrors local_worker.py: read the file ourselves rather than trusting the
# process env, because a launcher (Scheduled Task / service) starts python with
# almost nothing set. utf-8-sig strips a BOM — a BOM'd first key silently becomes
# unreadable and the worker can never connect.
_env: dict[str, str] = {}
_env_file = _ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8-sig").splitlines():
        _s = _line.strip().lstrip("﻿")
        if _s and not _s.startswith("#") and "=" in _s:
            _k, _v = _s.split("=", 1)
            _env[_k.strip().lstrip("﻿")] = _v.strip().strip('"').strip("'")
for _key in (
    "DATABASE_URL", "JWT_SECRET", "MASLAKA_ENABLED", "MASLAKA_VAULT_HOST",
    "MASLAKA_ENCRYPTION_KEY", "MASLAKA_AGENT_NUMBER", "MASLAKA_AGENT_ID",
    "MASLAKA_TRANSPORT", "MASLAKA_LOCAL_OUTBOX", "MASLAKA_LOCAL_INBOX",
    "MASLAKA_LOCAL_ARCHIVE",
):
    # `not in`, deliberately — NOT `not os.environ.get(...)`. An explicitly
    # empty value is a decision ("this is unset"), and refilling it from the
    # .env file overrides the caller silently. Live: the preflight test set
    # MASLAKA_AGENT_NUMBER="" to prove the worker refuses an unidentified
    # deployment, the file put the real value back, and the worker booted and
    # ran forever instead of exiting.
    if _key not in os.environ and _env.get(_key):
        os.environ[_key] = _env[_key]
os.environ.setdefault("DATABASE_URL_SYNC", os.environ.get("DATABASE_URL", "").replace("+asyncpg", ""))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(_ROOT / "maslaka_worker.log"), encoding="utf-8"),
    ],
)
log = logging.getLogger("maslaka-gateway")

from app.config import settings                                    # noqa: E402
from app.database import async_session                             # noqa: E402
from app.services.maslaka import orchestration                     # noqa: E402
from app.services.maslaka.transport import get_transport           # noqa: E402

HOSTNAME = socket.gethostname()[:120]
CLAIM_POLL_S = float(os.environ.get("MASLAKA_CLAIM_POLL_SECONDS", "10"))


def _preflight() -> None:
    """Refuse to start on a misconfiguration instead of running uselessly.

    Every check here is something that otherwise fails SILENTLY and looks healthy:
    an empty auto-created vault, a poll that scans nothing forever, or a literal
    placeholder shipped to a financial regulator.
    """
    problems: list[str] = []

    if not settings.MASLAKA_VAULT_HOST:
        problems.append(
            "MASLAKA_VAULT_HOST is false. This process is the vault host or it is "
            "nothing — running it on Railway would write outbox XML to a container "
            "disk the Transporter cannot see and report success."
        )
    if not settings.MASLAKA_ENABLED:
        problems.append(
            "MASLAKA_ENABLED is false — the מסלקה has not opened the vaults yet. "
            "Do not start the Gateway worker before the vault is live and the "
            "TODO(XSD) markers are closed (see the maslaka-gateway skill)."
        )
    # Invariant #1: never send an unidentified request. The adapter raises anyway,
    # but that turns every inquiry into a `failed` row; failing here says why once.
    if not (settings.MASLAKA_AGENT_NUMBER and settings.MASLAKA_AGENT_ID):
        problems.append(
            "MASLAKA_AGENT_NUMBER / MASLAKA_AGENT_ID are unset. A regulator's vault "
            "is the wrong place to discover the deployment was never configured."
        )
    # Invariant #4: relative vault paths resolve against the CWD, and
    # LocalVaultTransport.__init__ MKDIRS them — so a worker started from the wrong
    # directory creates a different, empty vault, passes healthcheck(), and
    # exchanges nothing while looking perfectly healthy. This is the one place a
    # hard failure is cheaper than a silent success.
    if (settings.MASLAKA_TRANSPORT or "local").lower() == "local":
        for name in ("MASLAKA_LOCAL_OUTBOX", "MASLAKA_LOCAL_INBOX", "MASLAKA_LOCAL_ARCHIVE"):
            value = getattr(settings, name, "") or ""
            if not Path(value).is_absolute():
                problems.append(
                    f"{name}={value!r} is RELATIVE. It resolves against the current "
                    f"working directory ({Path.cwd()}) and would be auto-created as an "
                    f"empty vault. Point it at the Transporter's folder, absolutely."
                )

    if problems:
        log.error("refusing to start — %d configuration problem(s):", len(problems))
        for i, p in enumerate(problems, 1):
            log.error("  %d. %s", i, p)
        raise SystemExit(2)


# Deliberately `datetime.min`, NOT `utcnow()`: it makes the first tick poll the inbox
# IMMEDIATELY on startup instead of sitting silent for a whole
# MASLAKA_POLL_INTERVAL_MINUTES. After a restart, feedback already sitting in the IN
# folder is picked up at once. Do not "fix" this to utcnow().
_last_poll_at = datetime.min


async def _tick() -> None:
    """One pass: drain the outbound queue, then poll the inbox on its own cadence."""
    global _last_poll_at
    async with async_session() as db:
        n = await orchestration.submit_pending_inquiries(db)
        if n:
            log.info("submitted %d inquiry/inquiries to the vault outbox", n)

    elapsed = (datetime.utcnow() - _last_poll_at).total_seconds()
    if elapsed < settings.MASLAKA_POLL_INTERVAL_MINUTES * 60:
        return
    _last_poll_at = datetime.utcnow()
    async with async_session() as db:
        stats = await orchestration.poll_and_ingest(db, user_id=None)
        expired = await orchestration.expire_stale_inquiries(db)
    if stats["scanned"] or expired:
        log.info(
            "poll: scanned=%d feedback=%d holdings=%d unknown=%d errors=%d expired=%d",
            stats["scanned"], stats["feedback_ingested"], stats["holdings_ingested"],
            stats["unknown"], stats["errors"], expired,
        )


async def main() -> None:
    _preflight()
    transport = get_transport()
    healthy = await transport.healthcheck()
    log.info(
        "Maslaka Gateway worker starting — host=%s transport=%s outbox=%s healthy=%s",
        HOSTNAME, settings.MASLAKA_TRANSPORT, settings.MASLAKA_LOCAL_OUTBOX, healthy,
    )
    if not healthy:
        # Not fatal: the Transporter may not have created its folders yet, and the
        # loop retries. But say it out loud rather than logging a silent zero.
        log.warning("vault healthcheck FAILED — check the Transporter's folders exist")

    while True:
        try:
            await _tick()
        except Exception:
            log.exception("gateway loop error (continuing)")
        await asyncio.sleep(CLAIM_POLL_S)


if __name__ == "__main__":
    # Supervisor, same shape as local_worker.py: nothing else restarts this
    # process, so any escape from main() means the clearinghouse queue silently
    # stops draining. A deliberate SystemExit (bad config) must NOT spin.
    _delay = 5
    while True:
        try:
            asyncio.run(main())
            break
        except KeyboardInterrupt:
            log.info("gateway worker stopped")
            break
        except SystemExit:
            raise
        except Exception:
            log.exception("gateway worker crashed — restarting in %ss", _delay)
            _time.sleep(_delay)
            _delay = min(_delay * 2, 60)
