"""Create (or reset) a ready-to-use LOCAL user — past the subscription gate.

`POST /api/auth/register` alone leaves `is_active=False`, so the new user is bounced
to /subscription-expired. This script creates the user the way the app would
(`hash_password`, `generate_unique_username`) and flips `is_active=True`, so the
account lands straight in the workspace.

Idempotent: if the email already exists, its password is reset and it is activated.

Run it:

    cd backend && source venv/bin/activate
    python scripts/create_user.py ban1@gmail.com 1234
    python scripts/create_user.py kiko@x.com secret --name "קיקו" --admin

Refuses to touch a non-localhost DATABASE_URL unless --allow-remote is passed —
the root .env points at the local docker DB, but a shell may have prod exported.
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

import app.models  # noqa: E402,F401  — register every mapper before querying User
from app.config import settings  # noqa: E402
from app.database import async_session  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.auth_service import hash_password, verify_password  # noqa: E402
from app.services.username_service import generate_unique_username  # noqa: E402

LOCAL_HOSTS = ("@localhost", "@127.0.0.1", "@db:")


async def main(args: argparse.Namespace) -> None:
    if not any(h in settings.DATABASE_URL for h in LOCAL_HOSTS) and not args.allow_remote:
        host = settings.DATABASE_URL.split("@")[-1]
        sys.exit(f"Refusing: DATABASE_URL is not local ({host}). Pass --allow-remote to override.")

    email = args.email.strip().lower()
    async with async_session() as db:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        created = user is None
        if created:
            user = User(email=email, username=await generate_unique_username(db, email))
            db.add(user)
        user.hashed_password = hash_password(args.password)
        user.is_active = True
        if args.name:
            user.full_name = args.name
        if args.admin:
            user.is_admin = True
        await db.commit()
        await db.refresh(user)

        assert verify_password(args.password, user.hashed_password)
        print(f"{'created' if created else 'updated'}: {user.email}  username={user.username}  "
              f"id={user.id}  is_active={user.is_active}  is_admin={user.is_admin}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("email")
    p.add_argument("password")
    p.add_argument("--name", help="full_name")
    p.add_argument("--admin", action="store_true", help="also set is_admin")
    p.add_argument("--allow-remote", action="store_true", help="allow a non-localhost DATABASE_URL")
    asyncio.run(main(p.parse_args()))
