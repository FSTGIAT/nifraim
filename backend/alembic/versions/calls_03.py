"""Calls: category (closed list in services/calls/categories.py) for filtering by topic.

Revision ID: calls_03
Revises: calls_02
"""
from alembic import op
import sqlalchemy as sa

revision = "calls_03"
down_revision = "calls_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("call_recordings", sa.Column("category", sa.String(24), nullable=True))
    op.create_index("ix_call_recordings_user_category", "call_recordings", ["user_id", "category"])


def downgrade() -> None:
    op.drop_index("ix_call_recordings_user_category", "call_recordings")
    op.drop_column("call_recordings", "category")
