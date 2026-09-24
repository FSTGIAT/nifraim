"""Per-user daily cap on AI calls + the cost ledger (ai_usage)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.ai_usage import AiUsage


async def calls_today(db: AsyncSession, user_id: uuid.UUID) -> int:
    since = datetime.utcnow() - timedelta(hours=24)
    return (await db.execute(
        select(func.count(AiUsage.id)).where(AiUsage.user_id == user_id, AiUsage.created_at >= since)
    )).scalar_one()


async def under_cap(db: AsyncSession, user_id: uuid.UUID) -> bool:
    return await calls_today(db, user_id) < settings.MAIL_AGENT_DAILY_AI_CALLS


def record(db: AsyncSession, user_id: uuid.UUID, feature: str, model: str, usage) -> None:
    db.add(AiUsage(
        user_id=user_id, feature=feature, model=model,
        input_tokens=getattr(usage, "input_tokens", 0) or 0,
        output_tokens=getattr(usage, "output_tokens", 0) or 0,
    ))
