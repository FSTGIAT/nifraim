"""What Nifra Agent has learned about ONE agent — never shared across users.

Written by the `remember` tool (the model decides a fact is worth keeping) and
by the router's intent log (which questions this agent asks, so the cache can
be warmed for them). Injected as a short block after the cached system prompt.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

MEMORY_KINDS = ("preference", "fact", "alias", "habit")


class AiMemory(Base):
    __tablename__ = "ai_memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)          # MEMORY_KINDS
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(16), default="model")      # model | agent
    uses: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AiIntentLog(Base):
    """One row per question the agent asked: which lane answered it and how fast.
    Drives cache warm-up (each agent's top intents) and the latency report."""
    __tablename__ = "ai_intent_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    intent: Mapped[str | None] = mapped_column(String(48), nullable=True)   # NULL = agent lane
    lane: Mapped[str] = mapped_column(String(8), nullable=False)            # cache | fast | agent
    ms: Mapped[int] = mapped_column(Integer, default=0)
    question: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
