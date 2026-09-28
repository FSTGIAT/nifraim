"""Monthly cycle: portal_run_batches.trigger/cycle_period + cycle_notifications

Revision ID: cycle_01
Revises: portal_setup_01
Create Date: 2026-09-28

Additive. Existing batches were all user-pressed → trigger defaults to 'admin'
for them (server_default), so none of them count as a cycle batch.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "cycle_01"
down_revision: Union[str, Sequence[str], None] = "portal_setup_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column("portal_run_batches", sa.Column("trigger", sa.String(10), nullable=False, server_default="admin"))
    op.add_column("portal_run_batches", sa.Column("cycle_period", sa.Date, nullable=True))
    op.create_index(
        "uq_portal_run_batches_user_cycle",
        "portal_run_batches",
        ["user_id", "cycle_period"],
        unique=True,
        postgresql_where=sa.text("trigger = 'cycle'"),
    )
    op.create_table(
        "cycle_notifications",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("period", sa.Date, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("emailed_at", sa.DateTime, nullable=True),
        sa.Column("seen_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("user_id", "kind", "period", name="uq_cycle_notifications_user_kind_period"),
    )
    op.create_index("ix_cycle_notifications_user_id", "cycle_notifications", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_cycle_notifications_user_id", table_name="cycle_notifications")
    op.drop_table("cycle_notifications")
    op.drop_index("uq_portal_run_batches_user_cycle", table_name="portal_run_batches")
    op.drop_column("portal_run_batches", "cycle_period")
    op.drop_column("portal_run_batches", "trigger")
