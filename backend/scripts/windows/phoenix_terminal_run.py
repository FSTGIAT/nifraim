"""Phoenix TERMINAL production — one orchestrator (Windows only).

Chains the already-live-verified pieces into the SAME ingest+aggregate pipeline
as every web portal, so Phoenix terminal production lands in the unified
production file (see memory phoenix_terminal_production + run_all_portals_aggregation):

  1. close stale PowerTerm TERM windows (the "zombie hwnd" bug)
  2. phoenix_browser_win.py  → hands-free Edge login + OTP → opens PowerTerm
  3. phoenix_win_terminal.py export → KERMIT MU_NK_HAYV → C:\\fnxbox
  4. MU→.MBT converter:
       • if env PHOENIX_MU_CONVERTER is set → run it (fully hands-free)
       • else → WATCH the .MBT folder for fresh files (agent runs the converter)
  5. phoenix_terminal.build_phoenix_production_xlsx(.MBT folder) → production xlsx
  6. ingest_file_bytes(make_active=False, company_source_override="הפניקס")
     → records land as production/הפניקס → the batch aggregates them automatically.

Invoked by the local worker for a credential whose portal_kind == "phoenix_terminal":
    python backend/scripts/windows/phoenix_terminal_run.py <run_id>

Env:
  DATABASE_URL, PORTAL_CRED_FERNET_KEY            (as the worker)
  PHOENIX_FNXBOX        default C:\\fnxbox         (MU_NK_HAYV lands here)
  PHOENIX_MBT_DIR       default %USERPROFILE%\\Downloads (.MBT files)
  PHOENIX_MU_CONVERTER  optional command; "{mu}" / "{out}" placeholders substituted
  PHOENIX_BACKEND_BASE  default https://nifraim-production.up.railway.app
  PHOENIX_MBT_WAIT_S    default 600  (how long to watch for .MBT when converting manually)

NOTE: Windows-only (pywin32 + Edge + PowerTerm). Cannot be tested off-Windows —
verify on the agent's machine.
"""
import os
import sys
import time
import glob
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime

_HERE = Path(__file__).resolve()
_BACKEND = _HERE.parents[2]            # …/backend
sys.path.insert(0, str(_BACKEND))

# Reuse the worker's .env loading for secrets
_ROOT = _BACKEND.parent
_envf = _ROOT / ".env"
if _envf.exists():
    for _l in _envf.read_text().splitlines():
        s = _l.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
os.environ.setdefault("DATABASE_URL_SYNC", os.environ.get("DATABASE_URL", "").replace("+asyncpg", ""))

FNXBOX = os.environ.get("PHOENIX_FNXBOX", r"C:\fnxbox")
MBT_DIR = os.environ.get("PHOENIX_MBT_DIR") or str(Path(os.environ.get("USERPROFILE", "")) / "Downloads")
CONVERTER = os.environ.get("PHOENIX_MU_CONVERTER", "").strip()
BASE = os.environ.get("PHOENIX_BACKEND_BASE", "https://nifraim-production.up.railway.app")
MBT_WAIT_S = int(os.environ.get("PHOENIX_MBT_WAIT_S", "600"))
PY = sys.executable
WINDIR = str(_HERE.parent)

MBT_NAMES = ("LIFE.MBT", "COVRLIFE.MBT", "LIFEHLTH.MBT", "COMPANY.MBT", "PERSON.MBT")


def _log(m):
    print(f"[phoenix_terminal_run] {m}", flush=True)


def _close_stale_terminals():
    """Close any pre-existing PowerTerm TERM windows so the export drives the
    FRESH login's terminal, not a zombie (the documented false-success bug)."""
    try:
        import win32gui, win32con
        def cb(hwnd, _):
            t = win32gui.GetWindowText(hwnd) or ""
            if "TERM" in t.upper() and win32gui.IsWindowVisible(hwnd):
                _log(f"closing stale terminal hwnd={hwnd} title={t!r}")
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        win32gui.EnumWindows(cb, None)
        time.sleep(3)
    except Exception as e:
        _log(f"close-stale skipped: {e}")


def _mbt_snapshot():
    out = {}
    for n in MBT_NAMES:
        p = Path(MBT_DIR) / n
        out[n] = (p.stat().st_mtime, p.stat().st_size) if p.exists() else None
    return out


def _run_login(username, password, token):
    _log("step 2: phoenix_browser_win login (hands-free OTP)…")
    r = subprocess.run([PY, str(Path(WINDIR) / "phoenix_browser_win.py"),
                        username, password, token, BASE], timeout=420)
    if r.returncode != 0:
        raise RuntimeError(f"login script exit {r.returncode}")


