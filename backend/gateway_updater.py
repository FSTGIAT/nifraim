"""Maslaka Gateway self-update — the Gateway side (run between two ticks of
maslaka_worker.py). The server side is app/api/maslaka_gateway.py.

Layout on the Gateway (GATEWAY_HOME, e.g. C:\\Nifraim\\app):
    .env  venv\\  maslaka_worker.log            never touched by an update
    gateway_launcher.py                          the Scheduled Task runs this
    releases\\<version>\\backend\\...             one folder per release (whole app tree)
    current.txt / previous.txt                   which release runs / runs before it
    probation.json                               a new release on trial
    gateway_event.json                           last update event, for the report

An update happens only when ALL hold:
  * GATEWAY_AUTO_UPDATE is not "false" (local kill switch),
  * the server says released ≠ running and not pinned (server kill switch),
  * the downloaded bundle IS the released version (a newer unreleased deploy is
    never taken — the admin's click is the gate),
  * requirements.txt is unchanged (a pip install stays a deliberate human step —
    the local worker never pips, and that once broke Phoenix with pywin32),
  * the new release unpacks, CRC-checks, compiles, imports and parses a real
    מסלקה sample file in a SEPARATE process with no DB writes and no sends.
Then it writes current.txt + probation.json and asks the launcher to restart
(exit 75). A release that doesn't complete a healthy tick within PROBATION_S, or
crashes twice, is rolled back by the launcher.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

EXIT_SWITCH = 75          # "a new release is staged — start it"
EXIT_PROBATION = 76       # "my trial expired without a healthy tick — roll me back"
PROBATION_S = 600
KEEP_RELEASES = 3

SELFTEST = r"""
import compileall, sys, os
ok = compileall.compile_dir('app', quiet=1)
if not ok:
    sys.exit('compile failed')
from app.services.maslaka import orchestration, adapter, events, transport, delta  # noqa
from app.services import mimshak
from app.services.mimshak import parse_mimshak_dat
data = open(os.path.join('gateway_selftest', 'sample.DAT'), 'rb').read()
recs = parse_mimshak_dat(data, 'sample.DAT').get('records', [])
if not recs:
    sys.exit('sample DAT parsed to 0 records')
print('selftest ok', len(recs))
"""


# ── small file helpers ────────────────────────────────────────────────────
def home() -> Path:
    return Path(os.environ.get("GATEWAY_HOME") or Path(__file__).resolve().parent.parent)


def read(p: Path) -> str | None:
    try:
        return p.read_text(encoding="utf-8").strip() or None
    except FileNotFoundError:
        return None


def write(p: Path, text: str) -> None:
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, p)


def running_version(backend_dir: Path) -> str:
    return read(backend_dir / "GATEWAY_VERSION") or "legacy"


def set_event(h: Path, state: str, detail: str = "") -> None:
    write(h / "gateway_event.json", json.dumps(
        {"state": state, "detail": detail[:3000], "at": datetime.utcnow().isoformat()}, ensure_ascii=False))


def get_event(h: Path) -> dict:
    try:
        return json.loads(read(h / "gateway_event.json") or "{}")
    except ValueError:
        return {}


# ── probation (cleared by the worker's first healthy tick) ────────────────
def start_probation(h: Path, version: str, previous: str) -> None:
    write(h / "probation.json", json.dumps({"version": version, "previous": previous,
                                           "started": time.time(), "crashes": 0}))


def probation(h: Path) -> dict | None:
    try:
        return json.loads(read(h / "probation.json") or "null")
    except ValueError:
        return None


def clear_probation(h: Path) -> bool:
    p = h / "probation.json"
    if p.exists():
        p.unlink()
        set_event(h, "ok", "release passed its trial")
        return True
    return False


def probation_expired(h: Path) -> bool:
    pr = probation(h)
    return bool(pr) and time.time() - pr.get("started", time.time()) > PROBATION_S


# ── network ───────────────────────────────────────────────────────────────
def _get(url: str, timeout: int = 60) -> bytes:
    last = None
    for attempt in range(3):
        try:
            return urllib.request.urlopen(urllib.request.Request(url), timeout=timeout).read()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"download failed: {last}")


def report(base: str, token: str, running: str, state: str, detail: str = "", tick_ok: bool = False) -> None:
    body = json.dumps({"running_version": running, "state": state, "detail": detail[:3900],
                       "tick_ok": tick_ok}).encode()
    req = urllib.request.Request(f"{base}/api/maslaka/gateway/report/{token}", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        urllib.request.urlopen(req, timeout=20).read()
    except Exception:  # noqa: BLE001 — reporting must never stop the worker
        pass


# ── staging ───────────────────────────────────────────────────────────────
def stage(h: Path, zip_bytes: bytes, expect_version: str) -> Path:
    """Unpack a release into releases/<version> after checking it. Raises on any
    problem; the live release is never touched here."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        bad = z.testzip()
        if bad is not None:
            raise RuntimeError(f"corrupt bundle (bad CRC in {bad})")
        names = set(z.namelist())
        for need in ("backend/maslaka_worker.py", "backend/GATEWAY_VERSION", "backend/app/services/maslaka/orchestration.py"):
            if need not in names:
                raise RuntimeError(f"bundle has no {need}")
        got = z.read("backend/GATEWAY_VERSION").decode().strip()
        if got != expect_version:
            raise RuntimeError(f"bundle is {got}, not the released {expect_version} (deployed moved on — release again)")
        rel = h / "releases" / expect_version
        tmp = h / "releases" / (expect_version + ".staging")
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True)
        z.extractall(tmp)
    shutil.rmtree(rel, ignore_errors=True)
    os.replace(tmp, rel)
    return rel


