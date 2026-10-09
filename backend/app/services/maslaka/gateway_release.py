"""What the Maslaka Gateway runs, and how a new version reaches it.

The Gateway (Azure VM with the static IP the מסלקה whitelisted) runs its own copy
of `backend/app` + `maslaka_worker.py`. A Railway deploy does not reach it, and
hand-picked file pushes left it a patchwork (2026-10-09: 49 of 272 files differed,
86 missing). Now:

  deploy (railway up) ─► an admin clicks "שחרר לגייטוויי" (released_version)
       ─► the Gateway, between two ticks, downloads THIS bundle, self-tests it in a
          separate release folder, switches, and rolls back if the new version
          doesn't complete a healthy tick (gateway_updater.py / gateway_launcher.py)

First end-to-end release test in production: 2026-10-10 (this comment is the change).

Mode A (one-click release) was Roy's choice: a human gate stays in front of the
regulator-facing machine, and an unfinished working tree never reaches it alone.
"""
from __future__ import annotations

import hashlib
import hmac
import io
import zipfile
from pathlib import Path

from app.config import settings

BACKEND = Path(__file__).resolve().parents[3]          # …/backend
ENTRY = "backend/maslaka_worker.py"
SELFTEST_SAMPLE = BACKEND / "tests" / "fixtures" / "maslaka" / "swiftness_samples" / \
    "101000514813450CONSLTING009202412051829016502.DAT"


def token_ok(token: str) -> bool:
    want = (settings.GATEWAY_TOKEN or "").strip()
    return bool(want) and hmac.compare_digest(want, (token or "").strip())


def members() -> list[tuple[Path, str]]:
    """(path, arcname) of every file a Gateway release ships — ONE list for the zip
    and its version hash, so the version describes exactly the downloaded bytes.
    The WHOLE app tree, never hand-picked files."""
    out: list[tuple[Path, str]] = []
    app = BACKEND / "app"
    for p in app.rglob("*"):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
            out.append((p, "backend/" + str(p.relative_to(BACKEND)).replace("\\", "/")))
    for rel in ("maslaka_worker.py", "gateway_updater.py", "gateway_launcher.py", "requirements.txt"):
        fp = BACKEND / rel
        if fp.exists():
            out.append((fp, "backend/" + rel))
    if SELFTEST_SAMPLE.exists():   # a real CONSLT file the release parses before it may switch
        out.append((SELFTEST_SAMPLE, "backend/gateway_selftest/sample.DAT"))
    return sorted(out, key=lambda m: m[1])


_VERSION: str | None = None


def version() -> str:
    """Content hash of the release. Deployed files never change inside a process."""
    global _VERSION
    if _VERSION is None:
        h = hashlib.sha256()
        for p, arc in members():
            h.update(arc.encode("utf-8") + b"\0")
            h.update(p.read_bytes())
        _VERSION = h.hexdigest()[:16]
    return _VERSION


def bundle() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p, arc in members():
            z.write(p, arc)
        z.writestr("backend/GATEWAY_VERSION", version() + "\n")
    return buf.getvalue()
