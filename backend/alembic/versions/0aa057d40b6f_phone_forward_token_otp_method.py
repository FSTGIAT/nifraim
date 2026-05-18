"""phone_forward_token + otp_method

Revision ID: 0aa057d40b6f
Revises: x3y4z5a6b7c8
Create Date: 2026-05-16 19:32:17.631973
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0aa057d40b6f'
down_revision: Union[str, None] = 'x3y4z5a6b7c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('phone_forward_token', sa.String(length=64), nullable=True),
    )
    op.create_index(
        op.f('ix_users_phone_forward_token'),
        'users',
        ['phone_forward_token'],
        unique=True,
    )
    op.add_column(
        'portal_credentials',
        sa.Column(
            'otp_method',
            sa.String(length=20),
            server_default='twilio',
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column('portal_credentials', 'otp_method')
    op.drop_index(op.f('ix_users_phone_forward_token'), table_name='users')
    op.drop_column('users', 'phone_forward_token')
