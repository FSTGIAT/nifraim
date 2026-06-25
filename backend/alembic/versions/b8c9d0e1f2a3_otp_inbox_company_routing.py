"""otp_inbox company routing columns

Revision ID: b8c9d0e1f2a3
Revises: a6b7c8d9e0f1
Create Date: 2026-06-20 15:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, Sequence[str], None] = 'a6b7c8d9e0f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Company a forwarded OTP belongs to, matched server-side from the SMS body
    # against SmsOtpTemplate patterns. portal_kind = base company token
    # (e.g. "phoenix"); matched_company = Hebrew display name. Both nullable —
    # NULL when no company template matched (runner falls back to time-based).
    op.add_column('otp_inbox', sa.Column('portal_kind', sa.String(32), nullable=True))
    op.add_column('otp_inbox', sa.Column('matched_company', sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column('otp_inbox', 'matched_company')
    op.drop_column('otp_inbox', 'portal_kind')
