import hashlib
import uuid
from collections import defaultdict

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.upload import FileUpload
from app.models.record import ClientRecord
from app.models.production_summary import ProductionSummary
from app.schemas.upload import ProductionFileInfo, ProductionAnalytics, ProductionCompareResponse
from app.api.deps import get_paid_user as get_current_user
from app.services.parser_service import parse_excel, CategoryMismatchError
from app.services.portal_service import create_snapshots_for_upload
from app.services.comparison_service import (
    _classify_product_type, _get_commission, _normalize_id,
    _GEMEL_KEYWORDS, _INSURANCE_KEYWORDS,
)
from app.services.rate_select import (
    accumulation_based,
    expected_rate,
    select_rate,
    make_pick_rate,
    compute_expected_commission,
)
from app.utils.company_norm import company_stem
from app.utils.product_taxonomy import classify_product
from app.services.commission_basis import detect_vat_basis, ex_vat_commission
from app.models.commission_rate import CommissionRate
from app.utils.sanitize import sanitize_record

router = APIRouter()


async def _create_snapshots_bg(user_id, upload_id):
    """Background task to create portal snapshots after production upload."""
    from app.database import async_session
    async with async_session() as db:
        await create_snapshots_for_upload(db, user_id, upload_id)


async def _compute_summary_bg(user_id, upload_id):
    """Background task to compute production summary after upload."""
    from app.database import async_session
    from app.services.summary_service import compute_production_summary
    async with async_session() as db:
        await compute_production_summary(db, user_id, upload_id)


def _compute_data_fingerprint(records: list[dict]) -> str:
    """Compute an MD5 fingerprint from parsed record data to detect duplicates."""
    rows = sorted(
        (
            r.get("id_number") or "",
            str(r.get("total_premium") or 0),
            str(r.get("accumulation") or 0),
            r.get("receiving_company") or "",
        )
        for r in records
    )
    return hashlib.md5(str(rows).encode()).hexdigest()


async def _get_production_upload(db: AsyncSession, user_id: uuid.UUID) -> FileUpload | None:
    """Returns the latest active production upload. Kept for backwards
    compatibility — most callers should use _get_production_upload_ids()
    instead since multiple companies' production files can be active
    simultaneously (unified monthly view)."""
    result = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user_id,
            FileUpload.is_production == True,
        )
        .order_by(FileUpload.uploaded_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_production_upload_ids(db: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    """Returns ALL active production upload IDs for the user — one per
    company. The dashboard aggregates records across these so Migdal +
    Menora + ... appear as one unified monthly production."""
    result = await db.execute(
        select(FileUpload.id).where(
            FileUpload.user_id == user_id,
            FileUpload.is_production == True,
        )
    )
    return [row[0] for row in result.all()]


async def _get_all_production_uploads(db: AsyncSession, user_id: uuid.UUID) -> list[FileUpload]:
    """All active production uploads (one per company). Used by /current
    and aggregation endpoints to render unified info."""
    result = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user_id,
            FileUpload.is_production == True,
        )
        .order_by(FileUpload.uploaded_at.desc())
    )
    return list(result.scalars().all())


def _display_name(first, last, id_number) -> str:
    """A person's name, or their ID when the file didn't carry one.

    Some parsers write "0" (or a stray separator) into the name columns rather
    than leaving them empty, so a plain `first or last or id` still yields a row
    labelled "0" — live, one client appeared in the movers chart as literally
    `0`. Anything with no letters or digits in it is not a name.
    """
    name = f"{first or ''} {last or ''}".strip()
    if name and any(ch.isalpha() for ch in name):
        return name
    return str(id_number or "").strip() or name


# Why one production record contributes nothing to expected commission.
# Four causes, because each implies a DIFFERENT fix for the agent; the previous
# two-bucket split reported one misleading sentence for all of them (QA #7).
UNCOVERED_BUCKETS = ("no_company", "no_rate", "risk_no_premium", "no_base")


def _uncovered_bucket(rate: float, route: str, is_accum: bool,
                      premium: float, accum: float, expected: float) -> str | None:
    """The bucket this record falls in, or None when it contributes.

      no_company      the insurer matched no agreement row at all → upload one.
                      `select_rate` signals this with route "none". Live: מגדל
                      has zero rate rows, yet the UI said "אין שיעור בהסכם",
                      which reads as "the agreement is incomplete".
      no_rate         an agreement exists but covers no matching product.
      risk_no_premium the row HAS accumulation, but a risk product is priced off
                      premium and the file carries none. Live: Phoenix's 316
                      rows hold ₪51.2M of צבירה and were reported as having
                      none — the agent went looking for data that was present.
      no_base         genuinely nothing to price off. Live: Harel's ר.ת. vault
                      reports leave both money columns empty on all 1,672 rows.
    """
    if rate <= 0:
        return "no_company" if route == "none" else "no_rate"
    if not is_accum and premium <= 0:
        return "risk_no_premium" if accum > 0 else "no_base"
    if expected <= 0:
        return "risk_no_premium" if (accum > 0 and premium <= 0) else "no_base"
    return None



# ---------------------------------------------------------------------------
# Unified-export selection + grouping (QA 2026-09-09)
#
# Both merged workbooks used to build their `סיכום` and per-company sheets by
# iterating FileUpload ROWS, while the `מאוחד` sheet held the merged upload's
# RECORDS. Two different row sets in one workbook: live, the נפרעים file showed
# 11 companies in `מאוחד` but only 4 in `סיכום`, and its `סה״כ` was
# 4299 = 2678 + 1621 — the merged total added to each company again.
#
# Everything below derives from ONE row set, grouped on `company_stem`, so the
# summary can no longer disagree with the sheets.
# ---------------------------------------------------------------------------


def _select_unified_uploads(uploads: list[FileUpload]) -> list[FileUpload]:
    """Pick the uploads whose records make up "this month's" merged view.

    A `מאוחד` upload is DERIVED: the batch folds the per-company uploads into
    it and then DELETES them (`batch_runner._delete_uploads`). So any
    per-company upload still sitting beside a merged one is either

      * OLDER than the merge  → a stale leftover from an earlier run. Its rows
        are either already inside the merge (double-count) or belong to a
        month that has since been superseded. Live on kikohib, four such
        leftovers (מור 05, מנורה 06, הראל 05, מגדל 05) were being reported as
        the current month while the merge itself held July.
      * NEWER than the merge  → a standalone run performed after the batch.
        Its rows are genuinely not in the merge yet and must be kept.

    `uploaded_at` answers this exactly and needs no `period_month`. That
    matters: the previous code carried a comment explaining that period
    detection is untrustworthy here (portal נפרעים filenames carry no month,
    so detection lands on record-data months — two fresh Harel files detected
    as 2026-02/03 while a stale merge held 2026-05). Selecting on upload time
    sidesteps that trap instead of re-entering it.

    Also replaces the 24-hour "harvest window", which silently dropped one of
    two Harel account files whenever the logins ran more than a day apart
    (live: 70 rows kept, 139 rows lost).
    """
    if not uploads:
        return []
    merged = [u for u in uploads if (u.company_source or "") == "מאוחד"]
    if not merged:
        # No merge yet — every per-company upload stands on its own. Dedupe by
        # filename (the upload replace-key), newest wins.
        seen: dict[str, FileUpload] = {}
        for u in sorted(uploads, key=lambda u: u.uploaded_at, reverse=True):
            seen.setdefault(u.filename, u)
        return list(seen.values())

    newest_merge = max(merged, key=lambda u: u.uploaded_at)
    picked = [newest_merge]
    seen = {newest_merge.filename: newest_merge}
    for u in sorted(uploads, key=lambda u: u.uploaded_at, reverse=True):
        if u is newest_merge or (u.company_source or "") == "מאוחד":
            continue
        if u.uploaded_at <= newest_merge.uploaded_at:
            continue  # stale leftover — already folded in, or superseded
        if u.filename not in seen:
            seen[u.filename] = u
            picked.append(u)
    return picked


async def _configured_company_stems(db: AsyncSession, user_id: uuid.UUID) -> dict[str, dict]:
    """`{company_stem: {"label", "production", "commission"}}` for every portal
    the agent has an ACTIVE credential for.

    The QA requirement is that every configured company is always visible —
    a company that downloaded nothing, or whose file failed to parse, must
    show up at zero WITH a reason rather than silently vanishing. Enumerating
    credentials (rather than the batch result) is what makes that hold on the
    export path too, which runs on demand and may run before any batch.

    Several portal kinds share one company (phoenix / phoenix_sfe /
    phoenix_terminal → הפניקס), so the label is derived from PORTAL_META's
    company field and collapsed through `company_stem` — the same key the rows
    are grouped on. No second hardcoded table to drift.

    `production` / `commission` say whether ANY of that company's configured
    portals actually publishes that report, read off PORTAL_META's category.
    This is what stops the production export from claiming מור "returned no
    data" when מור's portal has no production report to return: it is a
    gemel house, its portal serves נפרעים only.
    """
    from app.models.portal_credential import PortalCredential
    from app.services.portal_automation.companies import PORTAL_META, PORTAL_LABELS

    result = await db.execute(
        select(PortalCredential.portal_kind).where(
            PortalCredential.user_id == user_id,
            PortalCredential.is_active.is_(True),
        ).distinct()
    )
    stems: dict[str, dict] = {}
    for (kind,) in result.all():
        meta = PORTAL_META.get(kind)
        if meta:
            brand, category, _url = meta
        else:
            brand = PORTAL_LABELS.get(kind, kind).split("—")[0].strip()
            category = ""
        stem = company_stem(brand)
        if not stem:
            continue
        entry = stems.setdefault(
            stem, {"label": brand, "production": False, "commission": False}
        )
        if category.startswith("פרודוקציה"):
            entry["production"] = True
        elif category.startswith("נפרעים"):
            entry["commission"] = True
    return stems


async def _last_run_reason_by_stem(db: AsyncSession, user_id: uuid.UUID) -> dict[str, str]:
    """`{company_stem: why this company has no data}` from the latest batch.

    The reasons already exist — the batch collects them into `partial_notes`
    and concatenates them into `batch.error_message[:2000]`. That string is
    unreadable and unqueryable, so a company that failed showed up in the
    merged workbook as a bare zero with no explanation. Live examples from
    kikohib's 2026-08-30 run, all of which SHOULD reach the agent per company:

      הראל   — "לא הצלחנו להוריד אקסל נפרעים מאף חשבון בהראל (2 חשבונות)"
      כלל    — "תיבת .exe התקבלה אך לא חולצה"
      אלטשולר — "הפורמט לא זוהה (unknown) — לא ייכלל בקבצים המאוחדים"

    Reading `portal_runs` back per credential gives the same information keyed
    by company, with no schema change and no string parsing.
    """
    from app.models.portal_credential import PortalCredential
    from app.models.portal_run import PortalRun
    from app.models.portal_run_batch import PortalRunBatch
    from app.services.portal_automation.companies import PORTAL_META, PORTAL_LABELS

    batch_q = await db.execute(
        select(PortalRunBatch.id)
        .where(PortalRunBatch.user_id == user_id)
        .order_by(PortalRunBatch.started_at.desc())
        .limit(1)
    )
    batch_id = batch_q.scalar_one_or_none()
    if batch_id is None:
        return {}

    runs_q = await db.execute(
        select(PortalCredential.portal_kind, PortalRun.status, PortalRun.error_message)
        .join(PortalCredential, PortalCredential.id == PortalRun.credential_id)
        .where(PortalRun.batch_id == batch_id)
    )
    reasons: dict[str, str] = {}
    for kind, status, error in runs_q.all():
        if not error and status in ("success", None):
            continue
        meta = PORTAL_META.get(kind)
        brand = meta[0] if meta else PORTAL_LABELS.get(kind, kind).split("—")[0].strip()
        stem = company_stem(brand)
        if not stem:
            continue
        msg = (error or f"ההרצה הסתיימה בסטטוס {status}").strip()
        # Strip the batch's own "partially completed" prefix — the caller
        # already knows this company has no rows.
        for pref in ("הושלם חלקית:", "הושלם חלקית -"):
            if msg.startswith(pref):
                msg = msg[len(pref):].strip()
        msg = " ".join(msg.split())[:220]
        # A hard failure explains more than a success-with-losses; keep it.
        if stem not in reasons or status not in ("success", None):
            reasons[stem] = msg
    return reasons



