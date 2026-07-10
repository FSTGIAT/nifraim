"""mailbox intake: mailbox_configs + mailbox_processed_messages.

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-07-09 21:30:00.000000

Hachshara emails production as `Ild_prod_*.zip` rather than exposing it in the
agent portal. These two tables back the mail intake: one config row per agent
(routed by the MX record of their address — microsoft/google/other), and a
dedup ledger so a message is never ingested twice.

`forward_token` mirrors `users.phone_forward_token`: the token in the recipient
address is what resolves the tenant on the public Resend webhook.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d6e7f8a9b0c1"
down_revision: Union[str, Sequence[str], None] = "c5d6e7f8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mailbox_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("email_address", sa.String(255), nullable=False),
        sa.Column("mail_host", sa.String(16), nullable=False, server_default="other"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        # microsoft
        sa.Column("encrypted_refresh_token", sa.Text()),
        sa.Column("oauth_tenant_id", sa.String(64)),
        sa.Column("delta_link", sa.Text()),
        # google
        sa.Column("encrypted_password", sa.Text()),
        sa.Column("imap_host", sa.String(255), nullable=False, server_default="imap.gmail.com"),
        sa.Column("imap_port", sa.Integer(), nullable=False, server_default="993"),
        sa.Column("folder", sa.String(128), nullable=False, server_default="INBOX"),
        sa.Column("uidvalidity", sa.Integer()),
        sa.Column("last_seen_uid", sa.Integer()),
        # other (forwarding)
        sa.Column("forward_token", sa.String(64)),
        # status
        sa.Column("last_received_at", sa.DateTime()),
        sa.Column("last_polled_at", sa.DateTime()),
        sa.Column("last_status", sa.String(32)),
        sa.Column("last_error", sa.String(64)),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", name="uq_mailbox_configs_user"),
    )
    op.create_index(
        "ix_mailbox_configs_forward_token", "mailbox_configs", ["forward_token"], unique=True
    )
    op.create_index("ix_mailbox_configs_active", "mailbox_configs", ["is_active", "mail_host"])

    op.create_table(
        "mailbox_processed_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "mailbox_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mailbox_configs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("message_id", sa.String(255)),
        sa.Column("attachment_filename", sa.String(255)),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("upload_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("file_uploads.id")),
        sa.Column("processed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("mailbox_id", "external_id", name="uq_mailbox_messages_external"),
    )
    op.create_index(
        "ix_mailbox_messages_message_id", "mailbox_processed_messages", ["message_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_mailbox_messages_message_id", table_name="mailbox_processed_messages")
    op.drop_table("mailbox_processed_messages")
    op.drop_index("ix_mailbox_configs_active", table_name="mailbox_configs")
    op.drop_index("ix_mailbox_configs_forward_token", table_name="mailbox_configs")
    op.drop_table("mailbox_configs")
