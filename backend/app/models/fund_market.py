"""Official monthly fund data — רשות שוק ההון's גמל-נט / פנסיה-נט / ביטוח-נט.

Published as open data on data.gov.il (CKAN datastore; services/fund_market).
GLOBAL market data, not per user: one row per (source, fund, report month).
Upsert-only — history is the point (follow a fund month over month).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

SOURCES = ("gemel", "pension", "insurance")


class FundMarketMonthly(Base):
    __tablename__ = "fund_market_monthly"
    __table_args__ = (UniqueConstraint("source", "fund_id", "report_period", name="uq_fund_market_month"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(12), nullable=False, index=True)     # SOURCES
    fund_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)       # FUND_ID = קוד קופה/מסלול
    report_period: Mapped[int] = mapped_column(Integer, nullable=False, index=True) # YYYYMM
    fund_name: Mapped[str] = mapped_column(String(200), default="")
    classification: Mapped[str | None] = mapped_column(String(80), index=True)      # FUND_CLASSIFICATION
    specialization: Mapped[str | None] = mapped_column(String(80))
    sub_specialization: Mapped[str | None] = mapped_column(String(80))
    target_population: Mapped[str | None] = mapped_column(String(80))
    parent_company: Mapped[str | None] = mapped_column(String(200))
    managing_corporation: Mapped[str | None] = mapped_column(String(200))
    managing_corp_legal_id: Mapped[int | None] = mapped_column(BigInteger)
    # flows and size — ₪ millions as published
    total_assets: Mapped[float | None] = mapped_column(Float)
    deposits: Mapped[float | None] = mapped_column(Float)
    withdrawals: Mapped[float | None] = mapped_column(Float)
    internal_transfers: Mapped[float | None] = mapped_column(Float)
    net_monthly_deposits: Mapped[float | None] = mapped_column(Float)
    # fees and returns — PERCENT as published (0.53 = 0.53%)
    mgmt_fee: Mapped[float | None] = mapped_column(Float)
    deposit_fee: Mapped[float | None] = mapped_column(Float)
    monthly_yield: Mapped[float | None] = mapped_column(Float)
    ytd_yield: Mapped[float | None] = mapped_column(Float)
    yield_3y: Mapped[float | None] = mapped_column(Float)
    yield_5y: Mapped[float | None] = mapped_column(Float)
    avg_yield_3y: Mapped[float | None] = mapped_column(Float)
    avg_yield_5y: Mapped[float | None] = mapped_column(Float)
    std_dev: Mapped[float | None] = mapped_column(Float)
    alpha: Mapped[float | None] = mapped_column(Float)
    sharpe: Mapped[float | None] = mapped_column(Float)
    liquid_pct: Mapped[float | None] = mapped_column(Float)
    stock_exposure: Mapped[float | None] = mapped_column(Float)
    foreign_exposure: Mapped[float | None] = mapped_column(Float)
    fx_exposure: Mapped[float | None] = mapped_column(Float)
    actuarial_adjustment: Mapped[float | None] = mapped_column(Float)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PensyanetData(Base):
    """pensyanet.cma.gov.il XML export — what data.gov.il's פנסיה-נט resource lacks: asset
    allocation per track/fund, the fund-level actuarial balance and extra risk stats. GLOBAL, upsert-only (services/fund_market/pensyanet).

    Long format, one row per (report, level, entity, month, group, item):
      * asset reports  → grp = KVUTZAT_NECHASIM ("חלוקת נכסים ל-10 קבוצות ראשיות" …),
        item = asset type, amount in ₪ THOUSANDS, pct = share of the entity's assets;
      * wide reports   → grp = "", item_id = 0, the whole row in `data`.
    entity_id = FUND_ID of fund_market_monthly for level "track" (ID_MASLUL_RISHUY), the fund
    id (ID_KRN) for level "fund"."""
    __tablename__ = "pensyanet_data"
    __table_args__ = (UniqueConstraint("report", "level", "entity_id", "period", "grp", "item_id",
                                       name="uq_pensyanet_row"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    report: Mapped[str] = mapped_column(String(20), nullable=False, index=True)    # REPORTS key
    level: Mapped[str] = mapped_column(String(6), nullable=False)                  # fund | track
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    entity_name: Mapped[str | None] = mapped_column(String(200))
    period: Mapped[int] = mapped_column(Integer, nullable=False, index=True)       # YYYYMM
    grp: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    item_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    item_name: Mapped[str | None] = mapped_column(String(200))
    amount: Mapped[float | None] = mapped_column(Float)
    pct: Mapped[float | None] = mapped_column(Float)
    data: Mapped[dict | None] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
