"""Maslaka Gateway launcher — what the Scheduled Task runs (the stable outer loop).

    python -u C:\\Nifraim\\app\\gateway_launcher.py      (cwd C:\\Nifraim\\app)

It starts maslaka_worker.py from the release current.txt names (or the legacy
`backend\\` tree when there is no current.txt yet), with GATEWAY_HOME pointing
back here so .env and the log stay where they always were. It never imports the
app, so a broken release can never break the launcher.

Exit codes from the worker:
  75 (EXIT_SWITCH)      a new release is staged → start it right away
  76 (EXIT_PROBATION)   the new release's trial expired without a healthy tick
  anything else         a crash → restart with backoff; a release on trial that
                        crashes twice is rolled back
Rollback = current.txt ← previous.txt, probation.json removed, and the event
recorded in gateway_event.json (the next worker run reports it to Railway).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HOME = Path(__file__).resolve().parent
EXIT_SWITCH, EXIT_PROBATION = 75, 76
MAX_TRIAL_CRASHES = 2


def _read(p: Path) -> str | None:
    try:
        return p.read_text(encoding="utf-8").strip() or None
    except FileNotFoundError:
        return None


def _write(p: Path, text: str) -> None:
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, p)


def _event(state: str, detail: str) -> None:
    _write(HOME / "gateway_event.json", json.dumps(
        {"state": state, "detail": detail, "at": datetime.utcnow().isoformat()}, ensure_ascii=False))


def _log(msg: str) -> None:
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} LAUNCHER {msg}"
    print(line, flush=True)
    try:
        with open(HOME / "maslaka_worker.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def backend_dir(home: Path = HOME) -> Path:
    cur = _read(home / "current.txt")
    if cur and cur != "legacy":
        d = home / "releases" / cur / "backend"
        if (d / "maslaka_worker.py").exists():
            return d
        _log(f"release {cur} missing on disk — falling back to the legacy tree")
    return home / "backend"


def rollback(home: Path = HOME, why: str = "") -> str | None:
    """current.txt ← previous.txt. Returns the version rolled back to."""
    prev = _read(home / "previous.txt")
    bad = _read(home / "current.txt")
    if not prev or prev == bad:
        return None
    _write(home / "current.txt", prev)
    (home / "probation.json").unlink(missing_ok=True)
    _event("rolled_back", f"{bad} → {prev}: {why}")
    _log(f"ROLLED BACK {bad} → {prev} ({why})")
    return prev


def on_exit(code: int, home: Path = HOME) -> float:
    """Decide what happens after the worker exits; returns the delay before the next start."""
    if code == EXIT_SWITCH:
        _log(f"switching to release {_read(home / 'current.txt')}")
        return 0
    if code == EXIT_PROBATION:
        rollback(home, "no healthy tick within the trial period")
        return 0
    pr_path = home / "probation.json"
    if pr_path.exists():
        try:
            pr = json.loads(pr_path.read_text(encoding="utf-8"))
        except ValueError:
            pr = {}
        pr["crashes"] = int(pr.get("crashes", 0)) + 1
        if pr["crashes"] >= MAX_TRIAL_CRASHES:
            rollback(home, f"crashed {pr['crashes']}× during its trial (exit {code})")
            return 0
        _write(pr_path, json.dumps(pr))
    return 10 if code != 2 else 60     # 2 = refused to start (bad config): don't spin


def main() -> None:
    delay = 0
    while True:
        if delay:
            time.sleep(delay)
        d = backend_dir()
        env = dict(os.environ, GATEWAY_HOME=str(HOME), PYTHONUNBUFFERED="1")
        _log(f"starting worker from {d}")
        code = subprocess.run([sys.executable, "-u", "maslaka_worker.py"], cwd=str(d), env=env).returncode
        _log(f"worker exited with {code}")
        delay = on_exit(code)


if __name__ == "__main__":
    main()
