"""Gateway self-update: one row with the released version, the pin, and what the
Gateway reports it is running.

Revision ID: maslaka_gateway_01
Revises: maslaka_holding_01
"""
from alembic import op
import sqlalchemy as sa

revision = "maslaka_gateway_01"
down_revision = "maslaka_holding_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gateway_state",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("released_version", sa.String(32), nullable=True),
        sa.Column("released_by", sa.String(200), nullable=True),
        sa.Column("released_at", sa.DateTime(), nullable=True),
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("running_version", sa.String(32), nullable=True),
        sa.Column("state", sa.String(40), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("last_tick_ok_at", sa.DateTime(), nullable=True),
        sa.Column("reported_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("gateway_state")
