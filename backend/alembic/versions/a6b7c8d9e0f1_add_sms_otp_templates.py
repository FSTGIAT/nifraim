"""add_sms_otp_templates

Revision ID: a6b7c8d9e0f1
Revises: n7o8p9q0r1s2
Create Date: 2026-06-20 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'a6b7c8d9e0f1'
down_revision: Union[str, Sequence[str], None] = 'n7o8p9q0r1s2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sms_otp_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('company_name', sa.String(100), nullable=False),
        sa.Column('portal_kind', sa.String(32), nullable=True),
        sa.Column('pattern', sa.String(500), nullable=False),
        sa.Column('example', sa.String(500), nullable=True),
        sa.Column('is_block', sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column('active', sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('sms_otp_templates')
