"""AI mail agent: the agent's writing-style profile

Revision ID: mail_agent_02
Revises: mail_agent_01
Create Date: 2026-09-25

Additive only: one new table.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "mail_agent_02"
down_revision: Union[str, Sequence[str], None] = "mail_agent_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "mail_agent_profiles",
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("signature", sa.Text()),
        sa.Column("tone", sa.String(16)),
        sa.Column("address_form", sa.String(16)),
        sa.Column("writer_form", sa.String(16)),
        sa.Column("greeting", sa.String(255)),
        sa.Column("closing", sa.String(255)),
        sa.Column("customer_rules", sa.Text()),
        sa.Column("insurer_rules", sa.Text()),
        sa.Column("never_say", sa.Text()),
        sa.Column("style_notes", sa.Text()),
        sa.Column("encrypted_examples", sa.Text()),
        sa.Column("learn_opt_in", sa.Boolean()),
        sa.Column("learned_at", sa.DateTime()),
        sa.Column("skipped_at", sa.DateTime()),
        sa.Column("completed_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )


def downgrade() -> None:
    op.drop_table("mail_agent_profiles")
