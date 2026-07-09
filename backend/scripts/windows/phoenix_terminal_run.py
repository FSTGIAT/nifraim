"""Phoenix TERMINAL production — one orchestrator (Windows only).

Chains the already-live-verified pieces into the SAME ingest+aggregate pipeline
as every web portal, so Phoenix terminal production lands in the unified
production file (see memory phoenix_terminal_production + run_all_portals_aggregation):

  1. close stale PowerTerm TERM windows (the "zombie hwnd" bug)
  2. phoenix_browser_win.py  → hands-free Edge login + OTP → opens PowerTerm
  3. phoenix_win_terminal.py export → KERMIT MU_NK_HAYV → C:\\fnxbox
  4. phoenix_mu.build_phoenix_mu_production_xlsx(MU file) → production xlsx
     (parses the MU file DIRECTLY — no external MU→.MBT converter / manual step)
  5. ingest_file_bytes(make_active=False, company_source_override="הפניקס")
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
import re
import sys
import json
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

def _wsl(p: str) -> str:
    """Translate a Windows path (C:\\foo) to its WSL mount (/mnt/c/foo) when THIS
    orchestrator runs on Linux/WSL (its own file reads). No-op on native Windows.
    The GUI subprocesses always use their own internal Windows defaults, so we
    never feed a /mnt path back to them."""
    if sys.platform == "win32" or not p:
        return p
    m = re.match(r"^([A-Za-z]):[\\/](.*)$", p)
    if m:
        return f"/mnt/{m.group(1).lower()}/{m.group(2).replace(chr(92), '/')}"
    return p


def _detect_win_py() -> str:
    """The GUI steps (Edge login + PowerTerm export) MUST run on WINDOWS Python
    (pywin32 + native Edge launch the PowerTerm client; a WSL/Linux browser only
    offers a download). On a native Windows worker install one venv has both the
    app/DB deps AND pywin32, so WIN_PY == PY. On the IL WSL box they are two
    different interpreters: this orchestrator runs on the WSL venv (app/DB) and
    shells the GUI out to the Windows interpreter."""
    env = os.environ.get("PHOENIX_WIN_PYTHON", "").strip()
    if env:
        return env
    if sys.platform != "win32":
        for c in ("/mnt/c/Python313/python.exe", "/mnt/c/Python312/python.exe",
                  "/mnt/c/Python311/python.exe"):
            if Path(c).exists():
                return c
    return sys.executable


def _default_mbt_dir() -> str:
    """Downloads dir where the .MBT set lands — DERIVED, never a hardcoded user.
    Native Windows: %USERPROFILE%\\Downloads. WSL: the real Windows user's
    Downloads under /mnt/c/Users (skip Public/Default/All Users), so it works for
    ANY agent's box, not one named account. Override with PHOENIX_MBT_DIR."""
    if sys.platform == "win32":
        return str(Path(os.environ.get("USERPROFILE", "")) / "Downloads")
    users = Path("/mnt/c/Users")
    skip = {"public", "default", "default user", "all users", "defaultuser0"}
    if users.exists():
        cands = [d for d in users.iterdir()
                 if d.is_dir() and d.name.lower() not in skip and (d / "Downloads").exists()]
        # Prefer the most-recently-used profile (the logged-in agent).
        cands.sort(key=lambda d: d.stat().st_mtime, reverse=True)
        if cands:
            return str(cands[0] / "Downloads")
    return "/mnt/c/Users/Public/Downloads"


_DEF_MBT = _default_mbt_dir()
FNXBOX = _wsl(os.environ.get("PHOENIX_FNXBOX", r"C:\fnxbox"))
MBT_DIR = _wsl(os.environ.get("PHOENIX_MBT_DIR") or _DEF_MBT)
CONVERTER = os.environ.get("PHOENIX_MU_CONVERTER", "").strip()
BASE = os.environ.get("PHOENIX_BACKEND_BASE", "https://nifraim-production.up.railway.app")
MBT_WAIT_S = int(os.environ.get("PHOENIX_MBT_WAIT_S", "600"))
PY = sys.executable
WIN_PY = _detect_win_py()
WINDIR = str(_HERE.parent)

