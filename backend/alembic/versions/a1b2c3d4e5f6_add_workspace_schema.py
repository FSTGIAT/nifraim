"""add_workspace_schema

Revision ID: a1b2c3d4e5f6
Revises: 4e172183f374
Create Date: 2026-02-12 10:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '4e172183f374'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add workspace columns to file_uploads
    op.add_column('file_uploads', sa.Column('is_production', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('file_uploads', sa.Column('file_category', sa.String(length=20), nullable=True, server_default='general'))

    # Create recruits table
    op.create_table(
        'recruits',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('id_number', sa.String(length=20), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('company', sa.String(length=100), nullable=True),
        sa.Column('product', sa.String(length=100), nullable=True),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('recruits')
    op.drop_column('file_uploads', 'file_category')
    op.drop_column('file_uploads', 'is_production')
