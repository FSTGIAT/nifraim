"""Inject a manual OTP into PROD otp_inbox for royg (Altshuler e2e test).

Usage:
  DATABASE_URL="postgresql+asyncpg://…prod…" backend/venv/bin/python backend/inject_otp.py <CODE>
"""
import os, sys, asyncio
from datetime import datetime
from sqlalchemy import select
from app.database import async_session
from app.models.user import User
from app.models.otp_inbox import OtpInbox

EMAIL = os.environ.get("WORKER_USER_EMAIL", "royg@nifraim.com")
CODE = sys.argv[1] if len(sys.argv) > 1 else None


async def main():
    if not CODE:
        print("usage: inject_otp.py <CODE>"); return
    async with async_session() as db:
        uid = (await db.execute(select(User.id).where(User.email == EMAIL))).scalar_one()
        row = OtpInbox(
            user_id=uid, from_number="manual", to_number="manual",
            body=f"Altshuler test OTP {CODE}", otp_code=CODE,
            portal_kind="altshuler", received_at=datetime.utcnow(),
        )
        db.add(row); await db.commit()
        print("INJECTED OTP", CODE, "for", EMAIL, "at", datetime.utcnow().isoformat())


asyncio.run(main())
