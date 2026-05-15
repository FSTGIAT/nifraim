"""Add fund_track_funds (per-fund detail rows per maslul).

Revision ID: x3y4z5a6b7c8
Revises: w2x3y4z5a6b7
Create Date: 2026-05-16 01:00:00.000000

Adds a sibling table to fund_tracks holding individual fund rows
(e.g. "כלל תמר מניות") under each maslul. Refreshed by the scraper via
delete-then-insert on every run. Powers AI questions like
"איזו קופה השיגה את התשואה הגבוהה ביותר בחודש?".
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "x3y4z5a6b7c8"
down_revision: Union[str, Sequence[str], None] = "w2x3y4z5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fund_track_funds",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "track_id",
            sa.String(64),
            sa.ForeignKey("fund_tracks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fund_name", sa.String(120), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("month_return", sa.Numeric(6, 2), nullable=True),
        sa.Column("y1_return", sa.Numeric(6, 2), nullable=True),
        sa.Column("y3_return", sa.Numeric(6, 2), nullable=True),
        sa.Column("y5_return", sa.Numeric(6, 2), nullable=True),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_fund_track_funds_track_id",
        "fund_track_funds",
        ["track_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_fund_track_funds_track_id", table_name="fund_track_funds")
    op.drop_table("fund_track_funds")