def _summary_from_rows(
    df, value_cols: dict[str, str], configured: dict[str, dict], kind: str,
    reasons: dict[str, str] | None = None,
):
    """Build the `סיכום` frame and the per-company sheets from ONE row set.

    `value_cols` maps summary column name → dataframe column to sum.
    Returns `(summary_rows, [(sheet_name, sheet_df), ...])`.

    `סה״כ` is the sum of the company groups, so it cannot double-count the way
    the per-upload construction did.
    """
    import pandas as pd

    sheets: list[tuple[str, "pd.DataFrame"]] = []
    rows: list[dict] = []
    covered: set[str] = set()

    if not df.empty:
        for stem, group in df.groupby("_stem", sort=False):
            if not stem:
                continue
            covered.add(stem)
            periods = sorted({p for p in group["_period"].tolist() if p})
            entry = {
                "חברה": stem,
                "מספר רשומות": len(group),
                **{
                    label: float(group[col].fillna(0).sum())
                    for label, col in value_cols.items()
                },
                # A company reporting a different month than the file's headline
                # must be VISIBLE, not relabelled — that is QA #5.
                "תקופה": ", ".join(periods),
                "קובץ מקור": ", ".join(sorted(set(group["_source"].tolist()))),
            }
            rows.append(entry)
            sheets.append((stem, group.drop(columns=["_stem", "_period", "_source"])))

    # Configured-but-absent companies: zero row + reason, never omitted.
    #
    # The reason has to distinguish two very different situations, or it
    # misleads. "No data this run" means something went wrong and is worth
    # chasing. But מור/מיטב/אלטשולר/ילין/אנליסט/הכשרה are gemel houses whose
    # portals publish נפרעים ONLY — there is no production report to download,
    # so a production row for them is not a failure and must not read like one.
    report = "פרודוקציה" if kind == "production" else "נפרעים"
    for stem, meta in sorted(configured.items()):
        if stem in covered:
            continue
        if not meta.get(kind):
            reason = f"הפורטל אינו מספק דוח {report}"
        elif (reasons or {}).get(stem):
            # The real, per-company failure from the last run — far more use
            # than "no data": it names the ACTION (re-run, fix the parser,
            # extract the .exe box).
            reason = reasons[stem]
        else:
            reason = "לא התקבלו נתונים בהרצה האחרונה"
        rows.append({
            "חברה": stem,
            "מספר רשומות": 0,
            **{label_: 0.0 for label_ in value_cols},
            "תקופה": "",
            "קובץ מקור": reason,
        })

    rows.sort(key=lambda r: (-r["מספר רשומות"], r["חברה"]))
    total = {
        "חברה": "סה״כ",
        "מספר רשומות": int(sum(r["מספר רשומות"] for r in rows)),
        **{
            label: float(sum(r[label] for r in rows))
            for label in value_cols
        },
        "תקופה": "",
        "קובץ מקור": f"{len([r for r in rows if r['מספר רשומות']])} חברות עם נתונים "
                     f"מתוך {len(rows)}",
    }
    return rows + [total], sheets


def _excel_sheet_name(name: str, taken: set[str]) -> str:
    r"""Excel sheet names: <=31 chars, no `:\/?*[]`, unique."""
    safe = (name or "—")[:31]
    for bad in r":\/?*[]":
        safe = safe.replace(bad, " ")
    safe = safe.strip() or "—"
    base, i = safe, 2
    while safe in taken:
        suffix = f" ({i})"
        safe = base[: 31 - len(suffix)] + suffix
        i += 1
    taken.add(safe)
    return safe


async def _get_companies_for_upload(db: AsyncSession, upload_id: uuid.UUID) -> list[str]:
    result = await db.execute(
        select(ClientRecord.receiving_company)
        .where(
            ClientRecord.upload_id == upload_id,
            ClientRecord.receiving_company.isnot(None),
        )
        .distinct()
    )
    companies = [r[0] for r in result.all() if r[0] and r[0] not in ("nan", "None")]
    return sorted(companies)


@router.post("/upload", response_model=ProductionFileInfo)
async def upload_production(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    password: str = Form(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload & persist production file, replacing previous."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="לא סופק קובץ")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("xlsx", "xls"):
        raise HTTPException(status_code=400, detail="רק קבצי xlsx/xls נתמכים")

    content = await file.read()

    try:
        result = parse_excel(content, file.filename, password, expected_category="production")
    except CategoryMismatchError as e:
        # Surface the parser's Hebrew message verbatim — it tells the user
        # which tab the file actually belongs in.
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"שגיאה בפענוח הקובץ: {str(e)}")

    # Find prior active production FROM THE SAME COMPANY only. Different
    # companies' production files coexist as is_production=True so the
    # dashboard merges them into one monthly view.
    new_company = result.get("company_source")
    same_company_q = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user.id,
            FileUpload.is_production.is_(True),
            FileUpload.company_source == new_company,
        )
    )
    old_prod = same_company_q.scalar_one_or_none()
    if old_prod:
        # Build a fingerprint from the new parsed data
        new_fingerprint = _compute_data_fingerprint(result["records"])
        # Build fingerprint from existing records
        old_records_q = await db.execute(
            select(
                ClientRecord.id_number,
                ClientRecord.total_premium,
                ClientRecord.accumulation,
                ClientRecord.receiving_company,
            )
            .where(ClientRecord.upload_id == old_prod.id)
            .order_by(ClientRecord.id_number)
        )
        old_rows = old_records_q.all()
        old_fingerprint = hashlib.md5(
            str(sorted(
                (r[0] or "", str(r[1] or 0), str(r[2] or 0), r[3] or "")
                for r in old_rows
            )).encode()
        ).hexdigest()

        if new_fingerprint == old_fingerprint:
            raise HTTPException(
                status_code=400,
                detail="הקובץ מכיל נתונים זהים לקובץ הפרודוקציה הנוכחי — לא בוצע שינוי"
            )

        # Deactivate previous same-company production (keep file_category for history)
        old_prod.is_production = False

    # Create new production upload
    from app.services.parser_service import detect_period_month
    from datetime import datetime as _dt
    detected_period = detect_period_month(file.filename, result.get("records"), uploaded_at=_dt.utcnow())

    upload = FileUpload(
        user_id=user.id,
        filename=file.filename,
        file_type=ext,
        company_source=result["company_source"],
        record_count=len(result["records"]),
        format_type=result["format"],
        is_production=True,
        file_category="production",
        period_month=detected_period,
    )
    db.add(upload)
    await db.flush()

    # Bulk insert records
    for rec_data in result["records"]:
        clean = sanitize_record(rec_data)
        record = ClientRecord(
            user_id=user.id,
            upload_id=upload.id,
            **{k: v for k, v in clean.items() if hasattr(ClientRecord, k)},
        )
        db.add(record)

    await db.commit()
    await db.refresh(upload)

    # Create portal snapshots and production summary in background (non-blocking)
    background_tasks.add_task(_create_snapshots_bg, user.id, upload.id)
    background_tasks.add_task(_compute_summary_bg, user.id, upload.id)

    companies = await _get_companies_for_upload(db, upload.id)

    return ProductionFileInfo(
        id=str(upload.id),
        filename=upload.filename,
        file_type=upload.file_type,
        company_source=upload.company_source,
        record_count=upload.record_count,
        uploaded_at=upload.uploaded_at,
        period_month=upload.period_month,
        companies=companies,
    )


@router.get("/current", response_model=ProductionFileInfo | None)
async def get_current_production(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get unified production summary across all active company files.

    Migdal + Menora + ... uploads for the same period all stay
    is_production=True. This endpoint aggregates them into one "monthly
    production" view: combined record count, all companies, latest period.
    The `id` and `filename` reflect the most-recent upload (used by the UI
    as a representative anchor); `companies` lists every contributing one.
    """
    uploads = await _get_all_production_uploads(db, user.id)
    if not uploads:
        return None

    primary = uploads[0]  # most recent (ordered desc by uploaded_at)
    total_records = sum(u.record_count or 0 for u in uploads)

    # Collect every contributing company from each upload's records
    companies_set: set[str] = set()
    for u in uploads:
        for c in await _get_companies_for_upload(db, u.id):
            companies_set.add(c)
    # Fallback to company_source values when receiving_company is sparse
    for u in uploads:
        if u.company_source:
            companies_set.add(u.company_source)
    companies = sorted(c for c in companies_set if c not in ("nan", "None"))

    # Latest period across all active uploads
    periods = [u.period_month for u in uploads if u.period_month]
    latest_period = max(periods) if periods else None

    # When multiple companies feed the unified view, surface a synthetic
    # label so the UI doesn't claim it's just one company's file.
    if len(uploads) > 1:
        company_label = f"{len(uploads)} חברות"  # "N companies"
        filename_label = f"פרודוקציה מאוחדת — {len(uploads)} חברות"
    else:
        company_label = primary.company_source
        filename_label = primary.filename

    return ProductionFileInfo(
        id=str(primary.id),
        filename=filename_label,
        file_type=primary.file_type,
        company_source=company_label,
        record_count=total_records,
        uploaded_at=primary.uploaded_at,
        period_month=latest_period,
        companies=companies,
    )


@router.get("/export.xlsx")
async def export_unified_production(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Unified monthly production xlsx: a `סיכום` sheet plus one sheet per
    company.

    Summary and sheets are both derived from the SAME record set, grouped on
    `company_stem` — so `מנורה מבטחים ביטוח בע"מ` and
    `מנורה מבטחים פנסיה וגמל בע"מ` roll up as one company, and the summary can
    never list a different set of companies than the sheets do.
    """
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    import pandas as pd

    uploads = await _get_all_production_uploads(db, user.id)
    if not uploads:
        raise HTTPException(status_code=404, detail="אין קובץ פרודוקציה פעיל")

    picked = _select_unified_uploads(uploads)
    by_id = {u.id: u for u in picked}

    result = await db.execute(
        select(
            ClientRecord.id_number,
            ClientRecord.first_name,
            ClientRecord.last_name,
            ClientRecord.receiving_company,
            ClientRecord.product,
            ClientRecord.product_type,
            ClientRecord.fund_policy_number,
            ClientRecord.total_premium,
            ClientRecord.accumulation,
            ClientRecord.product_status,
            ClientRecord.is_active,
            ClientRecord.processing_date,
            ClientRecord.sign_date,
            ClientRecord.lead_source,
            ClientRecord.upload_id,
        )
        .where(ClientRecord.upload_id.in_(list(by_id.keys())))
        .order_by(ClientRecord.id_number)
    )
    rows = result.all()

    df = pd.DataFrame([
        {
            "ת.ז": r.id_number,
            "שם פרטי": r.first_name,
            "שם משפחה": r.last_name,
            "חברה מקבלת": r.receiving_company,
            # Source account (Harel agency logins have 2+) — blank otherwise.
            "מספר חשבון": r.lead_source or "",
            "מוצר": r.product,
            "סוג מוצר": r.product_type,
            "מספר פוליסה": r.fund_policy_number,
            "פרמיה": float(r.total_premium) if r.total_premium else None,
            "צבירה": float(r.accumulation) if r.accumulation else None,
            "סטטוס מוצר": r.product_status,
            "פעיל": r.is_active,
            "תאריך עיבוד": r.processing_date,
            "תאריך הצטרפות": r.sign_date,
            "_stem": company_stem(r.receiving_company)
                     or company_stem(by_id[r.upload_id].company_source),
            "_period": (
                by_id[r.upload_id].period_month.strftime("%Y-%m")
                if by_id[r.upload_id].period_month else ""
            ),
            "_source": by_id[r.upload_id].filename,
        }
        for r in rows
    ])

    configured = await _configured_company_stems(db, user.id)
    summary_rows, sheets = _summary_from_rows(
        df, {"סך פרמיה": "פרמיה", "סך צבירה": "צבירה"}, configured,
        kind="production", reasons=await _last_run_reason_by_stem(db, user.id),
    )

    HEBREW_MONTHS = ["", "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
                     "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"]
    periods = [u.period_month for u in picked if u.period_month]
    period = max(periods) if periods else None

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        # Summary first so it opens to the overview
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="סיכום", index=False)
        taken: set[str] = {"סיכום"}
        for name, sheet_df in sheets:
            sheet_df.to_excel(
                writer, sheet_name=_excel_sheet_name(name, taken), index=False
            )
    buf.seek(0)

    label = f"{HEBREW_MONTHS[period.month]} {period.year}" if period else ""
    fname = f"פרודוקציה מאוחדת{' ' + label if label else ''}.xlsx"
    from urllib.parse import quote
    cd = f"attachment; filename=production_merged.xlsx; filename*=UTF-8''{quote(fname)}"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": cd},
    )


