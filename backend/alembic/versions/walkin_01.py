"""Walk-in customers: hand-added customers whose phones the Nifraim App takes calls for.

Revision ID: walkin_01
Revises: calls_04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "walkin_01"
down_revision = "calls_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "walkin_customers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("id_number", sa.String(20), nullable=False),
        sa.Column("first_name", sa.String(80), nullable=False),
        sa.Column("last_name", sa.String(80), nullable=True),
        sa.Column("phone", sa.String(30), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_walkin_customers_user", "walkin_customers", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_walkin_customers_user", table_name="walkin_customers")
    op.drop_table("walkin_customers")
