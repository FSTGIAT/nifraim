"""מסלקה holdings: the account's status (STATUS-POLISA-O-CHESHBON), so two accounts
under one policy number (an inactive and an active one) stay two products.

Revision ID: maslaka_holding_01
Revises: policies_03
"""
from alembic import op
import sqlalchemy as sa

revision = "maslaka_holding_01"
down_revision = "policies_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pension_holdings", sa.Column("account_status", sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column("pension_holdings", "account_status")
