"""users.is_test_user — accounts an admin made for testing; only these may be
deleted from the admin (DELETE /api/admin/users/{id}).

Backfills users already on a simulated clock or on the test email domain.

Revision ID: test_user_02
Revises: sim_clock_01
"""
from alembic import op
import sqlalchemy as sa

revision = "test_user_02"
down_revision = "sim_clock_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column(
        "is_test_user", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute(
        "UPDATE users SET is_test_user = true "
        "WHERE is_admin = false AND (sim_clock_offset_s IS NOT NULL "
        "OR email LIKE '%@nifraim-test.com')"
    )


def downgrade() -> None:
    op.drop_column("users", "is_test_user")
