"""add portal_run_batches + portal_runs.batch_id

Backs the "run all portals" feature: a PortalRunBatch groups the per-credential
PortalRun children so the orchestrator can aggregate every downloaded production
file into ONE merged production upload and every נפרעים file into ONE merged
commission upload at batch end.

Revision ID: n7o8p9q0r1s2
Revises: 265c79c9e605
Create Date: 2026-06-18 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'n7o8p9q0r1s2'
down_revision: Union[str, None] = '265c79c9e605'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'portal_run_batches',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
        sa.Column('total', sa.Integer(), server_default='0', nullable=False),
        sa.Column('succeeded', sa.Integer(), server_default='0', nullable=False),
        sa.Column('failed', sa.Integer(), server_default='0', nullable=False),
        sa.Column('current_run_id', sa.UUID(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('merged_upload_id', sa.UUID(), nullable=True),
        sa.Column('merged_commission_upload_id', sa.UUID(), nullable=True),
        sa.Column('period_month', sa.Date(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['merged_upload_id'], ['file_uploads.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['merged_commission_upload_id'], ['file_uploads.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_portal_run_batches_user_started', 'portal_run_batches', ['user_id', 'started_at'], unique=False)
    op.create_index('ix_portal_run_batches_status', 'portal_run_batches', ['status'], unique=False)

    op.add_column('portal_runs', sa.Column('batch_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_portal_runs_batch_id', 'portal_runs', 'portal_run_batches',
        ['batch_id'], ['id'], ondelete='SET NULL',
    )
    op.create_index('ix_portal_runs_batch', 'portal_runs', ['batch_id', 'started_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_portal_runs_batch', table_name='portal_runs')
    op.drop_constraint('fk_portal_runs_batch_id', 'portal_runs', type_='foreignkey')
    op.drop_column('portal_runs', 'batch_id')

    op.drop_index('ix_portal_run_batches_status', table_name='portal_run_batches')
    op.drop_index('ix_portal_run_batches_user_started', table_name='portal_run_batches')
    op.drop_table('portal_run_batches')
