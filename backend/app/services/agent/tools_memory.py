"""The agent learns THIS agent — per user only, never across users."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select

from app.models.ai_memory import MEMORY_KINDS, AiMemory
from app.services.agent.registry import tool

MAX_PER_USER = 60


@tool("remember", "שמירת עובדה קבועה על הסוכן ועל העבודה שלו כדי לענות טוב יותר בפעם הבאה: העדפה ('מדרג לקוחות לפי פרמיה'), כינוי ('הגדולים' = מעל מיליון), הרגל, עובדה עסקית. לא לשמור נתוני לקוח רגישים.",
      {"kind": {"type": "string", "enum": list(MEMORY_KINDS)}, "text": {"type": "string"}}, ["kind", "text"],
      category="memory", status_he="לומד")
async def remember(ctx, kind: str, text: str):
    text = " ".join((text or "").split())[:300]
    if not text or kind not in MEMORY_KINDS:
        return "לא נשמר."
    n = (await ctx.db.execute(select(func.count()).select_from(AiMemory).where(AiMemory.user_id == ctx.user.id))).scalar_one()
    if n >= MAX_PER_USER:
        oldest = (await ctx.db.execute(select(AiMemory).where(AiMemory.user_id == ctx.user.id)
                                       .order_by(AiMemory.last_used.asc().nullsfirst(), AiMemory.created_at.asc()).limit(1))).scalar_one()
        await ctx.db.delete(oldest)
    dup = (await ctx.db.execute(select(AiMemory).where(AiMemory.user_id == ctx.user.id, AiMemory.text == text))).scalars().first()
    if not dup:
        ctx.db.add(AiMemory(user_id=ctx.user.id, kind=kind, text=text, source="model"))
    await ctx.db.commit()
    # a new preference can change answers (e.g. "הגדולים" by premium) — drop this agent's saved answers
    from app.services.agent.versioning import bump_now
    await bump_now(ctx.user.id, reason="remember")
    return "נשמר."


async def memory_block(db, user_id, limit: int = 15) -> str:
    rows = (await db.execute(select(AiMemory).where(AiMemory.user_id == user_id)
                             .order_by(AiMemory.uses.desc(), AiMemory.created_at.desc()).limit(limit))).scalars().all()
    if not rows:
        return ""
    for r in rows:
        r.uses = (r.uses or 0) + 1
        r.last_used = datetime.utcnow()
    return "מה שלמדת על הסוכן הזה (השתמש בזה):\n" + "\n".join(f"- [{r.kind}] {r.text}" for r in rows)
