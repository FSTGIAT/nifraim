"""Merged ("full picture") comparison orchestration.

The comparison dashboard must always reflect ALL companies' latest נפרעים
data against the full active production — regardless of whether the files
arrived via the run-all batch (one merged נפרעים upload, company_source
"מאוחד"), a manual multi-file upload, or single-portal automation runs on
different days.

Selection rule per company (normalized via ``normalize_company``):
    the freshest source wins. The latest "מאוחד" upload is the baseline; a
    per-company upload NEWER than it replaces that company's rows inside the
    merged baseline (rows are excluded by ``receiving_company``) so amounts
    are never double-counted. A per-company upload OLDER than the merged
    baseline is skipped only when the baseline actually contains that
    company — otherwise it is still folded in (the batch may not cover
    every company the user uploads manually).

Records are then split per category (גמל/ביטוח) with
``commission_category_token`` — exactly like the batch's ``_compare_merged``
— and one comparison per non-empty category is computed, persisted and
debt-synced. ``compute_comparison`` itself is untouched.
"""

import logging
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.upload import FileUpload
from app.models.record import ClientRecord
from app.models.paying_company import PayingCompany
from app.models.commission_comparison import CommissionComparison
from app.services.comparison_service import compute_comparison
from app.services.portal_automation.aggregate import (
    commission_category_token,
    NIFRAIM_CATEGORY_GEMEL,
)
from app.utils.company_norm import normalize_company
from app.utils.sanitize import to_jsonable

logger = logging.getLogger(__name__)

MERGED_SOURCE = "מאוחד"


def _record_to_dict(r: ClientRecord) -> dict:
    return {
        c.key: getattr(r, c.key)
        for c in r.__table__.columns
        if c.key not in ("id", "user_id", "upload_id")
    }


def _company_key(name: str | None) -> str:
    return normalize_company(name) or ""


