"""Nifra Insights state — reminders already spoken, and the cached theme clustering.

reminder_claims: one row per (user, key) the moment a reminder fires. Insert-or-nothing is
the dedupe across tabs, devices and (next version) the Android app — the first claimer
speaks, everyone else stays quiet. Keys: task:<call>:<i>:<date>T<time> · brief:<YYYY-MM-DD>.

calls_insights_cache: one row per user — Claude's grouping of the calls' free-text
products/topics into themes + the analyst narrative, valid while `fingerprint` matches.
See services/calls/insights_board.py.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ReminderClaim(Base):
    __tablename__ = "reminder_claims"
    __table_args__ = (Index("ix_reminder_claims_user_key", "user_id", "key", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    claimed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CallsInsightsCache(Base):
    __tablename__ = "calls_insights_cache"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    themes: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    narrative: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str | None] = mapped_column(String(60), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
