"""Run the portal batch LOCALLY (this Israeli residential machine) against the
PROD database. Playwright executes here → reaches every insurer directly (no
geo-block, no proxy). OTPs arrive in PROD otp_inbox via the phone-forward webhook
(phone → prod), and this runner (pointed at the prod DB) consumes them. Results
ingest into prod. No secrets hardcoded — DATABASE_URL is passed via the env.
"""
import os
from pathlib import Path

# Required Settings fields not supplied by the launching env come from local .env
_env = {}
for _line in Path("/home/roygi/test/.env").read_text().splitlines():
    _s = _line.strip()
    if _s and not _s.startswith("#") and "=" in _s:
        _k, _v = _s.split("=", 1)
        _env[_k.strip()] = _v.strip().strip('"').strip("'")
os.environ.setdefault("DATABASE_URL_SYNC", os.environ.get("DATABASE_URL", "").replace("+asyncpg", ""))
os.environ.setdefault("PORTAL_CRED_FERNET_KEY", _env.get("PORTAL_CRED_FERNET_KEY", ""))
os.environ.setdefault("IL_RESIDENTIAL_PROXY", "")  # direct from this IL machine

import asyncio
from datetime import datetime
from sqlalchemy import select
from app.database import async_session
from app.models.portal_run_batch import PortalRunBatch
from app.models.user import User
from app.services.portal_automation.batch_runner import run_batch


async def main():
    async with async_session() as db:
        uid = (await db.execute(select(User.id).where(User.email == "royg@nifraim.com"))).scalar_one()
        b = PortalRunBatch(user_id=uid, status="pending", started_at=datetime.utcnow())
        db.add(b)
        await db.commit()
        await db.refresh(b)
        print("BATCH_ID", b.id, flush=True)
    await run_batch(b.id)
    print("BATCH_DONE", flush=True)


asyncio.run(main())
