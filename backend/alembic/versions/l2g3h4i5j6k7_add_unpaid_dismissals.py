"""add unpaid_dismissals table

Revision ID: l2g3h4i5j6k7
Revises: k1f2g3h4i5j6
Create Date: 2026-04-27 22:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "l2g3h4i5j6k7"
down_revision: Union[str, None] = "k1f2g3h4i5j6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "unpaid_dismissals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("company_name", sa.String(length=100), nullable=False),
        sa.Column("customer_id_number", sa.String(length=40), nullable=False),
        sa.Column("dismissed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "company_name", "customer_id_number",
            name="uq_unpaid_dismissals_user_company_customer",
        ),
    )
    op.create_index(
        "ix_unpaid_dismissals_user_company",
        "unpaid_dismissals",
        ["user_id", "company_name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_unpaid_dismissals_user_company", table_name="unpaid_dismissals")
    op.drop_table("unpaid_dismissals")
