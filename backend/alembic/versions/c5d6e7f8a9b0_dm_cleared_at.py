"""dm_conversations: per-side clear markers (delete a conversation for yourself)

A conversation row is SHARED by two people, so "delete" cannot drop the row —
that would erase the other person's history too. Each side gets its own
`*_cleared_at`; messages at or before it are hidden from that side only.

Revision ID: c5d6e7f8a9b0
Revises: b9c0d1e2f3a4
Create Date: 2026-07-09 00:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c5d6e7f8a9b0'
down_revision: Union[str, Sequence[str], None] = 'b9c0d1e2f3a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('dm_conversations', sa.Column('a_cleared_at', sa.DateTime(), nullable=True))
    op.add_column('dm_conversations', sa.Column('b_cleared_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('dm_conversations', 'b_cleared_at')
    op.drop_column('dm_conversations', 'a_cleared_at')