@router.get("/commission-export.xlsx")
async def export_unified_commission(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Unified נפרעים xlsx: a `סיכום` sheet plus one sheet per company.

    Same one-row-set construction as the production export — see
    `_summary_from_rows`. Previously this endpoint kept a merged upload AND the
    stale per-company uploads beside it, so `סיכום` listed four May/June
    leftovers as the current month while `מאוחד` held eleven companies for
    July, and `סה״כ` counted every merged row twice.
    """
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    import pandas as pd

    result = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user.id,
            FileUpload.is_production == False,
            FileUpload.file_category == "commission",
        ).order_by(FileUpload.uploaded_at.desc())
    )
    uploads = list(result.scalars().all())
    if not uploads:
        raise HTTPException(status_code=404, detail="אין קובץ נפרעים פעיל")

    picked = _select_unified_uploads(uploads)
    by_id = {u.id: u for u in picked}

    rows_res = await db.execute(
        select(
            ClientRecord.id_number,
            ClientRecord.first_name,
            ClientRecord.last_name,
            ClientRecord.receiving_company,
            ClientRecord.product,
            ClientRecord.product_type,
            ClientRecord.fund_policy_number,
            ClientRecord.total_premium,
            ClientRecord.accumulation,
            ClientRecord.commission_paid,
            ClientRecord.commission_before_fee,
            ClientRecord.management_fee_amount,
            ClientRecord.commission_expected,
            ClientRecord.reported_commission_pct,
            ClientRecord.processing_date,
            ClientRecord.lead_source,
            ClientRecord.upload_id,
        )
        .where(ClientRecord.upload_id.in_(list(by_id.keys())))
        .order_by(ClientRecord.id_number)
    )
    rows = rows_res.all()

    # NOTE column semantics (Harel): the portal's headline נפרעים number is
    # the "סכום תשלום" column → commission_before_fee; "עמלה" (the agent
    # commission component) → commission_paid. Both are exported so the
    # workbook totals reconcile against the portal drill numbers. Collapsing
    # these into ONE column is a separate, per-insurer change: the two are
    # identical for Mor (summing would double), only one is populated for
    # Menora, and BOTH are populated with different figures for Hachshara.
    df = pd.DataFrame([
        {
            "ת.ז": r.id_number,
            "שם פרטי": r.first_name,
            "שם משפחה": r.last_name,
            "חברה מקבלת": r.receiving_company,
            "מספר חשבון": r.lead_source or "",
            "מוצר": r.product,
            "סוג מוצר": r.product_type,
            "מספר פוליסה": r.fund_policy_number,
            "פרמיה": float(r.total_premium) if r.total_premium else None,
            # The expected-commission BASE for the financial book lives here:
            # gemel/pension insurers report accumulation, not premium.
            "צבירה": float(r.accumulation) if r.accumulation else None,
            "סכום תשלום": float(r.commission_before_fee) if r.commission_before_fee else None,
            "עמלה ששולמה": float(r.commission_paid) if r.commission_paid else None,
            "דמי גביה": float(r.management_fee_amount) if r.management_fee_amount else None,
            "עמלה צפויה": float(r.commission_expected) if r.commission_expected else None,
            "אחוז עמלה": float(r.reported_commission_pct) if r.reported_commission_pct else None,
            "תאריך עיבוד": r.processing_date,
            "_stem": company_stem(r.receiving_company)
                     or company_stem(by_id[r.upload_id].company_source),
            "_period": (
                by_id[r.upload_id].period_month.strftime("%Y-%m")
                if by_id[r.upload_id].period_month else ""
            ),
            "_source": by_id[r.upload_id].filename,
        }
        for r in rows
    ])

    configured = await _configured_company_stems(db, user.id)
    summary_rows, sheets = _summary_from_rows(
        df,
        {"סך סכום תשלום": "סכום תשלום", "סך עמלה ששולמה": "עמלה ששולמה",
         "סך צבירה": "צבירה", "סך פרמיה": "פרמיה"},
        configured,
        kind="commission",
        reasons=await _last_run_reason_by_stem(db, user.id),
    )

    HEBREW_MONTHS = ["", "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
                     "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"]
    periods = [u.period_month for u in picked if u.period_month]
    period = max(periods) if periods else None

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="סיכום", index=False)
        taken: set[str] = {"סיכום"}
        for name, sheet_df in sheets:
            sheet_df.to_excel(
                writer, sheet_name=_excel_sheet_name(name, taken), index=False
            )
    buf.seek(0)

    label = f"{HEBREW_MONTHS[period.month]} {period.year}" if period else ""
    fname = f"נפרעים מאוחד{' ' + label if label else ''}.xlsx"
    from urllib.parse import quote
    cd = f"attachment; filename=commission_merged.xlsx; filename*=UTF-8''{quote(fname)}"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": cd},
    )


@router.delete("/current")
async def delete_current_production(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Remove current production file."""
    from app.models.portal_snapshot import PortalSnapshot
    from app.models.debt import Debt
    from app.models.production_summary import ProductionSummary

    upload = await _get_production_upload(db, user.id)
    if not upload:
        raise HTTPException(status_code=404, detail="לא נמצא קובץ פרודוקציה פעיל")

    # Delete related rows first to satisfy FK constraints.
    # debts.production_upload_id is NOT NULL → delete those debt rows.
    # debts.commission_upload_id is nullable but may also point at this upload → handled too.
    from sqlalchemy import delete as sql_delete, update as sql_update
    await db.execute(
        sql_delete(PortalSnapshot).where(PortalSnapshot.upload_id == upload.id)
    )
    await db.execute(
        sql_delete(ProductionSummary).where(ProductionSummary.upload_id == upload.id)
    )
    await db.execute(
        sql_delete(ClientRecord).where(ClientRecord.upload_id == upload.id)
    )
    await db.execute(
        sql_delete(Debt).where(Debt.production_upload_id == upload.id)
    )
    await db.execute(
        sql_update(Debt)
        .where(Debt.commission_upload_id == upload.id)
        .values(commission_upload_id=None)
    )

    await db.delete(upload)
    await db.commit()
    return {"status": "deleted"}


@router.get("/analytics", response_model=ProductionAnalytics | None)
async def get_production_analytics(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Analytics aggregated across ALL active production uploads.

    Multiple companies (Migdal + Menora + …) can each have an
    is_production=True upload for the same period; KPIs combine them so
    the dashboard reflects the unified monthly production.
    """
    uids = await _get_production_upload_ids(db, user.id)
    if not uids:
        return None

    # Totals
    totals = await db.execute(
        select(
            func.count().label("cnt"),
            func.count(func.distinct(ClientRecord.id_number)).label("unique_clients"),
            func.coalesce(func.sum(ClientRecord.total_premium), 0).label("total_premium"),
            func.coalesce(func.sum(ClientRecord.accumulation), 0).label("total_accumulation"),
            func.count(func.distinct(ClientRecord.receiving_company)).label("companies_count"),
        ).where(ClientRecord.upload_id.in_(uids))
    )
    t = totals.one()

    # Company breakdown
    company_q = await db.execute(
        select(
            ClientRecord.receiving_company,
            func.count().label("count"),
            func.count(func.distinct(ClientRecord.id_number)).label("unique_clients"),
            func.coalesce(func.sum(ClientRecord.total_premium), 0).label("premium"),
            func.coalesce(func.sum(ClientRecord.accumulation), 0).label("accumulation"),
        )
        .where(ClientRecord.upload_id.in_(uids), ClientRecord.receiving_company.isnot(None))
        .group_by(ClientRecord.receiving_company)
        .order_by(desc(func.coalesce(func.sum(ClientRecord.accumulation), 0)))
    )
    company_breakdown = [
        {"company": r[0], "count": r[1], "unique_clients": r[2], "premium": float(r[3]), "accumulation": float(r[4])}
        for r in company_q.all() if r[0] and r[0] not in ("nan", "None")
    ]

    # Product type breakdown
    product_q = await db.execute(
        select(
            ClientRecord.product_type,
            func.count().label("count"),
            func.coalesce(func.sum(ClientRecord.total_premium), 0).label("premium"),
        )
        .where(ClientRecord.upload_id.in_(uids), ClientRecord.product_type.isnot(None))
        .group_by(ClientRecord.product_type)
        .order_by(desc(func.count()))
    )
    product_type_breakdown = [
        {"product_type": r[0], "count": r[1], "premium": float(r[2])}
        for r in product_q.all() if r[0] and r[0] not in ("nan", "None")
    ]

    # Status breakdown
    status_q = await db.execute(
        select(
            ClientRecord.product_status,
            func.count().label("count"),
        )
        .where(ClientRecord.upload_id.in_(uids), ClientRecord.product_status.isnot(None))
        .group_by(ClientRecord.product_status)
        .order_by(desc(func.count()))
    )
    status_breakdown = [
        {"status": r[0], "count": r[1]}
        for r in status_q.all() if r[0] and r[0] not in ("nan", "None")
    ]

    # Top 10 clients by premium
    top_premium_q = await db.execute(
        select(
            ClientRecord.id_number,
            ClientRecord.first_name,
            ClientRecord.last_name,
            func.coalesce(func.sum(ClientRecord.total_premium), 0).label("premium"),
            func.count().label("products"),
        )
        .where(ClientRecord.upload_id.in_(uids), ClientRecord.id_number.isnot(None))
        .group_by(ClientRecord.id_number, ClientRecord.first_name, ClientRecord.last_name)
        .order_by(desc(func.coalesce(func.sum(ClientRecord.total_premium), 0)))
        .limit(10)
    )
    top_clients_premium = [
        {"id_number": r[0], "name": f"{r[1] or ''} {r[2] or ''}".strip(), "premium": float(r[3]), "products": r[4]}
        for r in top_premium_q.all()
    ]

    # Top 10 clients by accumulation
    top_accum_q = await db.execute(
        select(
            ClientRecord.id_number,
            ClientRecord.first_name,
            ClientRecord.last_name,
            func.coalesce(func.sum(ClientRecord.accumulation), 0).label("accumulation"),
            func.count().label("products"),
        )
        .where(ClientRecord.upload_id.in_(uids), ClientRecord.id_number.isnot(None))
        .group_by(ClientRecord.id_number, ClientRecord.first_name, ClientRecord.last_name)
        .order_by(desc(func.coalesce(func.sum(ClientRecord.accumulation), 0)))
        .limit(10)
    )
    top_clients_accumulation = [
        {"id_number": r[0], "name": f"{r[1] or ''} {r[2] or ''}".strip(), "accumulation": float(r[3]), "products": r[4]}
        for r in top_accum_q.all()
    ]

    return ProductionAnalytics(
        total_records=t.cnt,
        unique_clients=t.unique_clients,
        total_premium=float(t.total_premium),
        total_accumulation=float(t.total_accumulation),
        companies_count=t.companies_count,
        company_breakdown=company_breakdown,
        product_type_breakdown=product_type_breakdown,
        status_breakdown=status_breakdown,
        top_clients_premium=top_clients_premium,
        top_clients_accumulation=top_clients_accumulation,
    )


@router.get("/alerts")
async def get_production_alerts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """The three alerts the QA doc asks for by name, under "התראות":

        באלו לקוחות חלו השינויים הגדולים ביותר לחיוב ולשלילה
        באלו חברות חלו השינויים הגדולים ביותר לחיוב ולשלילה
        איזה לקוחות לא קיבלתי בגינם תשלום

    The last one is the reason this is a separate endpoint from `/rate-audit`.
    That one audits the insurer's arithmetic against the base the insurer
    ITSELF reported, so a client left out of the report contributes nothing to
    either side and the gap stays zero — a missing client is invisible there.
    Finding one needs the independent base: the production book.

    **The coverage guard is what makes "unpaid" mean anything.** A client can
    only be reported unpaid for a company that actually delivered a נפרעים file
    this period. Without that check, every client of every company whose
    download failed — live, הראל's 210 clients after its נפרעים leg errored —
    would be reported as "never paid for". Mirrors
    `comparison_service`'s `covered_stems`.
    """
    prod_ids = await _get_production_upload_ids(db, user.id)

    comm_uploads = _select_unified_uploads(list((await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user.id,
            FileUpload.is_production == False,
            FileUpload.file_category == "commission",
        ).order_by(FileUpload.uploaded_at.desc())
    )).scalars().all()))
    comm_ids = [u.id for u in comm_uploads]
    if not prod_ids and not comm_ids:
        return {"unpaid": [], "client_movers": [], "company_movers": [],
                "covered_companies": [], "previous_period": None}

    # ── who was paid, and for which companies do we have a report at all ──
    paid_ids: set[str] = set()
    covered: set[str] = set()
    comm_now: dict[str, float] = defaultdict(float)
    comm_now_client: dict[str, dict] = {}
    if comm_ids:
        for r in (await db.execute(select(ClientRecord).where(
            ClientRecord.upload_id.in_(comm_ids)
        ))).scalars().all():
            stem = company_stem(r.receiving_company)
            if stem:
                covered.add(stem)
            amount = _get_commission({
                "commission_paid": r.commission_paid,
                "commission_before_fee": r.commission_before_fee,
                "actual_amount": r.actual_amount,
            })
            amount = float(amount or 0)
            key = _normalize_id(r.id_number)
            if key and amount:
                paid_ids.add(key)
            if stem:
                comm_now[stem] += amount
            if key:
                e = comm_now_client.setdefault(
                    key, {"id_number": r.id_number,
                          "name": _display_name(r.first_name, r.last_name, r.id_number),
                          "amount": 0.0})
                e["amount"] += amount

    # ── production clients with no payment, inside covered companies only ──
    unpaid: dict[str, dict] = {}
    if prod_ids and covered:
        for r in (await db.execute(select(ClientRecord).where(
            ClientRecord.upload_id.in_(prod_ids)
        ))).scalars().all():
            stem = company_stem(r.receiving_company)
            if stem not in covered:
                continue
            key = _normalize_id(r.id_number)
            if not key or key in paid_ids:
                continue
            e = unpaid.setdefault(key, {
                "id_number": r.id_number,
                "name": _display_name(r.first_name, r.last_name, r.id_number),
                "companies": set(), "products": 0,
                "premium": 0.0, "accumulation": 0.0,
            })
            e["companies"].add(stem)
            e["products"] += 1
            e["premium"] += float(r.total_premium or 0)
            e["accumulation"] += float(r.accumulation or 0)

    unpaid_list = [
        {**u, "companies": sorted(u["companies"]),
         "premium": round(u["premium"], 2),
         "accumulation": round(u["accumulation"], 2)}
        for u in unpaid.values()
    ]
    unpaid_list.sort(key=lambda u: -(u["premium"] + u["accumulation"] / 12.0))

    # ── month over month, by company and by client ────────────────────────
    prev_upload = None
    if comm_uploads:
        cur_period = max((u.period_month for u in comm_uploads if u.period_month),
                         default=None)
        prev_q = await db.execute(
            select(FileUpload).where(
                FileUpload.user_id == user.id,
                FileUpload.is_production == False,
                FileUpload.file_category == "commission",
                FileUpload.id.notin_(comm_ids),
                FileUpload.period_month.isnot(None),
                *( [FileUpload.period_month < cur_period] if cur_period else [] ),
            ).order_by(FileUpload.period_month.desc()).limit(1)
        )
        prev_upload = prev_q.scalar_one_or_none()

    company_movers, client_movers = [], []
    if prev_upload is not None:
        comm_prev: dict[str, float] = defaultdict(float)
        prev_client: dict[str, dict] = {}
        for r in (await db.execute(select(ClientRecord).where(
            ClientRecord.upload_id == prev_upload.id
        ))).scalars().all():
            amount = float(_get_commission({
                "commission_paid": r.commission_paid,
                "commission_before_fee": r.commission_before_fee,
                "actual_amount": r.actual_amount,
            }) or 0)
            stem = company_stem(r.receiving_company)
            if stem:
                comm_prev[stem] += amount
            key = _normalize_id(r.id_number)
            if key:
                e = prev_client.setdefault(
                    key, {"name": _display_name(r.first_name, r.last_name, r.id_number),
                          "amount": 0.0})
                e["amount"] += amount

        for stem in set(comm_now) | set(comm_prev):
            now, before = comm_now.get(stem, 0.0), comm_prev.get(stem, 0.0)
            if round(now - before, 2):
                company_movers.append({
                    "company": stem, "now": round(now, 2), "previous": round(before, 2),
                    "delta": round(now - before, 2),
                    "delta_pct": round((now - before) / before * 100.0, 1) if before else None,
                    # A company that sent no report this period has not "dropped
                    # to zero" — it is missing. Live, הראל reads 6,788 → 0
                    # (−100%) purely because its נפרעים download failed, and
                    # presenting that as the month's biggest business decline
                    # would send the agent chasing an insurer instead of a
                    # failed run.
                    "reported": stem in covered,
                })
        company_movers.sort(key=lambda m: -abs(m["delta"]))

        for key in set(comm_now_client) | set(prev_client):
            now = comm_now_client.get(key, {}).get("amount", 0.0)
            before = prev_client.get(key, {}).get("amount", 0.0)
            if round(now - before, 2):
                client_movers.append({
                    "id_number": comm_now_client.get(key, {}).get("id_number") or key,
                    "name": (comm_now_client.get(key, {}).get("name")
                             or prev_client.get(key, {}).get("name") or ""),
                    "now": round(now, 2), "previous": round(before, 2),
                    "delta": round(now - before, 2),
                })
        client_movers.sort(key=lambda m: -abs(m["delta"]))

    # Every company the agent could expect a report from this period, each with
    # whether it actually arrived. The count alone read as a contradiction next
    # to a movers chart that showed one company MORE than the count.
    checked = []
    for stem in sorted(set(covered) | {m["company"] for m in company_movers}):
        checked.append({
            "company": stem,
            "reported": stem in covered,
            "commission": round(comm_now.get(stem, 0.0), 2),
        })

    return {
        "unpaid": unpaid_list[:50],
        "unpaid_total": len(unpaid_list),
        "checked_companies": checked,
        # Naming the companies the check COULD run for is what stops a short
        # list reading as "almost everyone was paid".
        "covered_companies": sorted(covered),
        "client_movers": client_movers[:10],
        "company_movers": company_movers[:10],
        "previous_period": (prev_upload.period_month.strftime("%Y-%m")
                            if prev_upload is not None and prev_upload.period_month else None),
    }



@router.get("/rate-audit")
async def get_rate_audit(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Per company: what the insurer actually paid vs what the agreement says.

    QA 2026-09-09 item 2 — "when the נפרעים rate disagrees with the agreement
    rate, raise an alert". Computable for EVERY company today, because the
    נפרעים report carries its own commission base: gemel houses report צבירה
    (מור ₪91.4M, הכשרה ₪213.2M) and insurers report פרמיה.

    **Everything is decided PER ROW, then summed.** Two measured reasons, both
    of which produced false breaches when this was computed on company totals:

      1. A company can carry BOTH bases. הפניקס has ₪125.4M of gemel צבירה AND
         ₪705K of insurance פרמיה under one brand; picking one basis for the
         company priced the whole book on the wrong denominator.
      2. The agreement rate is per PRODUCT. Asking `select_rate` for a company
         with no product returns the MEDIAN of that company's rates, so מנורה
         compared a blended 4.39% actual against a 10% median and reported a
         −56% breach that does not exist.

    `expected` therefore prices each row against ITS product's rate, exactly as
    the commission engine does, and `effective_agreed_rate` is reported back as
    a weighted average purely for display.

    ⚠️ This audits the insurer's ARITHMETIC, not whether it paid for everyone.
    The base is the base the insurer chose to remit on, so a client it left out
    of the report contributes nothing to either side and the gap stays zero. A
    missing client can only be found against production — a different question,
    which this endpoint deliberately does not claim to answer.
    """
    result = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user.id,
            FileUpload.is_production == False,
            FileUpload.file_category == "commission",
        ).order_by(FileUpload.uploaded_at.desc())
    )
    picked = _select_unified_uploads(list(result.scalars().all()))
    if not picked:
        return {"companies": [], "period": None}

    rows = (await db.execute(
        select(ClientRecord).where(
            ClientRecord.upload_id.in_([u.id for u in picked])
        )
    )).scalars().all()

    user_rates = list((await db.execute(
        select(CommissionRate).where(CommissionRate.user_id == user.id)
    )).scalars().all())

    # VAT basis is a per-COMPANY property of the export, so resolve it once per
    # company before pricing any row.
    grouped: dict[str, list] = defaultdict(list)
    for r in rows:
        brand = company_stem(r.receiving_company) or (r.receiving_company or "")
        if brand:
            grouped[brand].append(r)

    out = []
    for brand, recs in grouped.items():
        basis = detect_vat_basis([
            {"commission_paid": r.commission_paid,
             "commission_before_fee": r.commission_before_fee,
             "actual_amount": r.actual_amount} for r in recs
        ])
        # FIRM vs ESTIMATED, kept apart all the way to the response.
        # `rate_select` falls back to a company's DEFAULT or the MEDIAN of its
        # rates when no agreement line names the product, and that number must
        # never be shown as "what you are owed" — `comparison_service` carries
        # the incident: מנורה has no ביטוח-חיים line, those policies fell to
        # the 10% median and produced a ₪21K phantom debt. The same fallback
        # here priced 21 Phoenix PENSION rows at an ~8.7% insurance rate
        # (expected ₪5,515 vs ₪230 actually paid) and 61 מנורה "מבטחים יותר"
        # rows at ₪12,001 vs ₪361 — both would read as the insurer underpaying
        # by ~96%. Only a rate row that NAMES the product can accuse anyone.
        paid = expected = accum_base = prem_base = 0.0
        paid_firm = expected_firm = 0.0
        accum_firm = prem_firm = 0.0
        no_rate_rows = estimated_rows = 0
        per_product: dict[str, dict] = {}

        for r in recs:
            accum = float(r.accumulation or 0)
            premium = float(r.total_premium or 0)
            row_paid = ex_vat_commission({
                "commission_paid": r.commission_paid,
                "commission_before_fee": r.commission_before_fee,
                "actual_amount": r.actual_amount,
            }, basis)
            paid += row_paid

            product_type = r.fund_type or r.product_type
            # The CANONICAL basis decision, not a hand-rolled one. It excludes
            # קרן פנסיה, whose commission is on the monthly deposit rather than
            # the balance — pricing 21 Phoenix pension rows off their
            # accumulation invented ₪5,515 of "expected" against ₪230 actually
            # paid, and that single mistake drove Phoenix's headline gap.
            is_accum = accumulation_based(product_type, accum)
            rate, route = select_rate(
                user_rates, r.receiving_company, r.product, product_type, is_accum
            )
            if is_accum:
                accum_base += accum
                row_exp = accum * rate / 12.0
            else:
                prem_base += premium
                row_exp = premium * rate
            if rate <= 0:
                no_rate_rows += 1
            is_estimate = not (route or "").endswith((":product", ":residue"))
            expected += row_exp
            if rate > 0 and is_estimate:
                estimated_rows += 1
            elif rate > 0:
                paid_firm += row_paid
                expected_firm += row_exp
                # The rate columns must be computed on the SAME rows as the
                # gap. Deriving them from the full base put מנורה at
                # "4.39% actual vs 10.87% agreed" beside a +2.0% gap — two
                # numbers that contradict each other on one line.
                if is_accum:
                    accum_firm += accum
                else:
                    prem_firm += premium

            _, prod = classify_product({
                "product_type": r.product_type, "fund_type": r.fund_type,
                "product": r.product, "total_premium": premium,
                "accumulation": accum,
            })
            pp = per_product.setdefault(
                prod or "ללא שם מוצר",
                {"product": prod or "ללא שם מוצר", "paid": 0.0,
                              "expected": 0.0, "records": 0, "estimated": 0}
            )
            pp["paid"] += row_paid
            pp["expected"] += row_exp
            pp["records"] += 1
            if rate > 0 and is_estimate:
                pp["estimated"] += 1

        base = accum_base if accum_base > prem_base else prem_base
        base_kind = "accumulation" if accum_base > prem_base else "premium"
        # Headline rate: the whole book, for "what is this insurer paying me".
        implied_all = (paid * 12.0 / accum_base) if base_kind == "accumulation" and accum_base \
            else ((paid / prem_base) if prem_base else None)
        # Comparable pair: firm rows only, so the two rate columns and the gap
        # all describe the same rows.
        firm_accum = accum_firm > prem_firm
        firm_base = accum_firm if firm_accum else prem_firm
        implied = ((paid_firm * 12.0 / firm_base) if firm_accum else (paid_firm / firm_base)) \
            if firm_base else None
        eff_agreed = ((expected_firm * 12.0 / firm_base) if firm_accum else (expected_firm / firm_base)) \
            if firm_base else None
        # The headline gap is FIRM-ONLY. An estimated expected is not a claim.
        gap_pct = ((paid_firm - expected_firm) / expected_firm * 100.0) \
            if expected_firm > 0 else None

        for pp in per_product.values():
            pp["paid"] = round(pp["paid"], 2)
            pp["expected"] = round(pp["expected"], 2)

        out.append({
            "company": brand,
            "records": len(recs),
            "paid": round(paid, 2),
            "expected": round(expected, 2),
            # Comparable pair — same rows on both sides, firm rates only.
            "paid_firm": round(paid_firm, 2),
            "expected_firm": round(expected_firm, 2),
            "gap": round(paid_firm - expected_firm, 2),
            "gap_pct": round(gap_pct, 1) if gap_pct is not None else None,
            "rows_estimated": estimated_rows,
            # True when NOTHING in this company is firm enough to compare — the
            # UI must show "לא ניתן להשוות", never a gap.
            "comparable": expected_firm > 0,
            "base": round(base, 2),
            "base_kind": base_kind,
            "implied_rate": round(implied, 6) if implied is not None else None,
            "implied_rate_all": round(implied_all, 6) if implied_all is not None else None,
            "effective_agreed_rate": round(eff_agreed, 6) if eff_agreed else None,
            # No agreement covers ANY row → there is nothing to compare against,
            # and a 0 expected must not be rendered as "-100% underpaid".
            "no_agreement": no_rate_rows == len(recs),
            "rows_without_rate": no_rate_rows,
            "products": sorted(per_product.values(), key=lambda x: -x["paid"]),
            # An unverified VAT basis can move `paid` by ~18%, which would read
            # as a rate breach that isn't one.
            "vat_verified": basis["verified"],
            "vat_reason": basis["reason"],
        })
    out.sort(key=lambda c: -c["paid"])
    periods = [u.period_month for u in picked if u.period_month]
    return {
        "companies": out,
        "period": max(periods).strftime("%Y-%m") if periods else None,
    }


