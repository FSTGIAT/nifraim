"""add portal automation tables

Revision ID: k1l2m3n4o5p6
Revises: a0586c3abe01, i9d0e1f2g3h4
Create Date: 2026-04-30 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'k1l2m3n4o5p6'
# Merge of two existing heads — debts branch + recruits-sign-date branch.
down_revision: Union[str, Sequence[str], None] = ('a0586c3abe01', 'i9d0e1f2g3h4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'portal_credentials',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('portal_kind', sa.String(length=32), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('encrypted_password', sa.Text(), nullable=False),
        sa.Column('twilio_to_number', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('schedule_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('category_hint', sa.String(length=64), nullable=True),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('last_run_status', sa.String(length=20), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'portal_kind', name='uq_portal_credentials_user_kind'),
    )
    op.create_index('ix_portal_credentials_schedule', 'portal_credentials', ['schedule_enabled', 'is_active'])

    op.create_table(
        'portal_runs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('credential_id', sa.UUID(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('stage', sa.String(length=20), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('screenshot_path', sa.String(length=255), nullable=True),
        sa.Column('downloaded_filename', sa.String(length=255), nullable=True),
        sa.Column('upload_id', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['credential_id'], ['portal_credentials.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['upload_id'], ['file_uploads.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_portal_runs_user_started', 'portal_runs', ['user_id', 'started_at'])
    op.create_index('ix_portal_runs_status', 'portal_runs', ['status'])
    op.create_index('ix_portal_runs_credential', 'portal_runs', ['credential_id', 'started_at'])

    op.create_table(
        'otp_inbox',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('from_number', sa.String(length=20), nullable=False),
        sa.Column('to_number', sa.String(length=20), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('otp_code', sa.String(length=8), nullable=True),
        sa.Column('received_at', sa.DateTime(), nullable=False),
        sa.Column('consumed_at', sa.DateTime(), nullable=True),
        sa.Column('portal_run_id', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['portal_run_id'], ['portal_runs.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_otp_inbox_user_consumed', 'otp_inbox', ['user_id', 'consumed_at'])
    op.create_index('ix_otp_inbox_received', 'otp_inbox', ['received_at'])


def downgrade() -> None:
    op.drop_index('ix_otp_inbox_received', table_name='otp_inbox')
    op.drop_index('ix_otp_inbox_user_consumed', table_name='otp_inbox')
    op.drop_table('otp_inbox')

    op.drop_index('ix_portal_runs_credential', table_name='portal_runs')
    op.drop_index('ix_portal_runs_status', table_name='portal_runs')
    op.drop_index('ix_portal_runs_user_started', table_name='portal_runs')
    op.drop_table('portal_runs')

    op.drop_index('ix_portal_credentials_schedule', table_name='portal_credentials')
    op.drop_table('portal_credentials')
