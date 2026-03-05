"""add phone email employer columns

Revision ID: aa2f1f919567
Revises: f6a7b8c9d0e1
Create Date: 2026-03-05 11:58:48.615721
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'aa2f1f919567'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('client_records', sa.Column('client_phone', sa.String(length=30), nullable=True))
    op.add_column('client_records', sa.Column('client_email', sa.String(length=100), nullable=True))
    op.add_column('client_records', sa.Column('employer_name', sa.String(length=100), nullable=True))
    op.add_column('client_records', sa.Column('employer_id', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('client_records', 'employer_id')
    op.drop_column('client_records', 'employer_name')
    op.drop_column('client_records', 'client_email')
    op.drop_column('client_records', 'client_phone')
