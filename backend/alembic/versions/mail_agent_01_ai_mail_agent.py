"""AI mail agent: watched senders, mail items, AI usage ledger

Revision ID: mail_agent_01
Revises: mslk_shiyuch_02
Create Date: 2026-09-24

Additive only: three new tables and one nullable column.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "mail_agent_01"
down_revision: Union[str, Sequence[str], None] = "mslk_shiyuch_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "mail_watch_senders",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("address", sa.String(255), nullable=False),
        sa.Column("label", sa.String(255)),
        sa.Column("kind", sa.String(16), nullable=False, server_default="other"),
        sa.Column("company_name", sa.String(100)),
        sa.Column("customer_id_number", sa.String(20)),
        sa.Column("created_at", sa.DateTime()),
        sa.UniqueConstraint("user_id", "address", name="uq_mail_watch_sender"),
    )
    op.create_index("ix_mail_watch_senders_user_id", "mail_watch_senders", ["user_id"])

    op.create_table(
        "mail_items",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("watch_sender_id", UUID, sa.ForeignKey("mail_watch_senders.id", ondelete="SET NULL")),
        sa.Column("provider_id", sa.String(255)),
        sa.Column("internet_message_id", sa.String(512), nullable=False),
        sa.Column("in_reply_to", sa.String(512)),
        sa.Column("references", sa.Text()),
        sa.Column("from_address", sa.String(255), nullable=False),
        sa.Column("from_name", sa.String(255)),
        sa.Column("subject", sa.String(998)),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("encrypted_body", sa.Text()),
        sa.Column("attachments", sa.JSON()),
        sa.Column("category", sa.String(32)),
        sa.Column("summary", sa.Text()),
        sa.Column("entities", sa.JSON()),
        sa.Column("suggested_action", sa.String(16)),
        sa.Column("ai_skipped_reason", sa.String(64)),
        sa.Column("linked_company", sa.String(100)),
        sa.Column("linked_customer_id_number", sa.String(20)),
        sa.Column("draft_subject", sa.String(998)),
        sa.Column("draft_body", sa.Text()),
        sa.Column("draft_warnings", sa.JSON()),
        sa.Column("draft_model", sa.String(64)),
        sa.Column("draft_edited", sa.Boolean(), server_default=sa.false()),
        sa.Column("sent_message_id", sa.String(512)),
        sa.Column("sent_at", sa.DateTime()),
        sa.Column("imported_upload_id", UUID),
        sa.Column("status", sa.String(16), nullable=False, server_default="new"),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
        sa.UniqueConstraint("user_id", "internet_message_id", name="uq_mail_item_msgid"),
    )
    op.create_index("ix_mail_items_user_id", "mail_items", ["user_id"])
    op.create_index("ix_mail_items_status", "mail_items", ["status"])
    op.create_index("ix_mail_items_received_at", "mail_items", ["received_at"])

    op.create_table(
        "ai_usage",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feature", sa.String(32), nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("input_tokens", sa.Integer(), server_default="0"),
        sa.Column("output_tokens", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_ai_usage_user_id", "ai_usage", ["user_id"])
    op.create_index("ix_ai_usage_created_at", "ai_usage", ["created_at"])

    op.add_column("mailbox_configs", sa.Column("mail_agent_checked_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("mailbox_configs", "mail_agent_checked_at")
    op.drop_table("ai_usage")
    op.drop_table("mail_items")
    op.drop_table("mail_watch_senders")
