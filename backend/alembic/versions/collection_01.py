"""Collection agent (סוכן גבייה): one case per (agent, insurer, month) with unpaid commission

Revision ID: collection_01
Revises: agreement_req_01
Create Date: 2026-09-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "collection_01"
down_revision: Union[str, Sequence[str], None] = "agreement_req_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "collection_cases",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_key", sa.String(100), nullable=False),
        sa.Column("company_name", sa.String(100), nullable=False),
        sa.Column("period", sa.Date, nullable=True),
        sa.Column("items", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("customers_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("expected_total", sa.Float, nullable=False, server_default="0"),
        sa.Column("to_email", sa.String(255), nullable=True),
        sa.Column("contact_name", sa.String(100), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("draft_subject", sa.String(255), nullable=True),
        sa.Column("draft_body", sa.Text, nullable=True),
        sa.Column("sent_at", sa.DateTime, nullable=True),
        sa.Column("sent_message_id", sa.String(255), nullable=True),
        sa.Column("reminder_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_reminder_at", sa.DateTime, nullable=True),
        sa.Column("replied_at", sa.DateTime, nullable=True),
        sa.Column("reply_message_id", sa.String(255), nullable=True),
        sa.Column("reply_summary", sa.Text, nullable=True),
        sa.Column("resolved_at", sa.DateTime, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("user_id", "company_key", "period", name="uq_collection_cases_user_company_period"),
    )
    op.create_index("ix_collection_cases_user_id", "collection_cases", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_collection_cases_user_id", table_name="collection_cases")
    op.drop_table("collection_cases")
