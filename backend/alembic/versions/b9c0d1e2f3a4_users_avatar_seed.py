"""users.avatar_seed — the seed a person picked for their generated avatar

Nullable on purpose: NULL means "derive the avatar from the username", which is
what every existing row already renders today. So there is nothing to backfill
and no NOT NULL constraint to trip old code.

Revision ID: b9c0d1e2f3a4
Revises: d7e8f9a0b1c2
Create Date: 2026-07-09 00:20:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b9c0d1e2f3a4'
down_revision: Union[str, Sequence[str], None] = 'd7e8f9a0b1c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('avatar_seed', sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'avatar_seed')
