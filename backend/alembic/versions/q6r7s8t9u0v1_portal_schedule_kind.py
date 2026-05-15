"""replace portal_credentials.schedule_enabled with schedule_kind

Revision ID: q6r7s8t9u0v1
Revises: p5q6r7s8t9u0
Create Date: 2026-05-15 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "q6r7s8t9u0v1"
down_revision: Union[str, Sequence[str], None] = "p5q6r7s8t9u0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the new enum-string column with default 'manual'.
    op.add_column(
        "portal_credentials",
        sa.Column("schedule_kind", sa.String(length=20), nullable=False, server_default="manual"),
    )
    # Backfill: any existing schedule_enabled=true row becomes 'daily'.
    op.execute(
        """
        UPDATE portal_credentials
        SET schedule_kind = CASE WHEN schedule_enabled THEN 'daily' ELSE 'manual' END
        """
    )
    # Replace the old composite index with one keyed on schedule_kind.
    op.drop_index("ix_portal_credentials_schedule", table_name="portal_credentials")
    op.create_index(
        "ix_portal_credentials_schedule",
        "portal_credentials",
        ["schedule_kind", "is_active"],
    )
    op.drop_column("portal_credentials", "schedule_enabled")


def downgrade() -> None:
    op.add_column(
        "portal_credentials",
        sa.Column(
            "schedule_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.execute(
        "UPDATE portal_credentials SET schedule_enabled = (schedule_kind <> 'manual')"
    )
    op.drop_index("ix_portal_credentials_schedule", table_name="portal_credentials")
    op.create_index(
        "ix_portal_credentials_schedule",
        "portal_credentials",
        ["schedule_enabled", "is_active"],
    )
    op.drop_column("portal_credentials", "schedule_kind")
