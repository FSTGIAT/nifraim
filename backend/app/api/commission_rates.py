import os
import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.record import ClientRecord
from app.models.ai_document import AiDocument
from app.models.commission_rate import CommissionRate
from app.models.upload import FileUpload
from app.schemas.record import (
    CommissionRateIn,
    CommissionRateOut,
    RateCoverageOut,
    RateCoverageRow,
)
from app.api.deps import get_paid_user as get_current_user
from app.services.rate_select import explain_expected_commission
from app.utils.company_norm import company_stem
from app.utils.hebrew_mappings import DEFAULT_COMMISSION_RATES

router = APIRouter()


def _out(r: CommissionRate) -> CommissionRateOut:
    """Single serializer for a rate row. Was inlined four times, which is how
    `rate_kind` came to be written by the extractor, read by the matcher, and
    never sent to the browser."""
    return CommissionRateOut(
        id=str(r.id),
        company_name=r.company_name,
        product=r.product,
        rate=float(r.rate),
        rate_kind=r.rate_kind,
        rate_scope=r.rate_scope,
        payment_frequency=r.payment_frequency,
        paid_to=r.paid_to,
        company_email=r.company_email,
        effective_from=r.effective_from,
        effective_to=r.effective_to,
    )


@router.get("/agreements")
async def list_agreements(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """One card per company: which agreement PDF backs its rates.

    The shelf shows rates but never showed the DOCUMENT they came from, so an
    agent could not check a surprising percentage against the page it was read
    off — and an agreement that extracted **nothing** left no trace on the
    shelf at all. Live for this user that was 6 of 16 uploads (ילין, מור,
    מיטב, מגדל…), each invisible.

    A company is keyed by `company_stem` so 'מנורה מבטחים' and
    'מנורה מבטחים ביטוח בע"מ' share one card, matching how `select_rate`
    actually resolves a company.
    """
    rates = list((await db.execute(
        select(CommissionRate).where(CommissionRate.user_id == user.id)
    )).scalars().all())
    docs = list((await db.execute(
        select(AiDocument)
        .where(AiDocument.user_id == user.id)
        .order_by(AiDocument.uploaded_at.desc())
    )).scalars().all())

    # doc_id -> {stem: count} from the rates that actually link back to it.
    rates_by_doc: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    label_for_stem: dict[str, str] = {}
    rates_by_stem: dict[str, int] = defaultdict(int)
    for r in rates:
        stem = company_stem(r.company_name) or (r.company_name or "")
        if not stem:
            continue
        rates_by_stem[stem] += 1
        # Longest raw spelling wins as the label — it is the most informative
        # and matches what the agreement itself printed.
        if len(r.company_name or "") > len(label_for_stem.get(stem, "")):
            label_for_stem[stem] = r.company_name
        if r.source_document_id:
            rates_by_doc[str(r.source_document_id)][stem] += 1

    companies: dict[str, dict] = {}

    def _bucket(stem: str) -> dict:
        return companies.setdefault(stem, {
            "company": label_for_stem.get(stem, stem),
            "stem": stem,
            "rates_total": rates_by_stem.get(stem, 0),
            "documents": [],
        })

    for d in docs:
        sd = d.structured_data or {}
        extraction = sd.get("extraction") or {}
        entry = {
            "id": str(d.id),
            "filename": d.filename,
            "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
            "status": d.status,
            "error": d.error,
            # Whether the PDF is actually READABLE, not merely recorded.
            # The column stays set after a disk wipe, so trusting it
            # renders an enabled button that 404s.
            "has_file": bool(d.file_path and os.path.exists(d.file_path)),
            "rates": len(sd.get("rates") or []),
            # Why it produced nothing, when it produced nothing. Documents
            # extracted before this field existed simply carry None.
            "zero_reason": extraction.get("zero_reason"),
            "appendix_ref": extraction.get("appendix_ref"),
            "verified": extraction.get("verified"),
            "dropped": len(extraction.get("dropped") or []),
        }
        stems = set(rates_by_doc.get(str(d.id), {}))
        if not stems:
            # No rate links back — either it extracted nothing, or it predates
            # source_document_id. Fall back to the companies Claude named.
            stems = {
                company_stem(c) or c
                for c in (d.companies_mentioned or []) if c
            }
        for stem in (stems or {""}):
            if not stem:
                continue
            b = _bucket(stem)
            b["documents"].append({**entry, "rates": rates_by_doc.get(str(d.id), {}).get(stem, entry["rates"])})

    # Companies with rates but no document at all (seeded defaults).
    for stem in rates_by_stem:
        _bucket(stem)

    out = sorted(companies.values(), key=lambda c: (-c["rates_total"], c["company"]))
    return {"companies": out, "total_documents": len(docs)}


@router.get("", response_model=list[CommissionRateOut])
async def list_rates(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CommissionRate).where(CommissionRate.user_id == user.id)
    )
    return [_out(r) for r in result.scalars().all()]


