"""Agreement requests: auto-email insurers for the commission agreement

Revision ID: agreement_req_01
Revises: cycle_01
Create Date: 2026-09-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "agreement_req_01"
down_revision: Union[str, Sequence[str], None] = "cycle_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "agreement_requests",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_key", sa.String(100), nullable=False),
        sa.Column("company_name", sa.String(100), nullable=False),
        sa.Column("to_email", sa.String(255), nullable=False),
        sa.Column("contact_name", sa.String(100), nullable=True),
        sa.Column("subject", sa.String(255), nullable=True),
        sa.Column("sent_message_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="sent"),
        sa.Column("sent_at", sa.DateTime, nullable=True),
        sa.Column("replied_at", sa.DateTime, nullable=True),
        sa.Column("reply_message_id", sa.String(255), nullable=True),
        sa.Column("document_id", UUID, sa.ForeignKey("ai_documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("user_id", "company_key", name="uq_agreement_requests_user_company"),
    )
    op.create_index("ix_agreement_requests_user_id", "agreement_requests", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_agreement_requests_user_id", table_name="agreement_requests")
    op.drop_table("agreement_requests")
