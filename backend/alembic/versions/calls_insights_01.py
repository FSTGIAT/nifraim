"""Nifra Insights: reminder_claims (spoken-once dedupe) + calls_insights_cache (themes).

Revision ID: calls_insights_01
Revises: customer_history_01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "calls_insights_01"
down_revision = "customer_history_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reminder_claims",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.String(120), nullable=False),
        sa.Column("claimed_at", sa.DateTime),
    )
    op.create_index("ix_reminder_claims_user_key", "reminder_claims", ["user_id", "key"], unique=True)
    op.create_table(
        "calls_insights_cache",
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("themes", JSONB),
        sa.Column("narrative", sa.Text),
        sa.Column("model", sa.String(60)),
        sa.Column("computed_at", sa.DateTime),
    )


def downgrade() -> None:
    op.drop_table("calls_insights_cache")
    op.drop_index("ix_reminder_claims_user_key", table_name="reminder_claims")
    op.drop_table("reminder_claims")
