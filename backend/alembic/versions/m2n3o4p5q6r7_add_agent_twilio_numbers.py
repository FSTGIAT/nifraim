"""add agent_twilio_numbers + portal_credentials.contact_phone_synced_to

Revision ID: m2n3o4p5q6r7
Revises: k1l2m3n4o5p6
Create Date: 2026-04-30 17:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "m2n3o4p5q6r7"
down_revision: Union[str, Sequence[str], None] = "k1l2m3n4o5p6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_twilio_numbers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("phone_number", sa.String(length=20), nullable=False),
        sa.Column("twilio_sid", sa.String(length=64), nullable=False),
        sa.Column("provisioned_at", sa.DateTime(), nullable=False),
        sa.Column("released_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_twilio_numbers_user_active", "agent_twilio_numbers", ["user_id", "released_at"])
    op.create_index("ix_agent_twilio_numbers_phone", "agent_twilio_numbers", ["phone_number"])

    op.add_column(
        "portal_credentials",
        sa.Column("contact_phone_synced_to", sa.String(length=20), nullable=True),
    )

    # Distinguish a normal report-download run from a one-time contact-phone
    # migration run; both use portal_runs but have different success criteria.
    op.add_column(
        "portal_runs",
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="download"),
    )


def downgrade() -> None:
    op.drop_column("portal_runs", "kind")
    op.drop_column("portal_credentials", "contact_phone_synced_to")
    op.drop_index("ix_agent_twilio_numbers_phone", table_name="agent_twilio_numbers")
    op.drop_index("ix_agent_twilio_numbers_user_active", table_name="agent_twilio_numbers")
    op.drop_table("agent_twilio_numbers")
