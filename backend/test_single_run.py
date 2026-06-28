"""Run ONE portal credential locally against prod DB (immune to reloads).
Usage: WORKER_USER_EMAIL=… DATABASE_URL=… python backend/test_single_run.py <portal_kind>
"""
import os, sys, asyncio
from pathlib import Path
_env={}
for _l in (Path(__file__).resolve().parent.parent/".env").read_text().splitlines():
    s=_l.strip()
    if s and not s.startswith("#") and "=" in s:
        k,v=s.split("=",1); _env[k.strip()]=v.strip().strip('"').strip("'")
os.environ.setdefault("DATABASE_URL_SYNC", os.environ.get("DATABASE_URL","").replace("+asyncpg",""))
os.environ.setdefault("PORTAL_CRED_FERNET_KEY", _env.get("PORTAL_CRED_FERNET_KEY",""))
os.environ["IL_RESIDENTIAL_PROXY"]=""; os.environ["IL_HAREL_PROXY"]=""
from datetime import datetime
from sqlalchemy import select
from app.database import async_session
from app.models.user import User
from app.models.portal_credential import PortalCredential
from app.models.portal_run import PortalRun
from app.services.portal_automation.runner import run_automation

KIND=sys.argv[1] if len(sys.argv)>1 else "menora"
EMAIL=os.environ.get("WORKER_USER_EMAIL","royg@nifraim.com")

async def main():
    async with async_session() as db:
        uid=(await db.execute(select(User.id).where(User.email==EMAIL))).scalar_one()
        cred=(await db.execute(select(PortalCredential).where(PortalCredential.user_id==uid, PortalCredential.portal_kind==KIND))).scalar_one()
        run=PortalRun(user_id=uid, credential_id=cred.id, status="pending", started_at=datetime.utcnow())
        db.add(run); await db.commit(); await db.refresh(run)
        print("RUN_ID",run.id,"KIND",KIND,flush=True)
    await run_automation(run.id)
    async with async_session() as db:
        r=(await db.execute(select(PortalRun).where(PortalRun.id==run.id))).scalar_one()
        print("RESULT", r.status, r.stage, (r.error_message or "")[:80], r.downloaded_filename, flush=True)

asyncio.run(main())