async def compute_merged_comparison(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    run_debt_sync: bool = True,
) -> dict:
    """Compute + persist the merged all-companies comparison per category.

    Returns::

        {
          "comparisons": {category: comparison_dict},
          "persisted": [categories],
          "skip_reason": None | "no_production" | "no_commission",
          "folded_upload_ids": [uuid, ...],
        }
    """
    out = {"comparisons": {}, "persisted": [], "skip_reason": None, "folded_upload_ids": []}

    # ── Production side: ALL active per-company production uploads ──────
    prod_q = await db.execute(
        select(FileUpload)
        .where(
            FileUpload.user_id == user_id,
            FileUpload.is_production.is_(True),
        )
        .order_by(FileUpload.uploaded_at)
    )
    prod_uploads = list(prod_q.scalars().all())
    if not prod_uploads:
        out["skip_reason"] = "no_production"
        return out
    prod_upload_ids = [u.id for u in prod_uploads]
    prod_anchor = prod_uploads[-1]  # newest — FK anchor + period label

    prod_recs_q = await db.execute(
        select(ClientRecord).where(
            ClientRecord.upload_id.in_(prod_upload_ids),
            ClientRecord.user_id == user_id,
        )
    )
    prod_dicts = [_record_to_dict(r) for r in prod_recs_q.scalars().all()]
    if not prod_dicts:
        out["skip_reason"] = "no_production"
        return out

    # ── Commission side: pick the freshest source per company ───────────
    comm_uploads_q = await db.execute(
        select(FileUpload)
        .where(
            FileUpload.user_id == user_id,
            FileUpload.file_category == "commission",
        )
        .order_by(FileUpload.uploaded_at.desc())
    )
    comm_uploads = list(comm_uploads_q.scalars().all())
    if not comm_uploads:
        out["skip_reason"] = "no_commission"
        return out

    merged_upload = next(
        (u for u in comm_uploads if (u.company_source or "").strip() == MERGED_SOURCE),
        None,
    )

    # Newest upload per company key (uploads are already newest-first).
    # Uploads without a recognizable company fall back to a per-filename key
    # so re-uploads of the same file don't double-count.
    # EVERY מאוחד-tagged upload is excluded here — not just the chosen
    # baseline — else a stale prior-month merged upload (batch filenames
    # embed the month, so they never replace each other) would be folded in
    # as a phantom "company" and double every figure.
    # Zero-record uploads carry no signal: they must never become a
    # company's "latest source" (that would erase the company's baseline
    # rows while contributing nothing).
    latest_by_company: dict[str, FileUpload] = {}
    for u in comm_uploads:
        if (u.company_source or "").strip() == MERGED_SOURCE:
            continue
        if not (u.record_count or 0):
            continue
        key = _company_key(u.company_source) or f"__file:{u.filename}"
        if key not in latest_by_company:
            latest_by_company[key] = u

    # Load the merged baseline rows and index the companies it covers.
    merged_records: list[dict] = []
    merged_companies: set[str] = set()
    if merged_upload is not None:
        merged_recs_q = await db.execute(
            select(ClientRecord).where(
                ClientRecord.upload_id == merged_upload.id,
                ClientRecord.user_id == user_id,
            )
        )
        merged_records = [_record_to_dict(r) for r in merged_recs_q.scalars().all()]
        merged_companies = {
            _company_key(r.get("receiving_company"))
            for r in merged_records
            if r.get("receiving_company")
        }

    # Decide which per-company uploads to fold in, and which companies must
    # be dropped from the merged baseline (their own upload is newer).
    selected_uploads: list[FileUpload] = []
    exclude_from_merged: set[str] = set()
    for key, u in latest_by_company.items():
        covered_by_merged = merged_upload is not None and key in merged_companies
        if covered_by_merged and (
            (merged_upload.uploaded_at or datetime.min) >= (u.uploaded_at or datetime.min)
        ):
            continue  # the merged baseline is fresher for this company
        selected_uploads.append(u)
        if covered_by_merged:
            exclude_from_merged.add(key)

    commission_dicts: list[dict] = []
    sources: set[str] = set()
    contributing: dict[str, set[uuid.UUID]] = {"gemel_hishtalmut": set(), "insurance": set()}

    def _cat_of(rec: dict) -> str:
        return (
            "gemel_hishtalmut"
            if commission_category_token(rec) == NIFRAIM_CATEGORY_GEMEL
            else "insurance"
        )

    if merged_records:
        for rec in merged_records:
            rc = rec.get("receiving_company")
            if rc and _company_key(rc) in exclude_from_merged:
                continue
            commission_dicts.append(rec)
            if rc:
                sources.add(rc)
            contributing[_cat_of(rec)].add(merged_upload.id)

    if selected_uploads:
        sel_recs_q = await db.execute(
            select(ClientRecord).where(
                ClientRecord.upload_id.in_([u.id for u in selected_uploads]),
                ClientRecord.user_id == user_id,
            )
        )
        upload_by_id = {u.id: u for u in selected_uploads}
        for r in sel_recs_q.scalars().all():
            rec = _record_to_dict(r)
            commission_dicts.append(rec)
            src = rec.get("receiving_company") or upload_by_id[r.upload_id].company_source
            if src:
                sources.add(src)
            contributing[_cat_of(rec)].add(r.upload_id)

    if not commission_dicts:
        out["skip_reason"] = "no_commission"
        return out

    out["folded_upload_ids"] = sorted(
        {uid for ids in contributing.values() for uid in ids}, key=str
    )

    # ── Split per category and compute (mirrors batch _compare_merged) ──
    paying_q = await db.execute(
        select(PayingCompany).where(PayingCompany.user_id == user_id)
    )
    paying_names = [p.company_name for p in paying_q.scalars().all()]

    by_cat: dict[str, list[dict]] = {"gemel_hishtalmut": [], "insurance": []}
    for rec in commission_dicts:
        by_cat[_cat_of(rec)].append(rec)

    for category, recs in by_cat.items():
        if not recs:
            continue
        try:
            comparison = compute_comparison(
                prod_dicts, recs, paying_names, category_override=category
            )
            cat_sources = sorted({
                r.get("receiving_company") for r in recs if r.get("receiving_company")
            }) or sorted(sources)
            comparison["commission_company_sources"] = cat_sources
            comparison["commission_company_source"] = (
                cat_sources[0] if len(cat_sources) == 1 else None
            )
            if prod_anchor.period_month is not None:
                comparison["period_month"] = prod_anchor.period_month.isoformat()
            comparison["period_files_count"] = len(contributing[category])

            row = CommissionComparison(
                user_id=user_id,
                category=category,
                production_upload_id=prod_anchor.id,
                summary_json=to_jsonable(comparison.get("summary") or {}),
                result_json=to_jsonable(comparison),
                commission_company_sources=to_jsonable(cat_sources),
            )
            db.add(row)
            await db.commit()
            out["comparisons"][category] = comparison
            out["persisted"].append(category)

            if run_debt_sync:
                try:
                    from app.services.debt_service import sync_debts

                    cat_upload_ids = contributing[category]
                    anchor_comm_id = None
                    if merged_upload is not None and merged_upload.id in cat_upload_ids:
                        anchor_comm_id = merged_upload.id
                    elif cat_upload_ids:
                        newest = max(
                            (u for u in comm_uploads if u.id in cat_upload_ids),
                            key=lambda u: u.uploaded_at or datetime.min,
                        )
                        anchor_comm_id = newest.id
                    await sync_debts(
                        db, user_id, comparison,
                        production_upload_id=prod_anchor.id,
                        commission_upload_id=anchor_comm_id,
                        category=category,
                    )
                    await db.commit()
                except Exception as de:
                    logger.warning("Merged debt sync (%s) failed: %s", category, de)
                    await db.rollback()
        except Exception as e:
            logger.warning("Merged compare (%s) failed: %s", category, e)
            await db.rollback()

    return out
