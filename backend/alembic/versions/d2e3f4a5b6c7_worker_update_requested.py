"""worker_heartbeats.update_requested_at (UI 'update worker' button)

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-06-29 17:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'd2e3f4a5b6c7'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'worker_heartbeats',
        sa.Column('update_requested_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('worker_heartbeats', 'update_requested_at')
