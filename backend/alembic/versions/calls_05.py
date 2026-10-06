"""Calls: never-upload numbers (blocked_phones). Personal calls reuse category='personal'.

Revision ID: calls_05
Revises: walkin_01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "calls_05"
down_revision = "walkin_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "blocked_phones",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phone_key", sa.String(12), nullable=False),
        sa.Column("label", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_blocked_phones_user_key", "blocked_phones", ["user_id", "phone_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_blocked_phones_user_key", table_name="blocked_phones")
    op.drop_table("blocked_phones")
