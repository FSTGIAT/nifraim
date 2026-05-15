"""Add fund_tracks table for pension-fund ticker.

Revision ID: w2x3y4z5a6b7
Revises: v1w2x3y4z5a6
Create Date: 2026-05-16 00:30:00.000000

Stores latest published returns for 10 Israeli savings/pension fund tracks
(קופות גמל / קרנות השתלמות / פוליסות חיסכון / קופות גמל להשקעה). Powers the
Nasdaq-style ticker at the top of WorkspaceView and feeds the AI knowledge
layer at /api/ai/knowledge so the chat assistant can reason over current
market context.

10 rows are seeded with metadata only (label, category, maslul, sort_order);
the scraper at app.services.fund_scraper populates the return columns on
its first run (fires on startup if scraped_at IS NULL, then weekly Sun
06:00 IST via APScheduler).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "w2x3y4z5a6b7"
down_revision: Union[str, Sequence[str], None] = "v1w2x3y4z5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Order: matches what the user enumerated. Sort order drives the ticker chip
# order from right-to-left in RTL.
SEED_TRACKS = [
    ("gemel-under50",   'קופ"ג עד 50',       "kupot_gemel",      "under50", 10),
    ("gemel-50to60",    'קופ"ג 50-60',       "kupot_gemel",      "50to60",  20),
    ("gemel-over60",    'קופ"ג 60+',         "kupot_gemel",      "over60",  30),
    ("gemel-stocks",    'קופ"ג מניות',        "kupot_gemel",      "stocks",  40),
    ("hish-klali",      "השתלמות כללי",      "keren_hishtalmut", "klali",   50),
    ("hish-stocks",     "השתלמות מניות",     "keren_hishtalmut", "stocks",  60),
    ("polisa-klali",    "חיסכון כללי",        "polisot_hisachon", "klali",   70),
    ("polisa-stocks",   "חיסכון מניות",       "polisot_hisachon", "stocks",  80),
    ("gle-stocks",      'גמ"ל להשק׳ מניות',   "gemel_lehashkaa",  "stocks",  90),
    ("gle-klali",       'גמ"ל להשק׳ כללי',    "gemel_lehashkaa",  "klali",  100),
]


def upgrade() -> None:
    op.create_table(
        "fund_tracks",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("label_he", sa.String(80), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("maslul", sa.String(32), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("month_return", sa.Numeric(6, 2), nullable=True),
        sa.Column("ytd_return", sa.Numeric(6, 2), nullable=True),
        sa.Column("y1_return", sa.Numeric(6, 2), nullable=True),
        sa.Column("y3_return", sa.Numeric(6, 2), nullable=True),
        sa.Column("y5_return", sa.Numeric(6, 2), nullable=True),
        sa.Column("period_label", sa.String(16), nullable=True),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Seed metadata. Returns intentionally NULL — scraper fills on first run.
    op.bulk_insert(
        sa.table(
            "fund_tracks",
            sa.column("id", sa.String),
            sa.column("label_he", sa.String),
            sa.column("category", sa.String),
            sa.column("maslul", sa.String),
            sa.column("sort_order", sa.Integer),
        ),
        [
            {"id": tid, "label_he": label, "category": cat, "maslul": maslul, "sort_order": order}
            for (tid, label, cat, maslul, order) in SEED_TRACKS
        ],
    )


def downgrade() -> None:
    op.drop_table("fund_tracks")
