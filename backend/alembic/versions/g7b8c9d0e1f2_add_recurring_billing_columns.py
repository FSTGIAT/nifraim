"""add_recurring_billing_columns

Revision ID: g7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-03-10 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "g7b8c9d0e1f2"
down_revision: Union[str, None] = "cd8aa43f5736"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("subscriptions", sa.Column("token_exp_date", sa.String(10), nullable=True))
    op.add_column("subscriptions", sa.Column("last4_digits", sa.String(4), nullable=True))
    op.add_column("subscriptions", sa.Column("card_brand", sa.String(20), nullable=True))
    op.add_column("subscriptions", sa.Column("next_charge_at", sa.DateTime(), nullable=True))
    op.add_column("subscriptions", sa.Column("last_charge_at", sa.DateTime(), nullable=True))
    op.add_column("subscriptions", sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False))
    op.add_column("subscriptions", sa.Column("cardcom_low_profile_code", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("subscriptions", "cardcom_low_profile_code")
    op.drop_column("subscriptions", "retry_count")
    op.drop_column("subscriptions", "last_charge_at")
    op.drop_column("subscriptions", "next_charge_at")
    op.drop_column("subscriptions", "card_brand")
    op.drop_column("subscriptions", "last4_digits")
    op.drop_column("subscriptions", "token_exp_date")
