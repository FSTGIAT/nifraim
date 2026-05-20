"""Workspace insights endpoints.

Hosts cross-cutting "what is happening across my last N months?" queries that
the radial-orbital launcher surfaces. Keeps `production.py` focused on
upload/compare and lets this file own the aggregated month-by-month views.

`GET /api/insights/monthly-commission?months=3`
    For each of the latest N production periods, returns:
      - expected_total (production × agreement rates)
      - actual_total   (sum of commission_paid for commission uploads whose
                        period_month == that month)
      - gap_total      (expected - actual, or None when no נפרעים file exists)

If no נפרעים file exists for a month, `commission_uploaded=False` and the
actual/gap fields are null — the UI uses that to render "טרם הועלה" rather
than misleadingly showing ₪0.
"""
from __future__ import annotations

import calendar
import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_paid_user as get_current_user
from app.database import get_db
from app.models.commission_rate import CommissionRate
from app.models.record import ClientRecord
from app.models.upload import FileUpload
from app.models.user import User
from app.services.comparison_service import _classify_product_type
from app.utils.company_norm import normalize_company

logger = logging.getLogger(__name__)
router = APIRouter()


_HEBREW_MONTHS = {
    1: "ינואר", 2: "פברואר", 3: "מרץ", 4: "אפריל",
    5: "מאי", 6: "יוני", 7: "יולי", 8: "אוגוסט",
    9: "ספטמבר", 10: "אוקטובר", 11: "נובמבר", 12: "דצמבר",
}


def _month_label(period: date) -> str:
    return f"{_HEBREW_MONTHS.get(period.month, period.month)} {period.year}"


def _calendar_window(months: int, anchor: date | None = None) -> list[date]:
    """Return the last `months` first-of-month dates starting from the month
    BEFORE `anchor` (or today). For anchor=2026-05-19 and months=3, returns
    [2026-04-01, 2026-03-01, 2026-02-01].

    Anchoring on the calendar (not on what's in the DB) is what surfaces empty
    months in the UI — the user explicitly wants to see e.g. February as a card
    with "טרם הועלה" rather than have it disappear because no file was uploaded.
    """
    today = anchor or date.today()
    # First-of-month for the month BEFORE today. We never include the current
    # month because Israeli insurers report ~30 days late — current-month data
    # is effectively never available, so showing it would always read as "no
    # data".
    if today.month == 1:
        first_prev = date(today.year - 1, 12, 1)
    else:
        first_prev = date(today.year, today.month - 1, 1)
    out: list[date] = []
    cur = first_prev
    for _ in range(months):
        out.append(cur)
        if cur.month == 1:
            cur = date(cur.year - 1, 12, 1)
        else:
            cur = date(cur.year, cur.month - 1, 1)
    return out


def _build_rate_picker(user_rates: list[CommissionRate]):
    """Mirror of production.py _pick_rate — kept inline so insights doesn't
    import a private helper. Uses normalize_company + product substring match
    + book+reward sum (per commission_rate_summing.md memory).
    """

    def pick(company_name: str, product_name: str | None = None) -> float:
        if not company_name or not user_rates:
            return 0.0
        target_canon = normalize_company(company_name)
        candidates: list[CommissionRate] = []
        if target_canon:
            candidates = [
                r for r in user_rates
                if r.company_name and normalize_company(r.company_name) == target_canon
            ]
        if not candidates:
            target_lc = company_name.strip().lstrip("ה").lower()
            candidates = [
                r for r in user_rates
                if r.company_name and (
                    target_lc in r.company_name.lstrip("ה").lower()
                    or r.company_name.lstrip("ה").lower() in target_lc
                )
            ]
        if not candidates:
            return 0.0

        prod_lc = (product_name or "").strip().lower()
        if prod_lc:
            product_matches = [
                r for r in candidates
                if r.product and (
                    prod_lc in r.product.lower() or r.product.lower() in prod_lc
                )
            ]
            if product_matches:
                totals = [r for r in product_matches
                          if (getattr(r, "rate_kind", None) or "").lower() == "total"]
                if totals:
                    return float(totals[0].rate)
                book = next((r for r in product_matches
                             if (getattr(r, "rate_kind", None) or "").lower() == "book"), None)
                reward = next((r for r in product_matches
                               if (getattr(r, "rate_kind", None) or "").lower() == "reward"), None)
                if book and reward:
                    return float(book.rate) + float(reward.rate)
                if book:
                    return float(book.rate)
                if reward:
                    return float(reward.rate)
                singles = [r for r in product_matches
                           if (getattr(r, "rate_kind", None) or "single").lower() == "single"]
                if singles:
                    return float(singles[0].rate)
                return float(product_matches[0].rate)

        defaults = [r for r in candidates if not r.product]
        if defaults:
            prio = [r for r in defaults
                    if (getattr(r, "rate_kind", None) or "single") in ("total", "single")]
            chosen = prio[0] if prio else defaults[0]
            return float(chosen.rate)

        prio = [r for r in candidates
                if (getattr(r, "rate_kind", None) or "single") in ("total", "single")]
        chosen = prio[0] if prio else candidates[0]
        return float(chosen.rate)

    return pick


