"""הר הביטוח history: a re-fetch supersedes (is_current=false) instead of deleting, and each
request keeps what changed since the previous fetch (harb_requests.changes).

Revision ID: policies_03
Revises: policies_02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "policies_03"
down_revision = "policies_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("insurance_policies", sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("policy_documents", sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("harb_requests", sa.Column("changes", JSONB(), nullable=True))
    op.create_index("ix_insurance_policies_current", "insurance_policies", ["user_id", "customer_id_number", "is_current"])


def downgrade() -> None:
    op.drop_index("ix_insurance_policies_current", table_name="insurance_policies")
    op.drop_column("harb_requests", "changes")
    op.drop_column("policy_documents", "is_current")
    op.drop_column("insurance_policies", "is_current")
