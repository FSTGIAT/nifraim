"""(Re)build semantic-search passages for finished calls — after changing CALLS_EMBED_MODEL,
or once after deploying calls_04.

    cd backend && python scripts/reindex_calls.py [--user EMAIL] [--missing-only]
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, text  # noqa: E402

from app.database import async_session  # noqa: E402
from app.models.call_recording import CallRecording  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.calls.embeddings import index_call, model_name  # noqa: E402


async def main(email: str | None, missing_only: bool) -> None:
    async with async_session() as db:
        q = select(CallRecording).where(CallRecording.status == "done")
        if email:
            q = q.where(CallRecording.user_id == (await db.execute(select(User.id).where(User.email == email))).scalar_one())
        rows = (await db.execute(q.order_by(CallRecording.created_at))).scalars().all()
        if missing_only:
            have = {r[0] for r in (await db.execute(text("SELECT DISTINCT call_id FROM call_chunks WHERE model = :m"), {"m": model_name()}))}
            rows = [c for c in rows if c.id not in have]
        t, n = time.time(), 0
        for c in rows:
            n += await index_call(db, c)
        print(f"{len(rows)} calls → {n} passages with {model_name()} in {time.time() - t:.1f}s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--user")
    ap.add_argument("--missing-only", action="store_true")
    a = ap.parse_args()
    asyncio.run(main(a.user, a.missing_only))
