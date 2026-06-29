"""Upsert the Altshuler portal credential for royg in PROD.

Usage:
  DATABASE_URL="postgresql+asyncpg://…prod…" backend/venv/bin/python backend/upsert_altshuler_cred.py
"""
import os, asyncio
from pathlib import Path

_env = {}
for _l in (Path(__file__).resolve().parent.parent / ".env").read_text().splitlines():
    s = _l.strip()
    if s and not s.startswith("#") and "=" in s:
        k, v = s.split("=", 1); _env[k.strip()] = v.strip().strip('"').strip("'")
os.environ.setdefault("PORTAL_CRED_FERNET_KEY", _env.get("PORTAL_CRED_FERNET_KEY", ""))

from sqlalchemy import select
from app.database import async_session
from app.models.user import User
from app.models.portal_credential import PortalCredential
from app.utils.crypto import encrypt

EMAIL = os.environ.get("WORKER_USER_EMAIL", "royg@nifraim.com")
LICENSE = "125514"      # username = מס רישיון
ID_NUM = "40336281"     # password = מס זהות (plugin zero-pads to 9 → 040336281)


async def main():
    async with async_session() as db:
        uid = (await db.execute(select(User.id).where(User.email == EMAIL))).scalar_one_or_none()
        if not uid:
            print("NO USER", EMAIL); return
        cred = (await db.execute(select(PortalCredential).where(
            PortalCredential.user_id == uid,
            PortalCredential.portal_kind == "altshuler"))).scalar_one_or_none()
        enc = encrypt(ID_NUM)
        if cred:
            cred.username = LICENSE
            cred.encrypted_password = enc
            cred.is_active = True
            cred.otp_method = "manual"
            print("UPDATED cred", cred.id)
        else:
            cred = PortalCredential(
                user_id=uid, portal_kind="altshuler",
                username=LICENSE, encrypted_password=enc,
                otp_method="manual", is_active=True, schedule_kind="manual",
            )
            db.add(cred)
            print("CREATED cred for", EMAIL)
        await db.commit()
        print("OK: license(username)=", LICENSE, " id(password set, len)=", len(ID_NUM))


asyncio.run(main())
