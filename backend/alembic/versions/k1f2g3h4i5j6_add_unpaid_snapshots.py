"""add unpaid_snapshots table

Revision ID: k1f2g3h4i5j6
Revises: j0e1f2g3h4i5
Create Date: 2026-04-25 14:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "k1f2g3h4i5j6"
down_revision: Union[str, None] = "j0e1f2g3h4i5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "unpaid_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("commission_upload_id", sa.UUID(), nullable=False),
        sa.Column("company_name", sa.String(length=100), nullable=False),
        sa.Column("period_label", sa.String(length=20), nullable=False),
        sa.Column("unpaid_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("unpaid_customers_json", sa.JSON(), nullable=False),
        sa.Column("email_sent_at", sa.DateTime(), nullable=True),
        sa.Column("email_sent_to", sa.String(length=255), nullable=True),
        sa.Column("snapshot_date", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["commission_upload_id"], ["file_uploads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "commission_upload_id", "company_name",
            name="uq_unpaid_snapshots_user_upload_company",
        ),
    )
    op.create_index(
        "ix_unpaid_snapshots_user_period",
        "unpaid_snapshots",
        ["user_id", "period_label"],
        unique=False,
    )
    op.create_index(
        "ix_unpaid_snapshots_user_company_period",
        "unpaid_snapshots",
        ["user_id", "company_name", "period_label"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_unpaid_snapshots_user_company_period", table_name="unpaid_snapshots")
    op.drop_index("ix_unpaid_snapshots_user_period", table_name="unpaid_snapshots")
    op.drop_table("unpaid_snapshots")
