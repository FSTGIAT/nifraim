"""Customer portal setup wizard: per-link settings, agent offers, offer clicks

Revision ID: portal_setup_01
Revises: mail_agent_03
Create Date: 2026-09-27

Additive only. `customer_portal_links.settings` is NULL for every existing
link, which the app reads as "show everything" — no behaviour change.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "portal_setup_01"
down_revision: Union[str, Sequence[str], None] = "mail_agent_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column("customer_portal_links", sa.Column("settings", postgresql.JSONB, nullable=True))

    op.create_table(
        "agent_portal_offers",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("service_key", sa.String(32), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("user_id", "service_key", name="uq_agent_portal_offer"),
    )
    op.create_index("ix_agent_portal_offers_user_id", "agent_portal_offers", ["user_id"])

    op.create_table(
        "portal_offer_clicks",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("portal_link_id", UUID, sa.ForeignKey("customer_portal_links.id", ondelete="CASCADE"), nullable=False),
        sa.Column("service_key", sa.String(32), nullable=False),
        sa.Column("clicked_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_portal_offer_clicks_portal_link_id", "portal_offer_clicks", ["portal_link_id"])


def downgrade() -> None:
    op.drop_index("ix_portal_offer_clicks_portal_link_id", table_name="portal_offer_clicks")
    op.drop_table("portal_offer_clicks")
    op.drop_index("ix_agent_portal_offers_user_id", table_name="agent_portal_offers")
    op.drop_table("agent_portal_offers")
    op.drop_column("customer_portal_links", "settings")
