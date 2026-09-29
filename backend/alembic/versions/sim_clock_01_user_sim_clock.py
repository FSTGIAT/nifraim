"""users.sim_clock_offset_s — a TEST user's simulated "today".

Seconds added to the real clock for this user's cycle/מסלקה dates. NULL for
every real agent. Set only by an admin when creating a test user.

Revision ID: sim_clock_01
Revises: collection_01
"""
from alembic import op
import sqlalchemy as sa

revision = "sim_clock_01"
down_revision = "collection_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("sim_clock_offset_s", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "sim_clock_offset_s")
