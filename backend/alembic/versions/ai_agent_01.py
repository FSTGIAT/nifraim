"""Nifra AI v2: users.ai_data_version, ai_memories, ai_intent_log, fund_market_monthly.

Revision ID: ai_agent_01
Revises: track_split_01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "ai_agent_01"
down_revision = "track_split_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("ai_data_version", sa.Integer, nullable=False, server_default="0"))
    op.create_table(
        "ai_memories",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("source", sa.String(16), nullable=True),
        sa.Column("uses", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("last_used", sa.DateTime, nullable=True),
    )
    op.create_table(
        "ai_intent_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("intent", sa.String(48), nullable=True),
        sa.Column("lane", sa.String(8), nullable=False),
        sa.Column("ms", sa.Integer, nullable=True),
        sa.Column("question", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True, index=True),
    )
    op.create_table(
        "fund_market_monthly",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("source", sa.String(12), nullable=False, index=True),
        sa.Column("fund_id", sa.Integer, nullable=False, index=True),
        sa.Column("report_period", sa.Integer, nullable=False, index=True),
        sa.Column("fund_name", sa.String(200)),
        sa.Column("classification", sa.String(80), index=True),
        sa.Column("specialization", sa.String(80)),
        sa.Column("sub_specialization", sa.String(80)),
        sa.Column("target_population", sa.String(80)),
        sa.Column("parent_company", sa.String(200)),
        sa.Column("managing_corporation", sa.String(200)),
        sa.Column("managing_corp_legal_id", sa.BigInteger),
        *[sa.Column(c, sa.Float) for c in (
            "total_assets", "deposits", "withdrawals", "internal_transfers", "net_monthly_deposits",
            "mgmt_fee", "deposit_fee", "monthly_yield", "ytd_yield", "yield_3y", "yield_5y",
            "avg_yield_3y", "avg_yield_5y", "std_dev", "alpha", "sharpe", "liquid_pct",
            "stock_exposure", "foreign_exposure", "fx_exposure", "actuarial_adjustment")],
        sa.Column("fetched_at", sa.DateTime),
        sa.UniqueConstraint("source", "fund_id", "report_period", name="uq_fund_market_month"),
    )


def downgrade() -> None:
    op.drop_table("fund_market_monthly")
    op.drop_table("ai_intent_log")
    op.drop_table("ai_memories")
    op.drop_column("users", "ai_data_version")
