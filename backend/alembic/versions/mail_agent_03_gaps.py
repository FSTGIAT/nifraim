"""AI mail agent: append-only ledger of what the drafter was missing

Revision ID: mail_agent_03
Revises: mslk_auto_prod_04
Create Date: 2026-09-26

Additive only: one new table, backfilled from the "חסר מידע:" lines already
sitting in mail_items.draft_warnings.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "mail_agent_03"
down_revision: Union[str, Sequence[str], None] = "mslk_auto_prod_04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "mail_agent_gaps",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mail_item_id", UUID, sa.ForeignKey("mail_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("missing", sa.Text, nullable=False),
        sa.Column("category", sa.String(32), nullable=True),
        sa.Column("sender_kind", sa.String(16), nullable=True),
        sa.Column("from_address", sa.String(255), nullable=True),
        sa.Column("linked_company", sa.String(100), nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("draft_model", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_mail_agent_gaps_user_id", "mail_agent_gaps", ["user_id"])
    op.create_index("ix_mail_agent_gaps_mail_item_id", "mail_agent_gaps", ["mail_item_id"])
    op.create_index("ix_mail_agent_gaps_created_at", "mail_agent_gaps", ["created_at"])
    # Backfill from drafts made before this ledger existed.
    op.execute("""
        INSERT INTO mail_agent_gaps (id, user_id, mail_item_id, missing, category, from_address,
                                     linked_company, summary, draft_model, created_at)
        SELECT gen_random_uuid(), i.user_id, i.id, substr(w.v, length('חסר מידע:') + 1),
               i.category, i.from_address, i.linked_company, i.summary, i.draft_model,
               coalesce(i.updated_at, i.created_at)
        FROM mail_items i, jsonb_array_elements_text(i.draft_warnings::jsonb) AS w(v)
        WHERE i.draft_warnings IS NOT NULL AND w.v LIKE 'חסר מידע:%'
    """)
    op.execute("UPDATE mail_agent_gaps SET missing = btrim(missing)")


def downgrade() -> None:
    op.drop_table("mail_agent_gaps")
