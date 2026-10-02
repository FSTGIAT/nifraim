"""Nifra Agent latency report — real questions × runs, by lane (cache / fast / agent).

    cd backend && PYTHONPATH=. python scripts/agent_latency.py [email] [runs]

Calls the model for agent-lane questions (costs a few cents). Prints time to first
visible event, total, lane and prompt-cache reads.
"""
import asyncio
import statistics
import sys
import time

from sqlalchemy import select

from app.database import async_session
from app.models.user import User
from app.services.agent import cache
from app.services.agent.loop import run

QUESTIONS = [
    "כמה עמלות לא שולמו לי?", "מי לא שילם לי בהפניקס?", "כמה עמלה קיבלתי החודש?", "כמה צבירה יש לי לפי חברה?",
    "מי הלקוחות הגדולים שלי?", "מי עזב החודש?", "מה שיעור העמלה בהפניקס?", "מה מצב המסלקה?",
    "מה כדאי לי לעשות השבוע?", "תמונת מצב",
    "מה יש ללקוח גיא גורן?", "איזו קרן השתלמות מניות הכי טובה?", "למה מנורה לא שילמה לי?",
]


async def one(email, q, surface="chat"):
    async with async_session() as db:
        u = (await db.execute(select(User).where(User.email == email))).scalar_one()
        t = time.monotonic()
        first = None
        done = {}
        async for ev in run(db, u, q, surface=surface):
            if first is None and "text" in ev:          # first ANSWER text, not the status chip
                first = time.monotonic() - t
            if ev.get("done"):
                done = ev
        return done.get("lane"), first or 0, time.monotonic() - t, done.get("cache_read")


async def main():
    email = sys.argv[1] if len(sys.argv) > 1 else "test@test.com"
    runs = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    rows = []
    for r in range(runs):
        if r == 0:
            cache._store.clear()
        for q in QUESTIONS:
            lane, first, total, cr = await one(email, q)
            rows.append((lane, first, total))
            print(f"run{r} {lane:6} first={first:5.2f}s total={total:5.2f}s cache_read={cr} | {q}")
    print()
    for lane in ("cache", "fast", "agent"):
        ts = [t for l, _, t in rows if l == lane]
        fs = [f for l, f, _ in rows if l == lane]
        if ts:
            ts.sort()
            print(f"{lane:6} n={len(ts):2}  first-text p50={statistics.median(fs):.2f}s  total p50={statistics.median(ts):.2f}s  p95={ts[min(len(ts) - 1, int(len(ts) * .95))]:.2f}s")


asyncio.run(main())
