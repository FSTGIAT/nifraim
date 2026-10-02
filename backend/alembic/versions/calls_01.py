"""Calls plane: call_recordings (recorded conversations → ivrit.ai transcript → Claude summary).

Revision ID: calls_01
Revises: ai_agent_01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "calls_01"
down_revision = "ai_agent_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "call_recordings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="uploaded"),
        sa.Column("error", sa.String(300), nullable=True),
        sa.Column("mime_type", sa.String(60), nullable=True),
        sa.Column("audio_bytes", sa.Integer, nullable=True),
        sa.Column("duration_s", sa.Float, nullable=True),
        sa.Column("title", sa.String(120), nullable=True),
        sa.Column("transcript_text", sa.Text, nullable=True),
        sa.Column("segments", JSONB, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("insights", JSONB, nullable=True),
        sa.Column("stt_model", sa.String(80), nullable=True),
        sa.Column("llm_model", sa.String(60), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("transcribed_at", sa.DateTime, nullable=True),
        sa.Column("done_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_call_recordings_user_id", "call_recordings", ["user_id"])
    op.create_index("ix_call_recordings_created_at", "call_recordings", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_call_recordings_created_at", table_name="call_recordings")
    op.drop_index("ix_call_recordings_user_id", table_name="call_recordings")
    op.drop_table("call_recordings")
