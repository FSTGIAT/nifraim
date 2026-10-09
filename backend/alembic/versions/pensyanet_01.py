"""pensyanet_data: פנסיה-נט XML export (asset allocation, yield split, risk stats).

Revision ID: pensyanet_01
Revises: maslaka_gateway_01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "pensyanet_01"
down_revision = "maslaka_gateway_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pensyanet_data",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("report", sa.String(20), nullable=False, index=True),
        sa.Column("level", sa.String(6), nullable=False),
        sa.Column("entity_id", sa.Integer, nullable=False, index=True),
        sa.Column("entity_name", sa.String(200)),
        sa.Column("period", sa.Integer, nullable=False, index=True),
        sa.Column("grp", sa.String(80), nullable=False, server_default=""),
        sa.Column("item_id", sa.Integer, nullable=False, server_default="0"),
        sa.Column("item_name", sa.String(200)),
        sa.Column("amount", sa.Float),
        sa.Column("pct", sa.Float),
        sa.Column("data", JSONB),
        sa.Column("fetched_at", sa.DateTime),
        sa.UniqueConstraint("report", "level", "entity_id", "period", "grp", "item_id", name="uq_pensyanet_row"),
    )
    # data.gov.il serves "S&P" as "S1;P" (services/fund_market.fix_name fixes new rows)
    op.execute("UPDATE fund_market_monthly SET fund_name = regexp_replace(fund_name, '([Ss])1;([Pp])', '\\1&\\2', 'g') "
               "WHERE fund_name ~ '[Ss]1;[Pp]'")


def downgrade() -> None:
    op.drop_table("pensyanet_data")