MBT_NAMES = ("LIFE.MBT", "COVRLIFE.MBT", "LIFEHLTH.MBT", "COMPANY.MBT", "PERSON.MBT")


_WORKER_TOKEN = ""  # set in main() once the credential's token is known


def _log(m):
    print(f"[phoenix_terminal_run] {m}", flush=True)


def _post_log(msg: str) -> None:
    """Best-effort POST to the backend worker-log so phoenix_terminal progress /
    failures show up in Railway (WORKER-LOG …) exactly like the Playwright
    plugins. batch_runner runs this orchestrator as a subprocess WITHOUT
    capturing its stdout, so print() alone is invisible server-side — the black
    box that made 'login script exit 1' undiagnosable."""
    if not _WORKER_TOKEN:
        return
    try:
        import urllib.request
        body = f"phoenix_terminal: {msg}"[:3500].encode("utf-8")
        req = urllib.request.Request(
            f"{BASE}/api/portal-automation/worker/log/{_WORKER_TOKEN}",
            data=body, method="POST",
        )
        urllib.request.urlopen(req, timeout=6)
    except Exception:
        pass


def _tail(text: str, n: int = 900) -> str:
    """Last n chars of captured child output, blank-line-trimmed — the part that
    actually names the failure (a '!!' marker or a traceback)."""
    t = (text or "").strip()
    return t[-n:] if len(t) > n else t


# Every child's full stdout, kept so the failure handler can recover the
# screenshot path and the step trail. Previously we stored only the child's
# single '!!' line — a 123-character error_message that named the failing step
# but never the cause, which is what left phoenix_terminal undiagnosable.
_CHILD_OUT: dict = {}


def _last_screenshot() -> str:
    """Path of the failure screenshot the child reported, if any. The child
    prints '>> saved failure capture: <path>.png  (url=…)' from _shot()."""
    for out in reversed(list(_CHILD_OUT.values())):
        for line in reversed((out or "").splitlines()):
            m = re.search(r"saved failure capture:\s*(\S+\.png)", line)
            if m:
                return m.group(1)
    return ""


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