def requirements_changed(old_backend: Path, new_backend: Path) -> bool:
    def digest(p: Path) -> str:
        try:
            return hashlib.sha256(p.read_bytes()).hexdigest()
        except FileNotFoundError:
            return ""
    old, new = digest(old_backend / "requirements.txt"), digest(new_backend / "requirements.txt")
    return bool(old) and old != new


def _home_env(h: Path) -> dict[str, str]:
    """GATEWAY_HOME/.env as a dict — a release folder has no .env of its own."""
    out: dict[str, str] = {}
    try:
        lines = (h / ".env").read_text(encoding="utf-8-sig").splitlines()
    except FileNotFoundError:
        return out
    for line in lines:
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def selftest(new_backend: Path, python: str | None = None, timeout: int = 240) -> tuple[bool, str]:
    env = {**_home_env(home()), **os.environ}     # the process env wins, like the worker
    env["MASLAKA_SELFTEST"] = "1"
    try:
        r = subprocess.run([python or sys.executable, "-c", SELFTEST], cwd=str(new_backend), env=env,
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "selftest timed out"
    out = (r.stdout + r.stderr)[-1500:]
    return r.returncode == 0 and "selftest ok" in r.stdout, out


def prune(h: Path, keep: set[str]) -> None:
    rels = h / "releases"
    if not rels.exists():
        return
    dirs = sorted((d for d in rels.iterdir() if d.is_dir() and not d.name.endswith(".staging")),
                  key=lambda d: d.stat().st_mtime, reverse=True)
    for d in dirs[KEEP_RELEASES:]:
        if d.name not in keep:
            shutil.rmtree(d, ignore_errors=True)


# ── the one entry point the worker calls ──────────────────────────────────
_skip: set[str] = set()      # versions refused this process (needs_pip / failed) — don't re-download every minute


def maybe_update(backend_dir: Path, log=print) -> bool:
    """Returns True when a new release is staged and current.txt points at it —
    the caller must then exit with EXIT_SWITCH. Never raises."""
    h = home()
    base = (os.environ.get("GATEWAY_BASE") or "").rstrip("/")
    token = os.environ.get("GATEWAY_TOKEN") or ""
    if not (base and token) or (os.environ.get("GATEWAY_AUTO_UPDATE", "true").lower() == "false"):
        return False
    running = running_version(backend_dir)
    try:
        info = json.loads(_get(f"{base}/api/maslaka/gateway/version/{token}", timeout=30))
    except Exception as e:  # noqa: BLE001
        log(f"gateway update: version check failed ({e})")
        return False
    released = info.get("released")
    if info.get("pinned") or not released or released == running or released in _skip:
        return False
    log(f"gateway update: {running} → {released}")
    set_event(h, "updating", f"{running} → {released}")
    try:
        new_rel = stage(h, _get(f"{base}/api/maslaka/gateway/bundle/{token}", timeout=300), released)
    except Exception as e:  # noqa: BLE001
        _skip.add(released)
        set_event(h, "update_failed", str(e))
        log(f"gateway update: rejected ({e}) — staying on {running}")
        return False
    new_backend = new_rel / "backend"
    if requirements_changed(backend_dir, new_backend):
        _skip.add(released)
        set_event(h, "needs_pip", f"{released}: requirements.txt changed — install deliberately, then release again")
        log("gateway update: requirements.txt changed — NOT switching (needs a deliberate pip install)")
        return False
    ok, out = selftest(new_backend)
    if not ok:
        _skip.add(released)
        set_event(h, "update_failed", f"selftest failed: {out}")
        log(f"gateway update: selftest FAILED — staying on {running}\n{out}")
        return False
    write(h / "previous.txt", running)
    start_probation(h, released, running)
    write(h / "current.txt", released)
    set_event(h, "updating", f"switching {running} → {released} (selftest ok)")
    prune(h, keep={released, running})
    log(f"gateway update: {released} staged + selftest ok — restarting into it")
    return True
