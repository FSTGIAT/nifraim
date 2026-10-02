"""Official monthly fund data — רשות שוק ההון's גמל-נט / פנסיה-נט / ביטוח-נט.

Published as open data on data.gov.il (CKAN datastore; services/fund_market).
GLOBAL market data, not per user: one row per (source, fund, report month).
Upsert-only — history is the point (follow a fund month over month).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Integer, String, UniqueConstraint
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
