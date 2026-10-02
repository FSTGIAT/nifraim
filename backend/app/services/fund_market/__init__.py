"""Official monthly fund data: רשות שוק ההון's גמל-נט / פנסיה-נט / ביטוח-נט.

The old gemelnet.cma.gov.il ASPX views are gone (the page now serves a gov.il
"האתר המבוקש אינו נמצא" error). The SAME data is published as open data on
data.gov.il, through the CKAN datastore API: JSON, no auth, no scraping,
one row per fund per month, keyed by FUND_ID (קוד קופה / מסלול). Researched
2026-10-02; the latest REPORT_PERIOD then was 202608, so it lags 1–2 months.

`sync()` upserts into `fund_market_monthly` and never deletes, because the
month-over-month history is what we need. mygemel.net (services/fund_scraper)
stays only as the ticker's fallback.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

import httpx
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fund_market import FundMarketMonthly

logger = logging.getLogger(__name__)

API = "https://data.gov.il/api/3/action/datastore_search"
PAGE = 1000
TIMEOUT_S = 60

# source -> resources, oldest first. "current" = 2024→today, the only one that grows.
RESOURCES: dict[str, dict[str, str]] = {
    "gemel": {"2023": "2016d770-f094-4a2e-983e-797c26479720", "current": "a30dcbea-a1d2-482c-ae29-8f781f5025fb",
              "1999-2022": "91c849ed-ddc4-472b-bd09-0f5486cea35c"},
    "pension": {"2023": "4694d5a7-5284-4f3d-a2cb-5887f43fb55e", "current": "6d47d6b5-cb08-488b-b333-f1e717b1e1bd",
                "1999-2022": "a66926f3-e396-4984-a4db-75486751c2f7"},
    "insurance": {"2023": "672090ba-7893-4496-a07c-dc7e822cbf18", "current": "c6c62cc7-fe02-4b18-8f3e-813abfbb4647",
                  "1999-2022": "584e6b69-174f-46c9-b8db-03925b4c68c6"},
}

# API column -> our column
FIELD_MAP = {
    "FUND_NAME": "fund_name", "FUND_CLASSIFICATION": "classification",
    "SPECIALIZATION": "specialization", "SUB_SPECIALIZATION": "sub_specialization",
    "TARGET_POPULATION": "target_population", "PARENT_COMPANY_NAME": "parent_company",
    "MANAGING_CORPORATION": "managing_corporation",
    "TOTAL_ASSETS": "total_assets", "DEPOSITS": "deposits", "WITHDRAWLS": "withdrawals",
    "INTERNAL_TRANSFERS": "internal_transfers", "NET_MONTHLY_DEPOSITS": "net_monthly_deposits",
    "AVG_ANNUAL_MANAGEMENT_FEE": "mgmt_fee", "AVG_DEPOSIT_FEE": "deposit_fee",
    "MONTHLY_YIELD": "monthly_yield", "YEAR_TO_DATE_YIELD": "ytd_yield",
    "YIELD_TRAILING_3_YRS": "yield_3y", "YIELD_TRAILING_5_YRS": "yield_5y",
    "AVG_ANNUAL_YIELD_TRAILING_3YRS": "avg_yield_3y", "AVG_ANNUAL_YIELD_TRAILING_5YRS": "avg_yield_5y",
    "STANDARD_DEVIATION": "std_dev", "ALPHA": "alpha", "SHARPE_RATIO": "sharpe",
    "LIQUID_ASSETS_PERCENT": "liquid_pct", "STOCK_MARKET_EXPOSURE": "stock_exposure",
    "FOREIGN_EXPOSURE": "foreign_exposure", "FOREIGN_CURRENCY_EXPOSURE": "fx_exposure",
    "ACTUARIAL_ADJUSTMENT": "actuarial_adjustment",
}
_STR = {"fund_name": 200, "classification": 80, "specialization": 80, "sub_specialization": 80,
        "target_population": 80, "parent_company": 200, "managing_corporation": 200}


def to_row(source: str, rec: dict) -> dict | None:
    try:
        fund_id = int(rec["FUND_ID"])
        period = int(rec["REPORT_PERIOD"])
    except (KeyError, TypeError, ValueError):
        return None
    row = {"source": source, "fund_id": fund_id, "report_period": period, "fetched_at": datetime.utcnow()}
    for k, col in FIELD_MAP.items():
        v = rec.get(k)
        if col in _STR:
            row[col] = (str(v).strip()[: _STR[col]] if v not in (None, "") else None)
        else:
            try:
                row[col] = float(v) if v not in (None, "") else None
            except (TypeError, ValueError):
                row[col] = None
    legal = rec.get("MANAGING_CORPORATION_LEGAL_ID") or rec.get("PARENT_COMPANY_LEGAL_ID")
    try:
        row["managing_corp_legal_id"] = int(legal) if legal not in (None, "") else None
    except (TypeError, ValueError):
        row["managing_corp_legal_id"] = None
    if not row.get("managing_corporation"):
        row["managing_corporation"] = row.get("parent_company")
    return row


async def fetch(client: httpx.AsyncClient, resource_id: str, *, period_from: int | None = None) -> list[dict]:
    """Every record of one resource (optionally only periods >= period_from)."""
    out: list[dict] = []
    offset = 0
    while True:
        params = {"resource_id": resource_id, "limit": PAGE, "offset": offset, "sort": "_id asc"}
        r = await client.get(API, params=params)
        r.raise_for_status()
        body = r.json()
        if not body.get("success"):
            raise RuntimeError(f"datastore_search failed: {body.get('error')}")
        recs = body["result"]["records"]
        out += [x for x in recs if period_from is None or int(x.get("REPORT_PERIOD") or 0) >= period_from]
        offset += len(recs)
        if not recs or offset >= int(body["result"].get("total") or 0):
            return out


async def _upsert(db: AsyncSession, rows: list[dict]) -> int:
    n = 0
    for i in range(0, len(rows), 500):
        chunk = rows[i: i + 500]
        stmt = insert(FundMarketMonthly).values(chunk)
        cols = {c: getattr(stmt.excluded, c) for c in chunk[0] if c not in ("source", "fund_id", "report_period")}
        await db.execute(stmt.on_conflict_do_update(constraint="uq_fund_market_month", set_=cols))
        n += len(chunk)
    await db.commit()
    return n


async def latest_period(db: AsyncSession, source: str | None = None) -> int | None:
    q = select(func.max(FundMarketMonthly.report_period))
    if source:
        q = q.where(FundMarketMonthly.source == source)
    return (await db.execute(q)).scalar_one_or_none()


async def sync(db: AsyncSession, *, backfill: bool = False, include_pre_2023: bool = False) -> dict:
    """Pull the official data. Normal run: the "current" resource of each source,
    from (our latest period − 2) on — a month can be republished with fixes.
    `backfill`: 2023 + current from scratch; `include_pre_2023` adds 1999-2022."""
    stats: dict[str, int] = {}
    async with httpx.AsyncClient(timeout=TIMEOUT_S, headers={"User-Agent": "NifraimBot/1.0"}) as client:
        for source, res in RESOURCES.items():
            keys = ["current"]
            period_from = None
            if backfill:
                keys = (["1999-2022"] if include_pre_2023 else []) + ["2023", "current"]
            else:
                last = await latest_period(db, source)
                if last:
                    y, m = divmod(last, 100)
                    m -= 2
                    if m < 1:
                        y, m = y - 1, m + 12
                    period_from = y * 100 + m
                else:
                    keys = ["2023", "current"]   # first run ever: backfill from 2023
            rows: list[dict] = []
            for k in keys:
                try:
                    recs = await fetch(client, res[k], period_from=period_from)
                except Exception as e:  # noqa: BLE001 — keep the last good month
                    logger.warning("fund_market: %s/%s fetch failed: %s", source, k, e)
                    continue
                rows += [r for r in (to_row(source, x) for x in recs) if r]
            # same (fund, period) can appear in two resources at a boundary — last wins
            dedup = {(r["fund_id"], r["report_period"]): r for r in rows}
            stats[source] = await _upsert(db, list(dedup.values())) if dedup else 0
    logger.info("fund_market sync: %s", json.dumps(stats))
    return stats
