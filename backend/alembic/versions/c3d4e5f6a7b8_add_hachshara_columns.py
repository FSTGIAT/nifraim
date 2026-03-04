"""add_hachshara_columns

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-02-18 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('client_records', sa.Column('management_fee_amount', sa.Numeric(precision=15, scale=2), nullable=True))
    op.add_column('client_records', sa.Column('processing_date', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('client_records', 'processing_date')
    op.drop_column('client_records', 'management_fee_amount')
