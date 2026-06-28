"""worker_heartbeats table (local worker liveness)

Revision ID: c1d2e3f4a5b6
Revises: b8c9d0e1f2a3
Create Date: 2026-06-28 18:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'worker_heartbeats',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('last_seen', sa.DateTime(), nullable=False),
        sa.Column('hostname', sa.String(120), nullable=True),
        sa.Column('current_job', sa.String(200), nullable=True),
    )
    op.create_index('ix_worker_heartbeats_user_id', 'worker_heartbeats', ['user_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_worker_heartbeats_user_id', table_name='worker_heartbeats')
    op.drop_table('worker_heartbeats')