def _run_export():
    _log("step 3: phoenix_win_terminal export (KERMIT MU_NK_HAYV)…")
    r = subprocess.run([PY, str(Path(WINDIR) / "phoenix_win_terminal.py"), "export"], timeout=420)
    if r.returncode != 0:
        raise RuntimeError(f"export script exit {r.returncode}")


def _newest_mu():
    cands = glob.glob(os.path.join(FNXBOX, "MU_NK_HAYV*"))
    return max(cands, key=os.path.getmtime) if cands else None


def _convert_or_watch(before):
    """Produce fresh .MBT from the MU file. Either run the configured converter,
    or watch the .MBT folder for the agent's manual conversion."""
    if CONVERTER:
        mu = _newest_mu() or ""
        cmd = CONVERTER.replace("{mu}", mu).replace("{out}", MBT_DIR)
        _log(f"step 4: running converter: {cmd}")
        subprocess.run(cmd, shell=True, timeout=300)
    else:
        _log(f"step 4: no PHOENIX_MU_CONVERTER set — watching {MBT_DIR} for fresh .MBT "
             f"(run the converter now; waiting up to {MBT_WAIT_S}s)…")
    deadline = time.time() + (MBT_WAIT_S if not CONVERTER else 60)
    while time.time() < deadline:
        now = _mbt_snapshot()
        fresh = [n for n in MBT_NAMES if now[n] and now[n] != before.get(n)]
        if fresh:
            _log(f"fresh .MBT detected: {fresh}")
            time.sleep(3)   # let the converter finish writing the set
            return True
        time.sleep(5)
    return any(_mbt_snapshot().values())


async def _parse_and_ingest(run_id):
    from sqlalchemy import select
    from app.database import async_session
    from app.models.portal_run import PortalRun
    from app.services.phoenix_terminal import build_phoenix_production_xlsx
    from app.services.upload_ingest import ingest_file_bytes, schedule_post_ingest

    out = Path(FNXBOX) / f"phoenix_production_{datetime.utcnow():%Y%m}.xlsx"
    _log(f"step 5: parsing .MBT set from {MBT_DIR} → {out}")
    build_phoenix_production_xlsx(Path(MBT_DIR), out)
    content = out.read_bytes()

    async with async_session() as db:
        run = (await db.execute(select(PortalRun).where(PortalRun.id == run_id))).scalar_one()
        _log("step 6: ingesting as production/הפניקס (held; aggregates in the batch)")
        upload, fmt = await ingest_file_bytes(
            db, run.user_id, content, out.name,
            make_active=False, company_source_override="הפניקס",
        )
        run.status = "success"
        run.stage = "parse"
        run.downloaded_filename = out.name
        run.upload_id = upload.id
        run.finished_at = datetime.utcnow()
        await db.commit()
        await schedule_post_ingest(db, upload, fmt)
    _log(f"DONE — upload {upload.id} ({fmt})")


async def main():
    import uuid
    from sqlalchemy import select
    from app.database import async_session
    from app.models.portal_run import PortalRun
    from app.models.portal_credential import PortalCredential
    from app.models.user import User
    from app.utils.crypto import decrypt

    run_id = uuid.UUID(sys.argv[1])
    async with async_session() as db:
        run = (await db.execute(select(PortalRun).where(PortalRun.id == run_id))).scalar_one()
        cred = (await db.execute(select(PortalCredential).where(PortalCredential.id == run.credential_id))).scalar_one()
        user = (await db.execute(select(User).where(User.id == run.user_id))).scalar_one()
        username = cred.username
        password = decrypt(cred.encrypted_password)
        token = user.phone_forward_token
    if not token:
        raise RuntimeError("user has no phone_forward_token — OTP cannot be fetched")

    try:
        _close_stale_terminals()
        _run_login(username, password, token)
        before = _mbt_snapshot()
        _run_export()
        if not _convert_or_watch(before):
            raise RuntimeError("no .MBT files produced (converter not run / timed out)")
        await _parse_and_ingest(run_id)
    except Exception as e:
        _log(f"FAILED: {e}")
        from sqlalchemy import select as _sel
        from app.database import async_session as _s
        async with _s() as db:
            run = (await db.execute(_sel(PortalRun).where(PortalRun.id == run_id))).scalar_one()
            run.status = "failed"
            run.error_message = str(e)[:500]
            run.finished_at = datetime.utcnow()
            await db.commit()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