@router.get("/breakdown")
async def get_production_breakdown(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Company × product breakdown of the production book, split ביטוח/פיננסים.

    Answers QA 2026-09-09 items 8, 9 and 11, none of which the existing
    `/analytics` shape can serve:

      * company and product were two INDEPENDENT single-key GROUP BYs, so there
        was no cross-tab — clicking a company could never show what it holds.
      * both grouped on raw strings. `receiving_company` splits one insurer
        across its legal entities (מנורה ביטוח + מנורה פנסיה וגמל), and
        `product_type` reports one product under four spellings.
      * there was no ביטוח/פיננסים axis at all.

    Aggregated in Python rather than SQL because `classify_product` is a Python
    taxonomy; the active production book is ~2k rows, one indexed query.

    Every company reports BOTH bases — accumulation ("how much I manage there")
    and premium ("what my clients pay there") — because insurers populate only
    one of the two and a single-number chart silently hides half the book.
    """
    uids = await _get_production_upload_ids(db, user.id)
    if not uids:
        return {"companies": [], "products": {"insurance": [], "financial": []},
                "totals": {"premium": 0.0, "accumulation": 0.0, "clients": 0}}

    rows = (await db.execute(
        select(
            ClientRecord.receiving_company,
            ClientRecord.product_type,
            ClientRecord.fund_type,
            ClientRecord.product,
            ClientRecord.total_premium,
            ClientRecord.accumulation,
            ClientRecord.id_number,
        ).where(ClientRecord.upload_id.in_(uids))
    )).all()

    def _cell():
        return {"premium": 0.0, "accumulation": 0.0, "count": 0, "clients": set()}

    companies: dict[str, dict] = {}
    products: dict[str, dict[str, dict]] = {"insurance": {}, "financial": {}}
    all_clients: set[str] = set()
    tot_p = tot_a = 0.0

    for company, ptype, ftype, pname, premium, accum, idn in rows:
        if not company or company in ("nan", "None"):
            continue
        prem = float(premium or 0)
        acc = float(accum or 0)
        category, product = classify_product({
            "product_type": ptype, "fund_type": ftype, "product": pname,
            "total_premium": prem, "accumulation": acc,
        })
        # Brand, not legal entity — the agent thinks in one "מנורה".
        brand = company_stem(company) or company

        co = companies.setdefault(brand, {
            "company": brand, "premium": 0.0, "accumulation": 0.0,
            "count": 0, "clients": set(), "entities": set(),
            "products": {"insurance": {}, "financial": {}},
        })
        co["premium"] += prem
        co["accumulation"] += acc
        co["count"] += 1
        co["entities"].add(company)
        cell = co["products"][category].setdefault(product, _cell())
        cell["premium"] += prem
        cell["accumulation"] += acc
        cell["count"] += 1

        pc = products[category].setdefault(product, _cell())
        pc["premium"] += prem
        pc["accumulation"] += acc
        pc["count"] += 1

        if idn:
            co["clients"].add(idn)
            cell["clients"].add(idn)
            pc["clients"].add(idn)
            all_clients.add(idn)
        tot_p += prem
        tot_a += acc

    def _emit(cells: dict, sort_key: str) -> list[dict]:
        out = [
            {"product": name, "premium": round(c["premium"], 2),
             "accumulation": round(c["accumulation"], 2),
             "count": c["count"], "clients": len(c["clients"])}
            for name, c in cells.items()
        ]
        out.sort(key=lambda r: (-r[sort_key], -r["count"], r["product"]))
        return out

    company_list = []
    for co in companies.values():
        company_list.append({
            "company": co["company"],
            "premium": round(co["premium"], 2),
            "accumulation": round(co["accumulation"], 2),
            "count": co["count"],
            "clients": len(co["clients"]),
            # Which legal entities rolled up here — so the agent can see that
            # "מנורה" is two companies without the charts fragmenting.
            "entities": sorted(co["entities"]),
            "products": {
                "insurance": _emit(co["products"]["insurance"], "premium"),
                "financial": _emit(co["products"]["financial"], "accumulation"),
            },
        })
    company_list.sort(key=lambda r: (-(r["accumulation"] + r["premium"]), r["company"]))

    return {
        "companies": company_list,
        "products": {
            "insurance": _emit(products["insurance"], "premium"),
            "financial": _emit(products["financial"], "accumulation"),
        },
        "totals": {
            "premium": round(tot_p, 2),
            "accumulation": round(tot_a, 2),
            "clients": len(all_clients),
        },
    }


@router.get("/breakdown/clients")
async def get_breakdown_clients(
    category: str | None = None,
    product: str | None = None,
    company: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """The clients behind any cell of `/breakdown` — QA #9 ("clicking a product
    opens every client who holds it") and QA #8's per-company drill.

    Filters are applied to the CLASSIFIED values, not the raw columns, so the
    list matches exactly what the chart showed. Passing none returns every
    client, which is what the KPI tiles drill into.
    """
    uids = await _get_production_upload_ids(db, user.id)
    if not uids:
        return {"clients": [], "total": 0}

    rows = (await db.execute(
        select(
            ClientRecord.id_number,
            ClientRecord.first_name,
            ClientRecord.last_name,
            ClientRecord.receiving_company,
            ClientRecord.product_type,
            ClientRecord.fund_type,
            ClientRecord.product,
            ClientRecord.total_premium,
            ClientRecord.accumulation,
            ClientRecord.product_status,
        ).where(ClientRecord.upload_id.in_(uids))
    )).all()

    clients: dict[str, dict] = {}
    for idn, first, last, co, ptype, ftype, pname, premium, accum, status in rows:
        if not idn:
            continue
        prem = float(premium or 0)
        acc = float(accum or 0)
        cat, prod = classify_product({
            "product_type": ptype, "fund_type": ftype, "product": pname,
            "total_premium": prem, "accumulation": acc,
        })
        brand = company_stem(co) or (co or "")
        if category and cat != category:
            continue
        if product and prod != product:
            continue
        if company and brand != company:
            continue
        c = clients.setdefault(idn, {
            "id_number": idn, "name": f"{first or ''} {last or ''}".strip(),
            "premium": 0.0, "accumulation": 0.0, "products": [],
        })
        c["premium"] += prem
        c["accumulation"] += acc
        c["products"].append({
            "product": prod, "raw_product": pname or ptype or ftype or "",
            "company": brand, "category": cat,
            "premium": round(prem, 2), "accumulation": round(acc, 2),
            "status": status,
        })

    out = list(clients.values())
    for c in out:
        c["premium"] = round(c["premium"], 2)
        c["accumulation"] = round(c["accumulation"], 2)
    out.sort(key=lambda c: (-(c["accumulation"] + c["premium"]), c["name"]))
    return {"clients": out, "total": len(out)}



@router.get("/clients")
async def get_production_clients(
    sort: str = "premium",
    search: str = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get all clients from the active production file, grouped by id_number.

    Aggregates across all active production uploads (one per company) so a
    client appearing in both Migdal and Menora is shown once with summed
    premium/accumulation across both feeds.
    """
    uids = await _get_production_upload_ids(db, user.id)
    if not uids:
        return []

    order_col = func.coalesce(func.sum(ClientRecord.accumulation), 0) if sort == "accumulation" else func.coalesce(func.sum(ClientRecord.total_premium), 0)

    filters = [ClientRecord.upload_id.in_(uids), ClientRecord.id_number.isnot(None)]
    if search:
        search = search.strip()
        filters.append(
            (ClientRecord.id_number.contains(search)) |
            (ClientRecord.first_name.ilike(f"%{search}%")) |
            (ClientRecord.last_name.ilike(f"%{search}%"))
        )

    q = await db.execute(
        select(
            ClientRecord.id_number,
            func.min(ClientRecord.first_name).label("first_name"),
            func.min(ClientRecord.last_name).label("last_name"),
            func.min(ClientRecord.receiving_company).label("company"),
            func.coalesce(func.sum(ClientRecord.total_premium), 0).label("premium"),
            func.coalesce(func.sum(ClientRecord.accumulation), 0).label("accumulation"),
            func.count().label("products"),
        )
        .where(*filters)
        .group_by(ClientRecord.id_number)
        .order_by(desc(order_col))
        .limit(50)
    )
    return [
        {
            "id_number": r.id_number,
            "name": f"{r.first_name or ''} {r.last_name or ''}".strip(),
            "company": r.company,
            "premium": float(r.premium),
            "accumulation": float(r.accumulation),
            "products": r.products,
        }
        for r in q.all()
    ]


@router.get("/clients/{id_number}")
async def get_client_detail(
    id_number: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get all products for a specific client across active production uploads."""
    uids = await _get_production_upload_ids(db, user.id)
    if not uids:
        raise HTTPException(status_code=404, detail="אין קובץ פרודוקציה פעיל")

    result = await db.execute(
        select(ClientRecord)
        .where(
            ClientRecord.upload_id.in_(uids),
            ClientRecord.id_number == id_number.lstrip('0'),
        )
    )
    records = result.scalars().all()
    if not records:
        raise HTTPException(status_code=404, detail="לקוח לא נמצא")

    name = f"{records[0].first_name or ''} {records[0].last_name or ''}".strip()
    products = []
    for r in records:
        products.append({
            "product": r.product or r.product_type or "—",
            "company": r.receiving_company or "—",
            "premium": float(r.total_premium or 0),
            "accumulation": float(r.accumulation or 0),
            "status": r.product_status or "—",
            "policy_number": r.fund_policy_number or "—",
        })

    return {
        "id_number": id_number,
        "name": name,
        "products": products,
        "total_premium": sum(p["premium"] for p in products),
        "total_accumulation": sum(p["accumulation"] for p in products),
    }


@router.get("/landing")
async def production_landing(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Pre-upload Production tab hero data.

    Returns a lifetime count of production uploads + the most recent
    ProductionSummary so the agent always sees their last-known state, even
    when no file is currently active.
    """
    files_q = await db.execute(
        select(func.count())
        .select_from(FileUpload)
        .where(FileUpload.user_id == user.id, FileUpload.file_category == "production")
    )
    files_loaded = int(files_q.scalar_one() or 0)

    last_q = await db.execute(
        select(ProductionSummary)
        .where(ProductionSummary.user_id == user.id)
        .order_by(desc(ProductionSummary.upload_date))
        .limit(1)
    )
    last = last_q.scalar_one_or_none()
    if last is None:
        return {"files_loaded": files_loaded, "latest": None}

    return {
        "files_loaded": files_loaded,
        "latest": {
            "upload_date":        last.upload_date.isoformat(),
            "period_label":       last.period_label,
            "total_records":      last.total_records,
            "unique_clients":     last.unique_clients,
            "total_premium":      float(last.total_premium),
            "total_accumulation": float(last.total_accumulation),
            "companies_count":    len(last.companies_json or []),
            "top_clients":        (last.top_clients_json or [])[:5],
        },
    }


@router.get("/trend")
async def get_commission_trend(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Month-over-month ACTUAL commission received, broken down by company.

    This is the companion to `/expected-trend`. Expected commission can only be
    computed for a company that has an agreement AND a priceable base, so on a
    real book it covers a handful of companies — live, 2 of 9. Actual money
    received covers every company that paid, which is what an agent means by
    "show me all my companies".

    Grouping is by the RECORD's company, not the upload's `company_source`.
    The previous version grouped by source and so reported a single bucket
    named "מאוחד" worth ₪102,945 — the entire merged file as one "company" —
    alongside stale per-company leftovers, double-counting to ₪138,662 against
    a true ₪102,945. It had no frontend caller, which is why that went unseen.

    Period selection reuses `_select_unified_uploads`, so a stale leftover
    cannot resurface here after being excluded everywhere else.
    """
    uploads = list((await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user.id,
            FileUpload.is_production == False,
            FileUpload.file_category == "commission",
        ).order_by(FileUpload.uploaded_at.desc())
    )).scalars().all())
    if not uploads:
        return []

    # One merged upload per period: the batch produces exactly one, and a
    # period's rows must not be assembled from two different harvests.
    by_period: dict = {}
    for u in uploads:
        if u.period_month is None:
            continue
        cur = by_period.get(u.period_month)
        if cur is None or u.uploaded_at > cur.uploaded_at:
            by_period[u.period_month] = u
    if not by_period:
        return []

    keep = {u.id for u in _select_unified_uploads(uploads)}
    periods = sorted(
        p for p, u in by_period.items() if u.id in keep or u.company_source == "מאוחד"
    )
    if not periods:
        periods = sorted(by_period)

    points = []
    for period in periods:
        upload = by_period[period]
        rows = (await db.execute(
            select(
                ClientRecord.id_number,
                ClientRecord.receiving_company,
                ClientRecord.commission_paid,
                ClientRecord.commission_before_fee,
                ClientRecord.actual_amount,
            ).where(ClientRecord.upload_id == upload.id)
        )).all()

        by_company: dict[str, float] = defaultdict(float)
        clients: set[str] = set()
        total = 0.0
        for idn, company, paid, before_fee, actual in rows:
            amount = float(_get_commission({
                "commission_paid": paid,
                "commission_before_fee": before_fee,
                "actual_amount": actual,
            }) or 0)
            if not amount:
                continue
            stem = company_stem(company) or (company or "—")
            by_company[stem] += amount
            total += amount
            if idn:
                clients.add(idn)

        points.append({
            "period_month": period,
            "period_label": period.strftime("%Y-%m"),
            "total_commission": round(total, 2),
            "unique_clients": len(clients),
            "by_company": {k: round(v, 2) for k, v in
                           sorted(by_company.items(), key=lambda kv: -kv[1])},
        })
    return points



@router.get("/history", response_model=list[ProductionFileInfo])
async def get_production_history(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List previous production files (non-active) for comparison."""
    result = await db.execute(
        select(FileUpload)
        .where(
            FileUpload.user_id == user.id,
            FileUpload.file_category == "production",
            FileUpload.is_production == False,
        )
        .order_by(desc(FileUpload.uploaded_at))
        .limit(10)
    )
    uploads = result.scalars().all()
    out = []
    for u in uploads:
        companies = await _get_companies_for_upload(db, u.id)
        out.append(ProductionFileInfo(
            id=str(u.id),
            filename=u.filename,
            file_type=u.file_type,
            company_source=u.company_source,
            record_count=u.record_count,
            uploaded_at=u.uploaded_at,
            companies=companies,
        ))
    return out


@router.get("/expected-trend")
async def get_expected_commission_trend(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Per-period EXPECTED commission (production × agreement rates).

    Unlike `/trend` (which sums commission_paid from נפרעים files), this
    endpoint computes what the agent SHOULD earn for each production period
    based on the production records × their per-product/company rates.
    Drives the "עמלות צפויות לפי חודש" chart — the value updates the moment
    a new production file is uploaded, without waiting for the matching
    נפרעים report to arrive.

    For each production upload with non-NULL period_month:
      total_M = Σ over records of:
                  gemel/savings: accumulation × rate / 12
                  insurance:     premium × rate
    Re-uploads of the same period dedupe to the latest by uploaded_at.

    Returns {"points": [...], "reason": str|None} where reason explains an
    empty/thin chart: "no_production" (no period-tagged production uploads),
    "no_rates" (every period dropped — no record matched a rate > 0),
    "single_month" (only one point survived), or null.
    """
    from collections import defaultdict
    from app.models.commission_rate import CommissionRate
    from app.utils.company_norm import normalize_company

    # Pull every production upload that's period-tagged. We dedupe per
    # period_month down to ONE upload — preferring the active file
    # (is_production) so the trend agrees with the dashboard/AI, then latest
    # by uploaded_at for past periods. Re-uploads of the same month would
    # otherwise double-count or pick a stale duplicate.
    prod_q = await db.execute(
        select(FileUpload)
        .where(
            FileUpload.user_id == user.id,
            FileUpload.file_category == "production",
            FileUpload.period_month.isnot(None),
        )
        .order_by(desc(FileUpload.is_production), desc(FileUpload.uploaded_at))
    )
    prods = prod_q.scalars().all()
    latest_by_period: dict = {}
    for u in prods:
        if u.period_month not in latest_by_period:
            latest_by_period[u.period_month] = u
    if not latest_by_period:
        return {"points": [], "reason": "no_production"}

    # User's agreement rates — same _pick_rate logic as /compare.
    rates_q = await db.execute(
        select(CommissionRate).where(CommissionRate.user_id == user.id)
    )
    user_rates = list(rates_q.scalars().all())

    _pick_rate = make_pick_rate(user_rates)

    # Pull production records for all relevant uploads in one query.
    upload_ids = [u.id for u in latest_by_period.values()]
    records_q = await db.execute(
        select(
            ClientRecord.upload_id,
            ClientRecord.id_number,
            ClientRecord.receiving_company,
            ClientRecord.product_type,
            ClientRecord.product,
            ClientRecord.total_premium,
            ClientRecord.accumulation,
        ).where(
            ClientRecord.upload_id.in_(upload_ids),
            ClientRecord.user_id == user.id,
        )
    )

    # period_month → company → expected_total
    per_period: dict = defaultdict(lambda: defaultdict(float))
    per_period_clients: dict = defaultdict(set)
    upload_to_period = {u.id: u.period_month for u in latest_by_period.values()}

    # Why a company produced NO expected commission — so the chart can say so
    # instead of silently dropping it. An agent seeing 2 of 7 companies has no
    # way to tell "these have no agreement rate" from "the app is broken".
    # Four buckets, not two. The old pair ("no_rate" / "no_base") could not tell
    # apart the three things an agent would ACT on differently, so the UI showed
    # one misleading sentence for all of them (QA 2026-09-09, item 7):
    #
    #   no_company      → upload an agreement for this insurer     (מגדל: the
    #                     agent has ZERO rate rows for it)
    #   no_rate         → the agreement exists but has no rate for this product
    #   risk_no_premium → the row HAS accumulation but is a risk product, so the
    #                     premium basis applies and the file carries no premium.
    #                     Saying "אין צבירה או פרמיה בקובץ" here is simply false:
    #                     live, Phoenix's 316 production rows hold ₪51.2M of
    #                     צבירה and were reported as having none.
    #   no_base         → genuinely no premium AND no accumulation (Harel's
    #                     ר.ת. vault reports: money columns empty on all rows)
    excluded: dict = defaultdict(
        lambda: defaultdict(lambda: {b: 0 for b in UNCOVERED_BUCKETS})
    )

    for upload_id, id_number, company, product_type, product_name, premium, accum in records_q.all():
        if not company:
            continue
        # Classify by the DATA: any product carrying accumulation (gemel,
        # השתלמות, פוליסת חיסכון, פנסיה, מנהלים) earns commission on
        # accumulation; only premium-bearing risk products use premium × rate.
        accum_f = float(accum or 0)
        premium_f = float(premium or 0)
        is_accum = accumulation_based(product_type, accum_f)
        rate, route = select_rate(user_rates, company, product_name, product_type, is_accum)
        period = upload_to_period[upload_id]
        if is_accum:
            exp = accum_f * rate / 12.0 if rate > 0 else 0.0
        else:
            exp = premium_f * rate if rate > 0 else 0.0
        bucket = _uncovered_bucket(rate, route, is_accum, premium_f, accum_f, exp)
        if bucket:
            excluded[period][company][bucket] += 1
            continue
        per_period[period][company] += exp
        if id_number:
            per_period_clients[period].add(id_number)

    out = []
    for period in sorted(per_period.keys()):
        by_company = {c: round(v, 2) for c, v in per_period[period].items() if v > 0}
        total = round(sum(by_company.values()), 2)
        out.append({
            "period_month": period.isoformat(),
            "period_label": period.strftime("%Y-%m"),
            "total_expected": total,
            "unique_clients": len(per_period_clients[period]),
            "by_company": by_company,
            # Companies present in this month's production that contribute
            # nothing, and why. Shown under the chart.
            "uncovered": [
                {"company": co, **v}
                for co, v in sorted(
                    excluded.get(period, {}).items(),
                    key=lambda kv: -sum(kv[1].values()),
                )
                if co not in by_company and any(v.values())
            ],
        })
    if not out:
        reason = "no_rates"
    elif len(out) == 1:
        reason = "single_month"
    else:
        reason = None
    return {"points": out, "reason": reason}


class CompareRequest(BaseModel):
    current_upload_id: str
    previous_upload_id: str


async def _build_commission_lookups(db: AsyncSession, user_id: uuid.UUID, dividing_date, current_period_month=None, previous_period_month=None):
    """Build current vs previous {id_number: total_commission} grouped BY COMPANY.

    Period-aware pairing (added 2026-05):
      - current_period_month / previous_period_month: when supplied, ONLY
        commission uploads whose period_month matches are considered as
        current/previous candidates. This is the period filter the user
        explicitly asked for ("if production is APR, commission files
        should also be APR").
      - Uploads with NULL period_month are excluded from period-strict
        selection (they fall back into the legacy filename-based pairing).

    Pairing strategy when period is unknown:

    For each distinct company_source (fallback: filename):
      - current  = the latest upload
      - previous = the most recent upload with a DIFFERENT filename
                   (= a different period). If all uploads share the same filename
                   (re-uploads/corrections of the same period), fall back to the
                   second-latest of those.

    Returns:
        current_comm: {id_number: total}
        previous_comm: {id_number: total}
        has_data: bool
        has_previous: bool — at least one company has a prior-period pairing
        current_comm_detail: {id_number: [{company, commission}, ...]}
        covered_categories: set of product categories covered
    """
    all_result = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user_id,
            FileUpload.is_production == False,
            FileUpload.file_category == "commission",
        ).order_by(desc(FileUpload.uploaded_at))
    )
    all_uploads = all_result.scalars().all()

    # NOTE: period filtering was removed here (2026-05-18). Israeli insurance
    # commission reports lag production by ~1 month — APR production pairs
    # naturally with MAR commission reports. Restricting to literal period
    # match made the dashboard total drop to ₪1,731 (Hachshara APR alone)
    # while the agent's real reported commissions across all companies'
    # latest reports was ₪158K. We now show the LATEST file per company
    # regardless of labelled period; period_month is informational only.

    # Pair commission files BY COMPANY (not filename, not upload date).
    # For each company: current = latest upload; previous = the next-most-recent
    # upload with a DIFFERENT filename (= different period). If all uploads share
    # the same filename (re-uploads/corrections of the same period), previous
    # falls back to the second-latest of those.
    #
    # Rationale: users upload one commission file per company per month, with
    # period-specific filenames like "מור עמלות פברואר 26" vs "12_2025_נפרעים מור".
    # Date-based splits don't work because batch-uploads share timestamps, and
    # filename-based matching never triggers across periods.
    from collections import defaultdict

    upload_meta = {}  # upload_id → {company, filename}
    # Step 1: dedupe to LATEST upload per (company, filename) — handles
    # re-uploads of the same period (corrections). Each filename is a
    # separate data stream (Phoenix has 4 files for גמל/בריאות/ביטוח/עמלות,
    # we keep all 4).
    by_filename_latest = {}  # filename → latest upload
    for u in all_uploads:
        if u.filename not in by_filename_latest:
            by_filename_latest[u.filename] = u
            company_key = u.company_source or u.filename
            upload_meta[u.id] = {"company": company_key, "filename": u.filename}

    # Step 2: PER COMPANY, pick only files from the LATEST period for that
    # company. This is the right semantic for "this month's commission" —
    # mixing Sep 2025 + Jan 2026 + Mar 2026 files all together gave a
    # lifetime ₪158K total when the user expected ~₪65K (latest cycle).
    # Each company's "latest period" is the max(period_month) among its
    # uploads. Files with NULL period_month are kept as legacy fallback.
    by_company_period: dict[str, list] = defaultdict(list)
    for u in by_filename_latest.values():
        company_key = u.company_source or u.filename
        by_company_period[company_key].append(u)

    current_upload_ids = []
    previous_upload_ids = []
    for company, uploads in by_company_period.items():
        if not uploads:
            continue
        # Find the latest period_month for this company. Uploads with
        # period_month=None sort last so a dated upload always wins.
        with_period = [u for u in uploads if u.period_month is not None]
        if with_period:
            latest_period = max(u.period_month for u in with_period)
            current_uploads = [u for u in uploads if u.period_month == latest_period]
            # Previous = files from the next-most-recent period for this company
            prior_periods = sorted({u.period_month for u in with_period if u.period_month < latest_period}, reverse=True)
            if prior_periods:
                prev_period = prior_periods[0]
                previous_upload_ids.extend(u.id for u in uploads if u.period_month == prev_period)
        else:
            # No dated uploads → fall back to latest upload (legacy path)
            current_uploads = [uploads[0]]
        current_upload_ids.extend(u.id for u in current_uploads)

    has_previous = len(previous_upload_ids) > 0
    all_needed_ids = list(set(current_upload_ids + previous_upload_ids))

    has_data = len(all_needed_ids) > 0

    # Fetch records for all needed uploads in one query
    # records_by_upload: {upload_id: {id_number: commission_sum}}
    records_by_upload = {}
    covered_categories = set()  # which product categories have commission data
    if all_needed_ids:
        result = await db.execute(
            select(ClientRecord).where(
                ClientRecord.upload_id.in_(all_needed_ids),
                ClientRecord.user_id == user_id,
            )
        )
        for r in result.scalars().all():
            if not r.id_number:
                continue
            # Detect which categories are covered by commission files
            product = (r.fund_type or r.product or "").lower()
            if product:
                if any(kw in product for kw in _GEMEL_KEYWORDS):
                    covered_categories.add("gemel_hishtalmut")
                if any(kw in product for kw in _INSURANCE_KEYWORDS):
                    covered_categories.add("insurance")
            # ONE definition of "commission actually received", shared with
            # every other aggregator. This loop used to try `commission_expected`
            # third, which `comparison_service._get_commission` documents as
            # forbidden: that column held ₪163,447 of Menora "פרמיה לעמלה"
            # misclassified as commission, and is a computed estimate elsewhere.
            # Including it here made the dashboard's "עמלות שהתקבלו" disagree
            # with the comparison tab's figure for the same month.
            comm_val = _get_commission({
                "commission_paid": r.commission_paid,
                "commission_before_fee": r.commission_before_fee,
                "actual_amount": r.actual_amount,
            })
            if comm_val is not None:
                try:
                    comm_val = float(comm_val)
                except (ValueError, TypeError):
                    comm_val = None
            if comm_val is not None and comm_val != 0:
                if r.upload_id not in records_by_upload:
                    records_by_upload[r.upload_id] = {}
                rec = records_by_upload[r.upload_id]
                rec[r.id_number] = round(rec.get(r.id_number, 0.0) + comm_val, 2)

    # Aggregate across uploads for each period
    def _aggregate(upload_ids):
        combined = {}
        for uid in upload_ids:
            for id_num, val in records_by_upload.get(uid, {}).items():
                combined[id_num] = combined.get(id_num, 0.0) + val
        return combined

    current_comm = _aggregate(current_upload_ids)
    previous_comm = _aggregate(previous_upload_ids)

    # Per-company detail for current period: {id_number: [{company, commission}, ...]}
    current_comm_detail = {}
    for uid in current_upload_ids:
        company = upload_meta.get(uid, {}).get("company", "?")
        for id_num, val in records_by_upload.get(uid, {}).items():
            if id_num not in current_comm_detail:
                current_comm_detail[id_num] = []
            current_comm_detail[id_num].append({
                "company": company,
                "commission": round(val, 2),
            })

    return current_comm, previous_comm, has_data, has_previous, current_comm_detail, covered_categories


@router.post("/compare", response_model=ProductionCompareResponse)
async def compare_productions(
    req: CompareRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Compare two production files: new/removed/changed clients."""
    current_id = uuid.UUID(req.current_upload_id)
    previous_id = uuid.UUID(req.previous_upload_id)

    # Fetch upload metadata for file names/dates
    current_upload = await db.execute(
        select(FileUpload).where(FileUpload.id == current_id, FileUpload.user_id == user.id)
    )
    current_file = current_upload.scalar_one_or_none()
    previous_upload = await db.execute(
        select(FileUpload).where(FileUpload.id == previous_id, FileUpload.user_id == user.id)
    )
    previous_file = previous_upload.scalar_one_or_none()

    # Fetch records for both uploads (scoped by user_id)
    async def _fetch_grouped(upload_id):
        result = await db.execute(
            select(ClientRecord).where(
                ClientRecord.upload_id == upload_id,
                ClientRecord.user_id == user.id,
            )
        )
        records = result.scalars().all()
        grouped = {}
        for r in records:
            if not r.id_number:
                continue
            if r.id_number not in grouped:
                grouped[r.id_number] = {
                    "name": f"{r.first_name or ''} {r.last_name or ''}".strip(),
                    "company": r.receiving_company or "",
                    "premium": 0.0,
                    "accumulation": 0.0,
                    "products_count": 0,
                    "product_types": [],
                    "statuses": [],
                    "categories": set(),
                }
            g = grouped[r.id_number]
            g["premium"] += float(r.total_premium or 0)
            g["accumulation"] += float(r.accumulation or 0)
            g["products_count"] += 1
            if r.product_status:
                g["statuses"].append(r.product_status)
            if r.product_type:
                g["product_types"].append(r.product_type)
            cat = _classify_product_type(r.product_type)
            if cat:
                g["categories"].add(cat)
        return grouped

    current = await _fetch_grouped(current_id)
    previous = await _fetch_grouped(previous_id)

    # ── Commission lookup: split by previous production upload date ──
    # For each filename: current = latest overall, previous = latest before prev date
    # Files not re-uploaded → same data both sides → diff = 0 (honest)
    prev_date = previous_file.uploaded_at if previous_file else None
    cur_period = getattr(current_file, "period_month", None)
    prev_period = getattr(previous_file, "period_month", None) if previous_file else None
    current_comm, previous_comm, has_commission_data, has_previous_commission, current_comm_detail, covered_categories = await _build_commission_lookups(
        db, user.id, prev_date,
        current_period_month=cur_period,
        previous_period_month=prev_period,
    )

    current_ids = set(current.keys())
    previous_ids = set(previous.keys())

    new_ids = current_ids - previous_ids
    removed_ids = previous_ids - current_ids
    common_ids = current_ids & previous_ids

    def _comm_fields(cid):
        curr = round(current_comm.get(cid, 0.0), 2)
        detail = current_comm_detail.get(cid, [])
        if has_previous_commission:
            prev = round(previous_comm.get(cid, 0.0), 2)
            return {
                "commission": curr,
                "commission_prev": prev,
                "commission_diff": round(curr - prev, 2),
                "commission_details": detail,
            }
        # No previous commission data — don't fake a diff
        return {
            "commission": curr,
            "commission_prev": None,
            "commission_diff": None,
            "commission_details": detail,
        }

    new_clients = []
    for cid in sorted(new_ids):
        c = current[cid]
        new_clients.append({"id_number": cid, "name": c["name"], "company": c["company"],
                            "premium": round(c["premium"], 2), "accumulation": round(c["accumulation"], 2),
                            "products_count": c["products_count"],
                            "product_types": list(set(c["product_types"])),
                            **_comm_fields(cid)})

    removed_clients = []
    for cid in sorted(removed_ids):
        p = previous[cid]
        removed_clients.append({"id_number": cid, "name": p["name"], "company": p["company"],
                                "premium": round(p["premium"], 2), "accumulation": round(p["accumulation"], 2),
                                "products_count": p["products_count"],
                                "product_types": list(set(p["product_types"])),
                                **_comm_fields(cid)})

    changed_clients = []
    unchanged_clients = []
    for cid in sorted(common_ids):
        c = current[cid]
        p = previous[cid]
        changes = []
        premium_diff = round(c["premium"] - p["premium"], 2)
        accum_diff = round(c["accumulation"] - p["accumulation"], 2)

        if abs(premium_diff) > 0.01:
            changes.append({"field": "פרמיה", "old_val": round(p["premium"], 2), "new_val": round(c["premium"], 2)})
        if abs(accum_diff) > 0.01:
            changes.append({"field": "צבירה", "old_val": round(p["accumulation"], 2), "new_val": round(c["accumulation"], 2)})
        if c["products_count"] != p["products_count"]:
            changes.append({"field": "מוצרים", "old_val": p["products_count"], "new_val": c["products_count"]})

        if changes:
            changed_clients.append({
                "id_number": cid, "name": c["name"], "company": c["company"],
                "premium": round(c["premium"], 2), "accumulation": round(c["accumulation"], 2),
                "products_count": c["products_count"],
                "changes": changes, "premium_diff": premium_diff, "accumulation_diff": accum_diff,
                **_comm_fields(cid),
            })
        else:
            unchanged_clients.append({
                "id_number": cid, "name": c["name"], "company": c["company"],
                "premium": round(c["premium"], 2), "accumulation": round(c["accumulation"], 2),
                "products_count": c["products_count"],
                **_comm_fields(cid),
            })

    # Positive/negative split for premium and accumulation diffs
    premium_positive = sum(1 for c in changed_clients if c["premium_diff"] > 0.01)
    premium_negative = sum(1 for c in changed_clients if c["premium_diff"] < -0.01)
    accum_positive = sum(1 for c in changed_clients if c["accumulation_diff"] > 0.01)
    accum_negative = sum(1 for c in changed_clients if c["accumulation_diff"] < -0.01)

    # Commission totals — sum across EVERY commission record, not only IDs
    # in the current production file. Clients can earn commissions even if
    # they're no longer in the active production export (residual payments
    # on policies the agent placed years ago). The previous "scoped to
    # production clients only" semantics under-reported the real total by
    # ~4× (₪37K vs ₪158K).
    commission_total = round(sum(current_comm.values()), 2)
    if has_previous_commission:
        commission_prev_total = round(sum(previous_comm.values()), 2)
        commission_diff_total = round(commission_total - commission_prev_total, 2)
    else:
        commission_prev_total = None
        commission_diff_total = None

    # Commission diff counts across ALL current production clients
    all_clients_with_data = new_clients + removed_clients + changed_clients + unchanged_clients
    commission_diff_positive = sum(1 for c in all_clients_with_data if (c.get("commission_diff") or 0) > 0.01)
    commission_diff_negative = sum(1 for c in all_clients_with_data if (c.get("commission_diff") or 0) < -0.01)

    # Count clients with/without commission from current commission data
    # Only count "ללא עמלה" for clients whose product category is covered by uploaded commission files
    commission_positive_count = sum(1 for cid in current_ids if current_comm.get(cid, 0) > 0)
    commission_zero_count = 0
    for cid in current_ids:
        if current_comm.get(cid, 0) == 0:
            client_cats = current[cid].get("categories", set())
            # Count as "ללא עמלה" only if any of client's categories has commission data
            if client_cats & covered_categories:
                commission_zero_count += 1
            elif not client_cats and covered_categories:
                # Unknown category but we have some commission data — count conservatively
                commission_zero_count += 1

    # Commission breakdown by company — aggregate EVERY commission record,
    # not only those for current-production IDs. Matches the total above
    # and gives the true per-company picture (Phoenix ₪97K leader, not the
    # ₪1.4K that scoping-to-production showed).
    company_totals = {}  # company → {total, clients}
    for cid, entries in current_comm_detail.items():
        for entry in entries:
            co = entry["company"]
            if co not in company_totals:
                company_totals[co] = {"total": 0.0, "clients": set()}
            company_totals[co]["total"] += entry["commission"]
            if entry["commission"] != 0:
                company_totals[co]["clients"].add(cid)
    commission_by_company = sorted([
        {"company": co, "total": round(data["total"], 2), "clients_count": len(data["clients"])}
        for co, data in company_totals.items()
        if data["total"] != 0
    ], key=lambda x: -abs(x["total"]))

    # ── EXPECTED COMMISSION (from production × agreement rates) ──────────
    # For gemel/savings: monthly expected = accumulation × annual_rate / 12
    # For insurance:     monthly expected = premium × rate
    # Independent of whether נפרעים files exist — answers "how much SHOULD
    # I earn this month per my agreements?". User asked: "for גמל,
    # מתוך הצבירה הוא צריך לחשב את הנפרעים הצפויים לפי טבלת העמלות".
    from app.models.commission_rate import CommissionRate
    rates_q = await db.execute(
        select(CommissionRate).where(CommissionRate.user_id == user.id)
    )
    user_rates = list(rates_q.scalars().all())

    # Expected commission per agreement rates over the CURRENT production file.
    # Insurance uses per-product rates (השתלות 7.2%, חיים 11%, …), gemel uses
    # accum × rate / 12 — all handled by the shared helper so the dashboard,
    # the monthly insights view, and the AI chat report identical numbers.
    cur_prod_q = await db.execute(
        select(
            ClientRecord.id_number,
            ClientRecord.receiving_company,
            ClientRecord.product_type,
            ClientRecord.product,
            ClientRecord.total_premium,
            ClientRecord.accumulation,
        ).where(ClientRecord.upload_id == current_id, ClientRecord.user_id == user.id)
    )
    expected_commission_total, expected_commission_by_company = compute_expected_commission(
        cur_prod_q.all(), user_rates
    )

    summary = {
        "new_count": len(new_clients),
        "removed_count": len(removed_clients),
        "changed_count": len(changed_clients),
        "unchanged_count": len(unchanged_clients),
        "total_current": len(current),
        "total_previous": len(previous),
        "has_commission_data": has_commission_data,
        "has_previous_commission": has_previous_commission,
        "commission_total": round(commission_total, 2),
        "commission_prev_total": round(commission_prev_total, 2) if commission_prev_total is not None else None,
        "commission_diff_total": commission_diff_total,
        "commission_diff_positive": commission_diff_positive,
        "commission_diff_negative": commission_diff_negative,
        "commission_positive_count": commission_positive_count,
        "commission_zero_count": commission_zero_count,
        "commission_by_company": commission_by_company,
        # Expected commission per agreement rates (independent of נפרעים files).
        # Lets the agent see "how much I SHOULD earn this month" before
        # commissions actually arrive. Gap = expected - actual = unpaid/late.
        "expected_commission_total": expected_commission_total,
        "expected_commission_by_company": expected_commission_by_company,
        "premium_positive": premium_positive,
        "premium_negative": premium_negative,
        "accum_positive": accum_positive,
        "accum_negative": accum_negative,
        "current_filename": current_file.filename if current_file else "",
        "current_date": current_file.uploaded_at.isoformat() if current_file else "",
        "previous_filename": previous_file.filename if previous_file else "",
        "previous_date": previous_file.uploaded_at.isoformat() if previous_file else "",
    }

    return ProductionCompareResponse(
        summary=summary,
        new_clients=new_clients,
        removed_clients=removed_clients,
        changed_clients=changed_clients,
        unchanged_clients=unchanged_clients,
    )


# Commission format types (for backfilling file_category)
COMMISSION_FORMATS = {
    "agent_tracking", "company_report", "nifraim",
    "hachshara_nifraim", "menora", "altshuler",
    "clal_life_nifraim", "clal_health_nifraim", "migdal_nifraim",
    "ayalon_nifraim", "harel_nifraim", "phoenix_insurance_nifraim",
}


@router.post("/backfill-periods")
async def backfill_period_months(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """One-time backfill: set period_month on PRODUCTION uploads whose value is NULL.

    Production uploads via /api/production/upload historically didn't run
    detect_period_month, so their period_month is NULL even though the filename
    contains a clear month name. Without period_month, the trend chart can't
    anchor commission periods to production periods. This re-runs detection
    using filename + uploaded_at.

    NOTE: Commission files are intentionally excluded. Their period_month should
    only be set when the filename or data dates make it unambiguous — falling
    back to upload_at for a commission file mis-tags duplicate/summary files
    (e.g. Phoenix's "עמלות" file overlaps גמל/בריאות/ביטוח of the same period
    and would double-count the company total when forcibly anchored).
    """
    from app.services.parser_service import detect_period_month

    q = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user.id,
            FileUpload.period_month.is_(None),
            FileUpload.file_category == "production",
        )
    )
    uploads = q.scalars().all()
    updated = 0
    for u in uploads:
        pm = detect_period_month(u.filename, None, uploaded_at=u.uploaded_at)
        if pm is not None:
            u.period_month = pm
            updated += 1
    await db.commit()
    return {"updated": updated, "total_null_production": len(uploads)}


@router.post("/redetect-commission-periods")
async def redetect_commission_periods(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Re-run detect_period_month on every commission upload using its FULL records
    (sign_date / transfer_date / rights_assignment_date / processing_date) so
    period_month is rebuilt from real data dates, not the upload_at fallback.

    Use after `reset-commission-periods` over-cleared period_months.
    Files with no filename hint AND no usable record dates stay NULL — that's
    the correct outcome for Phoenix's "עמלות … כולל הראל" summary files which
    overlap other files of the same period.
    """
    from app.services.parser_service import detect_period_month

    q = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user.id,
            FileUpload.file_category == "commission",
        )
    )
    uploads = q.scalars().all()

    set_count = 0
    cleared_count = 0
    for u in uploads:
        # Fetch records for this upload (date columns only)
        rec_q = await db.execute(
            select(
                ClientRecord.sign_date,
                ClientRecord.transfer_date,
                ClientRecord.rights_assignment_date,
                ClientRecord.processing_date,
            ).where(ClientRecord.upload_id == u.id)
        )
        recs = [
            {
                "sign_date": r[0],
                "transfer_date": r[1],
                "rights_assignment_date": r[2],
                "processing_date": r[3],
            }
            for r in rec_q.all()
        ]
        # Pass uploaded_at=None — we DO NOT want the upload-date fallback for
        # commission files. Only filename + data dates count.
        pm = detect_period_month(u.filename, recs, uploaded_at=None)
        if pm != u.period_month:
            u.period_month = pm
            if pm is None:
                cleared_count += 1
            else:
                set_count += 1
    await db.commit()
    return {"set": set_count, "cleared": cleared_count, "total_checked": len(uploads)}


@router.post("/reset-commission-periods")
async def reset_commission_periods(
    only_filename_substring: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Reset period_month back to NULL on commission uploads that were tagged
    via upload_at fallback (filename has no month indicator). Default scope:
    every commission file whose filename has no Hebrew month name AND no
    numeric MM/YY token — these are the files most likely to be mis-tagged.

    Pass `only_filename_substring=...` to limit to one file (e.g. "כולל הראל").
    """
    import re
    from app.services.parser_service import _HE_MONTH_TO_INT, _RE_NUM_MONTH

    HE_MONTHS = set(_HE_MONTH_TO_INT.keys())

    q = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user.id,
            FileUpload.file_category == "commission",
            FileUpload.period_month.isnot(None),
        )
    )
    uploads = q.scalars().all()
    cleared = 0
    affected = []
    for u in uploads:
        fname = u.filename or ""
        if only_filename_substring and only_filename_substring not in fname:
            continue
        has_he_month = any(m in fname for m in HE_MONTHS)
        has_num_month = bool(_RE_NUM_MONTH.search(fname))
        if not has_he_month and not has_num_month:
            affected.append({"filename": fname, "was": u.period_month.isoformat()})
            u.period_month = None
            cleared += 1
    await db.commit()
    return {"cleared": cleared, "affected": affected}


@router.post("/backfill-categories")
async def backfill_file_categories(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """One-time backfill: set file_category on existing uploads based on format_type."""
    result = await db.execute(
        select(FileUpload).where(
            FileUpload.user_id == user.id,
            FileUpload.file_category.in_((None, "general")),
        )
    )
    uploads = result.scalars().all()
    updated = 0
    for u in uploads:
        if u.format_type == "production":
            u.file_category = "production"
            updated += 1
        elif u.format_type in COMMISSION_FORMATS:
            u.file_category = "commission"
            updated += 1
    await db.commit()
    return {"updated": updated, "total_checked": len(uploads)}


@router.post("/backfill-summaries")
async def backfill_summaries(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """One-time backfill: compute production summaries for all historical uploads."""
    from app.services.summary_service import compute_production_summary

    result = await db.execute(
        select(FileUpload)
        .where(
            FileUpload.user_id == user.id,
            FileUpload.file_category == "production",
        )
        .order_by(FileUpload.uploaded_at)
    )
    uploads = result.scalars().all()
    created = 0
    for u in uploads:
        summary = await compute_production_summary(db, user.id, u.id)
        if summary:
            created += 1
    return {"created": created, "total_uploads": len(uploads)}
