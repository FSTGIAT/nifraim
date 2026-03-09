"""add customer_portal_links

Revision ID: cd8aa43f5736
Revises: aa2f1f919567
Create Date: 2026-03-09 18:49:52.097211
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'cd8aa43f5736'
down_revision: Union[str, None] = 'aa2f1f919567'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('customer_portal_links',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('token', sa.String(length=64), nullable=False),
    sa.Column('customer_id_number', sa.String(length=20), nullable=False),
    sa.Column('customer_name', sa.String(length=200), nullable=False),
    sa.Column('customer_email', sa.String(length=100), nullable=True),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('failed_attempts', sa.Integer(), server_default='0', nullable=False),
    sa.Column('last_failed_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('last_accessed_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_customer_portal_links_token'), 'customer_portal_links', ['token'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_customer_portal_links_token'), table_name='customer_portal_links')
    op.drop_table('customer_portal_links')
