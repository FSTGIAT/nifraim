"""Add yield_recommendations table.

Revision ID: y4z5a6b7c8d9
Revises: x3y4z5a6b7c8
Create Date: 2026-05-19 00:00:00.000000

Stores the agent's currently-suggested track moves (production product → best
performing mygemel.net track in same category). The /api/yield-recommendations
endpoints read/write this table; the AI knowledge endpoint summarises it.
Re-running "Generate" replaces the user's rows wholesale.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "y4z5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "s1t2u3v4w5x6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "yield_recommendations",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "production_upload_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("file_uploads.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("id_number", sa.String(40), nullable=True),
        sa.Column("client_name", sa.String(200), nullable=True),
        sa.Column("fund_policy_number", sa.String(50), nullable=True),
        sa.Column("product_type", sa.String(100), nullable=True),
        sa.Column("current_company", sa.String(100), nullable=True),
        sa.Column("current_track", sa.String(120), nullable=True),
        sa.Column("current_yield_1y", sa.Numeric(6, 2), nullable=True),
        sa.Column("current_yield_3y", sa.Numeric(6, 2), nullable=True),
        sa.Column("current_yield_5y", sa.Numeric(6, 2), nullable=True),
        sa.Column("recommended_track_id", sa.String(64), nullable=False),
        sa.Column("recommended_track_name", sa.String(120), nullable=False),
        sa.Column("recommended_yield_1y", sa.Numeric(6, 2), nullable=True),
        sa.Column("recommended_yield_3y", sa.Numeric(6, 2), nullable=True),
        sa.Column("recommended_yield_5y", sa.Numeric(6, 2), nullable=True),
        sa.Column("accumulation", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("potential_annual_gain", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("reasoning", sa.String(500), nullable=True),
        sa.Column("confidence", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_yield_recommendations_user_id",
        "yield_recommendations",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_yield_recommendations_user_id", table_name="yield_recommendations")
    op.drop_table("yield_recommendations")
