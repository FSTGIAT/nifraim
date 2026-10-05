"""One recorded agent↔customer conversation (the "שיחות" tab).

The audio itself never lives here — it is on calls-gateway's volume. This row is the
agent-scoped record of the pipeline: status, the ivrit.ai transcript and the Claude
summary/insights. See app/services/calls/ and docs/ARCHITECTURE.md §18.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# uploaded → queued → transcribing → summarizing → done | failed
CALL_STATUSES = ("uploaded", "queued", "transcribing", "summarizing", "done", "failed")
CALL_TERMINAL = ("done", "failed")


class CallRecording(Base):
    __tablename__ = "call_recordings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="uploaded")
    error: Mapped[str | None] = mapped_column(String(300), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    audio_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    transcript_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    segments: Mapped[list | None] = mapped_column(JSONB, nullable=True)       # [{start,end,text}]
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    insights: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    stt_model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(60), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    transcribed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    done_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # where the audio came from: widget (browser) | phone_android | phone_ios
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="widget", server_default="widget")
    phone_number: Mapped[str | None] = mapped_column(String(30), nullable=True)   # normalised 0XXXXXXXXX
    direction: Mapped[str | None] = mapped_column(String(8), nullable=True)       # in | out
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    id_number: Mapped[str | None] = mapped_column(String(20), nullable=True)      # customer matched by phone
    source_ref: Mapped[str | None] = mapped_column(String(80), nullable=True)     # device file id — dedupes re-uploads
    category: Mapped[str | None] = mapped_column(String(24), nullable=True)       # services/calls/categories.py