@router.get("/coverage", response_model=RateCoverageOut)
async def rate_coverage(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """How much of the agent's ACTIVE production file the agreement shelf
    actually prices, and — for every company it doesn't — why.

    Exists because the expected-commission math fails by `continue`: a company
    whose name doesn't match, or whose records carry no premium, contributes ₪0
    and disappears with no error. The shelf shows percentages and counts and no
    money at all, so there was no surface on which an agent could notice that
    most of their portfolio was priced at nothing.
    """
    upload = (
        await db.execute(
            select(FileUpload)
            .where(FileUpload.user_id == user.id, FileUpload.is_production.is_(True))
            .order_by(FileUpload.uploaded_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not upload:
        return RateCoverageOut(has_production=False)

    rates = (
        await db.execute(
            select(CommissionRate).where(CommissionRate.user_id == user.id)
        )
    ).scalars().all()
    records = (
        await db.execute(
            select(
                ClientRecord.id_number,
                ClientRecord.receiving_company,
                ClientRecord.product,
                ClientRecord.product_type,
                ClientRecord.accumulation,
                ClientRecord.total_premium,
            ).where(ClientRecord.upload_id == upload.id)
        )
    ).all()

    total, _by_company, coverage = explain_expected_commission(records, list(rates))
    return RateCoverageOut(
        has_production=True,
        production_filename=upload.filename,
        total_records=sum(c["records"] for c in coverage),
        covered_records=sum(c["contributing"] for c in coverage),
        expected_total=total,
        rows=[RateCoverageRow(**c) for c in coverage],
    )


@router.post("/seed", response_model=list[CommissionRateOut])
async def seed_defaults(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seed the default commission rates from the rate table image."""
    # Check if user already has rates
    existing = await db.execute(
        select(CommissionRate).where(CommissionRate.user_id == user.id)
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Commission rates already exist. Delete them first to re-seed.")

    rates = []
    for item in DEFAULT_COMMISSION_RATES:
        rate = CommissionRate(
            user_id=user.id,
            company_name=item["company_name"],
            product=item.get("product"),
            rate=item["rate"],
            payment_frequency=item["payment_frequency"],
            paid_to=item["paid_to"],
            company_email=item.get("company_email"),
        )
        db.add(rate)
        rates.append(rate)

    await db.commit()
    for r in rates:
        await db.refresh(r)

    return [_out(r) for r in rates]


@router.post("", response_model=CommissionRateOut)
async def create_rate(
    data: CommissionRateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rate = CommissionRate(
        user_id=user.id,
        company_name=data.company_name,
        product=data.product,
        rate=data.rate,
        payment_frequency=data.payment_frequency,
        paid_to=data.paid_to,
        company_email=data.company_email,
        effective_from=data.effective_from,
        effective_to=data.effective_to,
    )
    if data.rate_kind:
        rate.rate_kind = data.rate_kind
    db.add(rate)
    await db.commit()
    await db.refresh(rate)
    return _out(rate)


@router.put("/{rate_id}", response_model=CommissionRateOut)
async def update_rate(
    rate_id: str,
    data: CommissionRateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CommissionRate).where(
            CommissionRate.id == uuid.UUID(rate_id),
            CommissionRate.user_id == user.id,
        )
    )
    rate = result.scalar_one_or_none()
    if not rate:
        raise HTTPException(status_code=404, detail="Rate not found")

    # Assign ONLY what the client actually sent. Assigning every field
    # unconditionally silently wiped the agreement's validity window: the
    # shelf's edit form has no date inputs, so `effective_from`/`effective_to`
    # arrived as their None defaults and editing a row's email cleared its
    # years — losing the window `commission_rate.py` documents as driving
    # sign-date matching.
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rate, field, value)
    await db.commit()
    await db.refresh(rate)

    return _out(rate)


@router.delete("/{rate_id}")
async def delete_rate(
    rate_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CommissionRate).where(
            CommissionRate.id == uuid.UUID(rate_id),
            CommissionRate.user_id == user.id,
        )
    )
    rate = result.scalar_one_or_none()
    if not rate:
        raise HTTPException(status_code=404, detail="Rate not found")

    await db.delete(rate)
    await db.commit()
    return {"status": "deleted"}
