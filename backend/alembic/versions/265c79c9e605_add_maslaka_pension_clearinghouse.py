"""add maslaka pension clearinghouse

Creates the 4 backing tables for the המסלקה הפנסיונית integration:
  - pension_inquiries     (request lifecycle, status state machine)
  - pension_audit_logs    (append-only audit, retention-safe)
  - pension_raw_payloads  (Fernet-encrypted XML at rest, LargeBinary)
  - pension_holdings      (per-product enrichment from Holdings v009)

Pre-existing schema drift detected by alembic autogenerate (agencies,
agency_invites, unpaid_snapshots, etc.) was REMOVED from this migration so
the clearinghouse change ships independently. If that drift needs to be
reconciled, do it in a separate migration.

Revision ID: 265c79c9e605
Revises: z5a6b7c8d9e0
Create Date: 2026-05-31 21:56:37.225343
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '265c79c9e605'
down_revision: Union[str, None] = 'z5a6b7c8d9e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── pension_inquiries ────────────────────────────────────────────────
    op.create_table(
        'pension_inquiries',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('customer_id_number', sa.String(length=20), nullable=False),
        sa.Column('customer_name', sa.String(length=200), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
        sa.Column('interface_code', sa.String(length=20), nullable=True),
        sa.Column('request_reference', sa.String(length=64), nullable=False),
        sa.Column('vault_outbound_filename', sa.String(length=255), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('error_detail', sa.String(length=500), nullable=True),
        sa.Column('providers_expected', sa.Integer(), nullable=True),
        sa.Column('providers_received', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_pension_inquiries_customer_id_number'), 'pension_inquiries', ['customer_id_number'], unique=False)
    op.create_index(op.f('ix_pension_inquiries_request_reference'), 'pension_inquiries', ['request_reference'], unique=True)
    op.create_index('ix_pension_inquiries_user_customer', 'pension_inquiries', ['user_id', 'customer_id_number'], unique=False)
    op.create_index(op.f('ix_pension_inquiries_user_id'), 'pension_inquiries', ['user_id'], unique=False)
    op.create_index('ix_pension_inquiries_user_status', 'pension_inquiries', ['user_id', 'status'], unique=False)

    # ── pension_audit_logs ───────────────────────────────────────────────
    op.create_table(
        'pension_audit_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('inquiry_id', sa.UUID(), nullable=True),
        sa.Column('customer_id_number', sa.String(length=20), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('from_status', sa.String(length=20), nullable=True),
        sa.Column('to_status', sa.String(length=20), nullable=True),
        sa.Column('actor', sa.String(length=20), nullable=False),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        # inquiry_id intentionally SET NULL — preserve audit trail if the
        # parent inquiry is purged later (compliance: events still happened).
        sa.ForeignKeyConstraint(['inquiry_id'], ['pension_inquiries.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_pension_audit_logs_created_at'), 'pension_audit_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_pension_audit_logs_customer_id_number'), 'pension_audit_logs', ['customer_id_number'], unique=False)
    op.create_index(op.f('ix_pension_audit_logs_inquiry_id'), 'pension_audit_logs', ['inquiry_id'], unique=False)
    op.create_index(op.f('ix_pension_audit_logs_user_id'), 'pension_audit_logs', ['user_id'], unique=False)
    op.create_index('ix_pension_audit_user_created', 'pension_audit_logs', ['user_id', 'created_at'], unique=False)

    # ── pension_raw_payloads ─────────────────────────────────────────────
    op.create_table(
        'pension_raw_payloads',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('inquiry_id', sa.UUID(), nullable=False),
        sa.Column('direction', sa.String(length=20), nullable=False),
        sa.Column('interface_code', sa.String(length=20), nullable=True),
        sa.Column('source_filename', sa.String(length=255), nullable=True),
        # LargeBinary so we don't pay base64's 33% overhead on encrypted blobs.
        sa.Column('ciphertext', sa.LargeBinary(), nullable=True),
        sa.Column('byte_size', sa.Integer(), server_default='0', nullable=False),
        sa.Column('purged', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['inquiry_id'], ['pension_inquiries.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_pension_raw_payloads_created_at'), 'pension_raw_payloads', ['created_at'], unique=False)
    op.create_index(op.f('ix_pension_raw_payloads_inquiry_id'), 'pension_raw_payloads', ['inquiry_id'], unique=False)
    op.create_index(op.f('ix_pension_raw_payloads_user_id'), 'pension_raw_payloads', ['user_id'], unique=False)

    # ── pension_holdings ─────────────────────────────────────────────────
    op.create_table(
        'pension_holdings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('inquiry_id', sa.UUID(), nullable=False),
        sa.Column('customer_id_number', sa.String(length=20), nullable=False),
        sa.Column('receiving_company', sa.String(length=100), nullable=True),
        sa.Column('provider_code', sa.String(length=20), nullable=True),
        sa.Column('product', sa.String(length=100), nullable=True),
        sa.Column('product_type', sa.String(length=100), nullable=True),
        sa.Column('fund_policy_number', sa.String(length=50), nullable=True),
        sa.Column('track', sa.String(length=100), nullable=True),
        sa.Column('accumulation', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('total_premium', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('management_fee_deposit', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('management_fee_balance', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('expected_pension', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('insurance_coverage', sa.Text(), nullable=True),
        sa.Column('status_date', sa.Date(), nullable=True),
        sa.Column('matched_client_record_id', sa.UUID(), nullable=True),
        sa.Column('match_status', sa.String(length=20), nullable=False),
        sa.Column('raw_payload_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['inquiry_id'], ['pension_inquiries.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['matched_client_record_id'], ['client_records.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['raw_payload_id'], ['pension_raw_payloads.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_pension_holdings_customer_id_number'), 'pension_holdings', ['customer_id_number'], unique=False)
    op.create_index(op.f('ix_pension_holdings_fund_policy_number'), 'pension_holdings', ['fund_policy_number'], unique=False)
    op.create_index(op.f('ix_pension_holdings_inquiry_id'), 'pension_holdings', ['inquiry_id'], unique=False)
    op.create_index(op.f('ix_pension_holdings_matched_client_record_id'), 'pension_holdings', ['matched_client_record_id'], unique=False)
    op.create_index('ix_pension_holdings_user_customer', 'pension_holdings', ['user_id', 'customer_id_number'], unique=False)
    op.create_index(op.f('ix_pension_holdings_user_id'), 'pension_holdings', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop in reverse dependency order.
    op.drop_index(op.f('ix_pension_holdings_user_id'), table_name='pension_holdings')
    op.drop_index('ix_pension_holdings_user_customer', table_name='pension_holdings')
    op.drop_index(op.f('ix_pension_holdings_matched_client_record_id'), table_name='pension_holdings')
    op.drop_index(op.f('ix_pension_holdings_inquiry_id'), table_name='pension_holdings')
    op.drop_index(op.f('ix_pension_holdings_fund_policy_number'), table_name='pension_holdings')
    op.drop_index(op.f('ix_pension_holdings_customer_id_number'), table_name='pension_holdings')
    op.drop_table('pension_holdings')

    op.drop_index(op.f('ix_pension_raw_payloads_user_id'), table_name='pension_raw_payloads')
    op.drop_index(op.f('ix_pension_raw_payloads_inquiry_id'), table_name='pension_raw_payloads')
    op.drop_index(op.f('ix_pension_raw_payloads_created_at'), table_name='pension_raw_payloads')
    op.drop_table('pension_raw_payloads')

    op.drop_index('ix_pension_audit_user_created', table_name='pension_audit_logs')
    op.drop_index(op.f('ix_pension_audit_logs_user_id'), table_name='pension_audit_logs')
    op.drop_index(op.f('ix_pension_audit_logs_inquiry_id'), table_name='pension_audit_logs')
    op.drop_index(op.f('ix_pension_audit_logs_customer_id_number'), table_name='pension_audit_logs')
    op.drop_index(op.f('ix_pension_audit_logs_created_at'), table_name='pension_audit_logs')
    op.drop_table('pension_audit_logs')

    op.drop_index('ix_pension_inquiries_user_status', table_name='pension_inquiries')
    op.drop_index(op.f('ix_pension_inquiries_user_id'), table_name='pension_inquiries')
    op.drop_index('ix_pension_inquiries_user_customer', table_name='pension_inquiries')
    op.drop_index(op.f('ix_pension_inquiries_request_reference'), table_name='pension_inquiries')
    op.drop_index(op.f('ix_pension_inquiries_customer_id_number'), table_name='pension_inquiries')
    op.drop_table('pension_inquiries')