@router.get("/monthly-commission")
async def monthly_commission(
    months: int = Query(default=3, ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Most recent N months that have production OR commission data.

    Earlier implementation anchored on the calendar window (today minus N
    months), which surfaced empty cards for months with no files at all.
    User feedback was that empty months read as visual noise — they want to
    see populated months only.

    Strict period match on both sides:
      - Production[M]  = the production upload whose period_month == M
      - Commission[M]  = commission uploads whose period_month == M

    Two states remain (the "empty" case is filtered out before return):
      - production_uploaded=true, commission_uploaded=false
                                  → expected_total set, actual_total=null
      - both uploaded              → all three numbers set
      - actual_total set, expected_total=null is also possible (commission
        arrived, production for that month not yet uploaded).
    """
    # Production file is the anchor — a month with only commission (no
    # production) wouldn't have a meaningful "expected" baseline to compare
    # against, so we skip it entirely. User explicitly asked: "if no
    # production file, not shown".
    periods_q = await db.execute(
        select(FileUpload.period_month)
        .where(
            FileUpload.user_id == user.id,
            FileUpload.file_category == "production",
            FileUpload.period_month.isnot(None),
        )
        .distinct()
        .order_by(desc(FileUpload.period_month))
        .limit(months)
    )
    periods: list[date] = [row[0] for row in periods_q.all() if row[0] is not None]
    if not periods:
        return {"months": []}

    # Load user's agreement rates once.
    rates_q = await db.execute(
        select(CommissionRate).where(CommissionRate.user_id == user.id)
    )
    user_rates = list(rates_q.scalars().all())
    pick_rate = _build_rate_picker(user_rates)

    # For each period, find the latest production upload for that period_month
    # (handles re-uploads — keep the latest by uploaded_at).
    prod_uploads_q = await db.execute(
        select(FileUpload)
        .where(
            FileUpload.user_id == user.id,
            FileUpload.file_category == "production",
            FileUpload.period_month.in_(periods),
        )
        .order_by(desc(FileUpload.uploaded_at))
    )
    latest_prod_by_period: dict[date, FileUpload] = {}
    for u in prod_uploads_q.scalars().all():
        if u.period_month not in latest_prod_by_period:
            latest_prod_by_period[u.period_month] = u

    # Pull production records for all those uploads in one query.
    prod_upload_ids = [u.id for u in latest_prod_by_period.values()]
    prod_records_by_upload: dict = {uid: [] for uid in prod_upload_ids}
    if prod_upload_ids:
        rec_q = await db.execute(
            select(
                ClientRecord.upload_id,
                ClientRecord.id_number,
                ClientRecord.receiving_company,
                ClientRecord.product_type,
                ClientRecord.product,
                ClientRecord.total_premium,
                ClientRecord.accumulation,
            ).where(
                ClientRecord.upload_id.in_(prod_upload_ids),
                ClientRecord.user_id == user.id,
            )
        )
        for upload_id, id_number, company, product_type, product_name, premium, accum in rec_q.all():
            prod_records_by_upload[upload_id].append({
                "id_number": id_number,
                "company": company,
                "product_type": product_type,
                "product": product_name,
                "premium": float(premium or 0),
                "accumulation": float(accum or 0),
            })

    # Commission uploads grouped by period_month (each period: list of uploads).
    comm_q = await db.execute(
        select(FileUpload)
        .where(
            FileUpload.user_id == user.id,
            FileUpload.file_category == "commission",
            FileUpload.period_month.in_(periods),
        )
    )
    comm_uploads_by_period: dict[date, list[FileUpload]] = {p: [] for p in periods}
    for u in comm_q.scalars().all():
        if u.period_month in comm_uploads_by_period:
            comm_uploads_by_period[u.period_month].append(u)

    # Sum commission_paid per (period, company) in one SQL group-by.
    all_comm_ids = [u.id for ulist in comm_uploads_by_period.values() for u in ulist]
    actual_per_upload: dict = {}
    if all_comm_ids:
        sums_q = await db.execute(
            select(
                ClientRecord.upload_id,
                func.coalesce(func.sum(ClientRecord.commission_paid), 0).label("total"),
            )
            .where(
                ClientRecord.upload_id.in_(all_comm_ids),
                ClientRecord.user_id == user.id,
            )
            .group_by(ClientRecord.upload_id)
        )
        for upload_id, total in sums_q.all():
            actual_per_upload[upload_id] = float(total or 0)

    out_months = []
    for period in periods:
        prod_upload = latest_prod_by_period.get(period)
        production_uploaded = prod_upload is not None
        comm_uploads = comm_uploads_by_period.get(period, [])
        commission_uploaded = len(comm_uploads) > 0

        # Expected per company
        expected_by_company: dict[str, float] = {}
        expected_total = 0.0
        if prod_upload:
            for rec in prod_records_by_upload.get(prod_upload.id, []):
                company = rec["company"]
                if not company:
                    continue
                cat = _classify_product_type(rec["product_type"]) or ""
                rate = pick_rate(company, rec["product"]) or pick_rate(company, rec["product_type"])
                if rate <= 0:
                    continue
                if cat == "gemel_hishtalmut":
                    base = rec["accumulation"]
                    if base <= 0:
                        continue
                    exp = base * rate / 12.0
                else:
                    base = rec["premium"]
                    if base <= 0:
                        continue
                    exp = base * rate
                if exp <= 0:
                    continue
                expected_by_company[company] = expected_by_company.get(company, 0.0) + exp
                expected_total += exp

        # Actual per company — use upload's company_source as the company name
        actual_by_company: dict[str, float] = {}
        actual_total = 0.0
        if commission_uploaded:
            for u in comm_uploads:
                company_key = u.company_source or u.filename or "—"
                total = actual_per_upload.get(u.id, 0.0)
                actual_by_company[company_key] = actual_by_company.get(company_key, 0.0) + total
                actual_total += total

        # Merge into per-company rows. Pair on company name, fall back to
        # showing expected-only or actual-only rows when names don't match
        # (e.g. production says "הפניקס" and commission upload's company_source
        # is "פניקס") — normalize_company handles the canonical match.
        company_canon_map: dict[str, str] = {}  # canonical → display
        canon_buckets: dict[str, dict] = {}

        def _bucket(company_display: str):
            canon = normalize_company(company_display) or company_display
            if canon not in canon_buckets:
                canon_buckets[canon] = {"company": company_display, "expected": 0.0, "actual": 0.0}
                company_canon_map[canon] = company_display
            return canon_buckets[canon]

        for co, val in expected_by_company.items():
            b = _bucket(co)
            b["expected"] += val
        for co, val in actual_by_company.items():
            b = _bucket(co)
            b["actual"] += val

        by_company = []
        for canon, b in canon_buckets.items():
            exp = round(b["expected"], 2)
            act = round(b["actual"], 2) if commission_uploaded else None
            gap = round(exp - (act or 0), 2) if commission_uploaded else None
            by_company.append({
                "company": b["company"],
                "expected": exp,
                "actual": act,
                "gap": gap,
            })
        by_company.sort(key=lambda r: -(r["expected"] or 0))

        # When production isn't uploaded for this month, expected is also
        # null — there's nothing to compute it from. The UI keys off these
        # nulls to render the "טרם הועלה" empty state instead of "₪0".
        expected_out = round(expected_total, 2) if production_uploaded else None
        actual_out = round(actual_total, 2) if commission_uploaded else None
        gap_out = None
        if production_uploaded and commission_uploaded:
            gap_out = round(expected_total - actual_total, 2)

        out_months.append({
            "period_month": period.isoformat(),
            "label": _month_label(period),
            "production_uploaded": production_uploaded,
            "commission_uploaded": commission_uploaded,
            "expected_total": expected_out,
            "actual_total": actual_out,
            "gap_total": gap_out,
            "by_company": by_company,
        })

    # Newest first.
    out_months.sort(key=lambda m: m["period_month"], reverse=True)
    return {"months": out_months}