def _run_child(label: str, argv: list, timeout: int) -> None:
    """Run a GUI sub-step on WINDOWS Python (WIN_PY), CAPTURING its output so a
    failure names itself instead of a bare 'exit N'. cwd=WINDIR so the relative
    script resolves over the \\wsl.localhost UNC cwd the Windows interpreter
    inherits when launched from WSL. On non-zero (or timeout) the child's output
    tail is raised AND posted to WORKER-LOG."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    # Leave PHOENIX_DEBUG_DIR unset unless the operator set it — the child then
    # drops failure screenshots into the Windows user's Downloads (findable),
    # not this bundle folder.
    try:
        r = subprocess.run(
            [WIN_PY, *argv], cwd=WINDIR, timeout=timeout, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired as e:
        raw = (e.output or "") if isinstance(e.output, str) else ""
        _CHILD_OUT[label] = raw
        out = _tail(raw)
        _log(f"{label} TIMEOUT after {timeout}s. tail:\n{out}")
        _post_log(f"{label} TIMEOUT {timeout}s :: {out[-500:]}")
        raise RuntimeError(f"{label} timed out after {timeout}s: {out[-300:] or 'no output'}")
    _CHILD_OUT[label] = r.stdout or ""
    tail = _tail(r.stdout or "")
    # Surface the child's progress/failure markers to the worker log regardless.
    _log(f"{label} exit={r.returncode}. tail:\n{tail}")
    _post_log(f"{label} exit={r.returncode} :: {tail[-600:]}")
    if r.returncode != 0:
        # The child's own '!!' diagnosis names the STEP; the tail carries the
        # traceback that names the CAUSE. Keep both — one line alone is what made
        # the last eight failures unreadable.
        markers = [ln for ln in (r.stdout or "").splitlines() if ln.strip().startswith("!!")]
        why = markers[-1].strip() if markers else ""
        detail = _tail(r.stdout or "", 1500)
        raise RuntimeError(
            f"{label} exit {r.returncode}: {why or 'no !! marker'}\n--- child output tail ---\n"
            f"{detail or 'no output'}"
        )


def _run_login(username, password, token):
    _log(f"step 2: phoenix_browser_win login (hands-free OTP) [py={WIN_PY}]…")
    _run_child("login", ["phoenix_browser_win.py", username, password, token, BASE], 420)


def _run_export():
    _log(f"step 3: phoenix_win_terminal export (KERMIT MU_NK_HAYV) [py={WIN_PY}]…")
    _run_child("export", ["phoenix_win_terminal.py", "export"], 420)


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


def _period_from_mu(mu_name: str) -> str:
    """MU_NK_HAYV_MOSHE_2026_06 → '06-2026' (MM-YYYY) so detect_period_month
    (filename-first) resolves the right reporting month."""
    m = re.search(r"(\d{4})[_-](\d{2})", mu_name or "")
    return f"{m.group(2)}-{m.group(1)}" if m else f"{datetime.utcnow():%m-%Y}"


async def _parse_and_ingest(run_id):
    from sqlalchemy import select
    from app.database import async_session
    from app.models.portal_run import PortalRun
    from app.services.phoenix_mu import build_phoenix_mu_production_xlsx
    from app.services.upload_ingest import ingest_file_bytes, schedule_post_ingest

    mu = _newest_mu()
    if not mu:
        raise RuntimeError(f"no MU_NK_HAYV file found in {FNXBOX}")
    period = _period_from_mu(os.path.basename(mu))
    out = Path(FNXBOX) / f"הפניקס פרודוקציה {period}.xlsx"
    _log(f"step 5: parsing MU file {os.path.basename(mu)} → {out.name}")
    build_phoenix_mu_production_xlsx(Path(mu), out)
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
        # schedule_post_ingest is SYNC and takes (user_id, upload_id, category) —
        # NOT awaited and NOT (db, upload, fmt). Awaiting its None return was the
        # "object NoneType can't be used in 'await' expression" failure.
        try:
            schedule_post_ingest(run.user_id, upload.id, upload.file_category)
        except Exception as e:
            _log(f"post-ingest dispatch warning (non-fatal): {e}")
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

    global _WORKER_TOKEN
    _WORKER_TOKEN = token
    _post_log(f"start run {str(run_id)[:8]} user={getattr(user, 'email', '?')} win_py={WIN_PY}")

    try:
        _close_stale_terminals()
        _run_login(username, password, token)
        _run_export()
        # MU_NK_HAYV is parsed DIRECTLY by app.services.phoenix_mu — no external
        # MU→.MBT converter / manual step anymore (see _parse_and_ingest).
        await _parse_and_ingest(run_id)
    except Exception as e:
        _log(f"FAILED: {e}")
        _post_log(f"FAILED: {str(e)[:600]}")
        shot = _last_screenshot()
        if shot:
            _log(f"failure screenshot: {shot}")
            _post_log(f"screenshot: {shot}")
        from sqlalchemy import select as _sel
        from app.database import async_session as _s
        async with _s() as db:
            run = (await db.execute(_sel(PortalRun).where(PortalRun.id == run_id))).scalar_one()
            run.status = "failed"
            # error_message is TEXT — keep the child's traceback, not just its
            # first line. The old [:500] truncation discarded every cause.
            run.error_message = str(e)[:4000]
            if shot:
                run.screenshot_path = shot[:255]
            run.finished_at = datetime.utcnow()
            await db.commit()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
