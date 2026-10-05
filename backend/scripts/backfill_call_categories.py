"""Give calls summarised before 2026-10-05 a category, topics and task due dates.

Never rewrites a summary or a follow-up (the agent may have sent it) — only fills the new
fields (services/calls/sweep.categorize). The calls sweep does the same automatically every
~2 minutes; this script is for doing it all at once.

    cd backend && python scripts/backfill_call_categories.py [--user EMAIL] [--dry-run]
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.database import async_session  # noqa: E402
from app.models.call_recording import CallRecording  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.calls.sweep import categorize  # noqa: E402


async def main(email: str | None, dry: bool) -> None:
    async with async_session() as db:
        q = select(CallRecording).where(CallRecording.status == "done", CallRecording.category.is_(None),
                                        CallRecording.summary.is_not(None))
        if email:
            uid = (await db.execute(select(User.id).where(User.email == email))).scalar_one()
            q = q.where(CallRecording.user_id == uid)
        rows = (await db.execute(q.order_by(CallRecording.created_at))).scalars().all()
        print(f"{len(rows)} calls to classify")
        for c in rows:
            if dry:
                print(f"  {c.created_at:%d/%m %H:%M} {c.title}")
                continue
            try:
                await categorize(db, c)
            except Exception as e:  # noqa: BLE001
                print(f"  {c.id}: skipped ({e})")
                continue
            await db.commit()
            print(f"  {c.created_at:%d/%m %H:%M} {c.category:12} {c.title}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--user")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    asyncio.run(main(a.user, a.dry_run))
