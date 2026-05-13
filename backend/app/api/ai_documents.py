"""AI document upload + management.

Users upload PDFs (e.g. commission agreements). We extract structured data
via Claude once, persist it in `ai_documents`, and upsert any commission
rates found into `commission_rates` (linked back via source_document_id).

Subsequent AI chat requests pull from `ai_documents` directly — no
re-parsing, no re-uploading.
"""
import hashlib
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)

# Files live on the persistent docker volume. Override with AI_DOC_STORAGE_DIR
# in tests / alternate envs.
DOC_STORAGE_DIR = Path(os.environ.get("AI_DOC_STORAGE_DIR", "/app/data/ai_documents"))


def _save_pdf_to_disk(user_id: UUID, doc_id: UUID, file_bytes: bytes) -> str:
    user_dir = DOC_STORAGE_DIR / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    path = user_dir / f"{doc_id}.pdf"
    path.write_bytes(file_bytes)
    return str(path)

from app.api.deps import get_paid_user
from app.database import get_db
from app.models.ai_document import AiDocument
from app.models.commission_rate import CommissionRate
from app.models.user import User
from app.schemas.ai_document import AiDocumentListItem, AiDocumentOut
from app.services.document_extraction import extract_pdf


router = APIRouter()

MAX_PDF_BYTES = 25 * 1024 * 1024  # 25 MB Anthropic limit for documents


def _upsert_rates_from_doc(
    db: AsyncSession,
    user_id: UUID,
    doc_id: UUID,
    rates: list[dict],
    existing_rates_by_company: dict[str, CommissionRate],
) -> int:
    """Insert/update commission_rates rows for the extracted entries.

    Upsert key: (user_id, company_name). When a rate already exists for the
    company we update its `rate` and tag `source_document_id`; otherwise we
    insert a new row.

    Returns the count of rows touched.
    """
    # commission_rates.rate is Numeric(6,4) storing FRACTIONS (0.005 = 0.5%),
    # not percent. Claude returns rate_percent (e.g. 4.5 → 4.5%), so divide
    # by 100. Values outside (0, 100]% are likely fund fees / caps, not
    # commission rates — skip them rather than overflow the column.
    touched = 0
    for r in rates:
        company = (r.get("company") or "").strip()
        if not company:
            continue
        try:
            percent = Decimal(str(r.get("rate_percent")))
        except (InvalidOperation, TypeError):
            continue
        if percent <= 0 or percent > 100:
            continue
        rate_val = (percent / Decimal(100)).quantize(Decimal("0.0001"))

        existing = existing_rates_by_company.get(company)
        if existing is not None:
            existing.rate = rate_val
            existing.source_document_id = doc_id
            if r.get("frequency"):
                existing.payment_frequency = str(r["frequency"])[:20]
        else:
            new_row = CommissionRate(
                user_id=user_id,
                company_name=company[:100],
                rate=rate_val,
                payment_frequency=(r.get("frequency") or None) and str(r["frequency"])[:20],
                source_document_id=doc_id,
            )
            db.add(new_row)
        touched += 1
    return touched


@router.post("/upload", response_model=AiDocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_paid_user),
):
    """Upload a PDF, extract its content, and persist for AI reuse."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="חסר שם קובץ")

    # We only accept PDFs for v1 — the extraction prompt + Claude document
    # block are PDF-specific.
    content_type = (file.content_type or "").lower()
    is_pdf = content_type == "application/pdf" or file.filename.lower().endswith(".pdf")
    if not is_pdf:
        raise HTTPException(status_code=400, detail="כרגע נתמכים רק קבצי PDF")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="הקובץ ריק")
    if len(file_bytes) > MAX_PDF_BYTES:
        raise HTTPException(status_code=400, detail="הקובץ גדול מ-25MB")

    sha = hashlib.sha256(file_bytes).hexdigest()

    # Dedupe: same user + same bytes → return the existing record without
    # re-calling Claude. This is the cache hit the user explicitly asked for.
    # Exception: if the cached record was extracted before we started capturing
    # full document text, refresh it once so the AI can answer doc-level Qs.
    existing_q = await db.execute(
        select(AiDocument).where(
            AiDocument.user_id == user.id,
            AiDocument.sha256 == sha,
        )
    )
    existing = existing_q.scalar_one_or_none()
    if existing is not None:
        cached_full = (existing.structured_data or {}).get("full_content") or ""
        has_file = existing.file_path and os.path.exists(existing.file_path)
        # Re-extract if any required section is absent — earlier extraction
        # prompts didn't require clawback / refund coverage, so docs uploaded
        # before that change are missing those answers.
        looks_complete = any(k in cached_full for k in ("ביטול", "החזר", "Clawback", "פדיון"))
        has_text_layer = bool(existing.extracted_text)
        if existing.status == "ready" and cached_full and has_file and looks_complete and has_text_layer:
            return existing
        try:
            extracted = await extract_pdf(file_bytes, file.filename)
            existing.doc_type = extracted.get("doc_type")
            existing.companies_mentioned = extracted.get("companies") or []
            existing.structured_data = extracted
            existing.summary = extracted.get("summary")
            existing.extracted_text = extracted.get("text_layer")
            existing.status = "ready"
            existing.error = None
            existing.processed_at = datetime.now(timezone.utc)
            if not has_file:
                try:
                    existing.file_path = _save_pdf_to_disk(user.id, existing.id, file_bytes)
                except OSError as e:
                    logger.warning(f"Could not persist PDF for {existing.id}: {e}")
            await db.commit()
            await db.refresh(existing)
        except Exception as e:
            existing.error = str(e)[:1000]
            await db.commit()
        return existing

    # Run the extraction up-front (synchronous in the request lifetime).
    # A typical commission agreement extraction takes 5–15 seconds.
    try:
        extracted = await extract_pdf(file_bytes, file.filename)
        status_val = "ready"
        err = None
    except Exception as e:
        extracted = {"doc_type": None, "companies": [], "summary": None, "rates": []}
        status_val = "error"
        err = str(e)[:1000]

    doc = AiDocument(
        user_id=user.id,
        filename=file.filename[:255],
        sha256=sha,
        size_bytes=len(file_bytes),
        doc_type=extracted.get("doc_type"),
        companies_mentioned=extracted.get("companies") or [],
        structured_data=extracted,
        summary=extracted.get("summary"),
        extracted_text=extracted.get("text_layer"),
        status=status_val,
        error=err,
        processed_at=datetime.now(timezone.utc),
    )
    db.add(doc)
    await db.flush()  # populate doc.id so rate rows can link back

    # Persist the raw PDF so chat queries can attach it back as a document
    # block — this is what gives the AI true Q&A on the source.
    try:
        doc.file_path = _save_pdf_to_disk(user.id, doc.id, file_bytes)
    except OSError as e:
        logger.warning(f"Could not persist PDF for {doc.id}: {e}")

    # Upsert extracted rates into commission_rates (only when extraction
    # succeeded and the doc actually has rate entries).
    if status_val == "ready" and extracted.get("rates"):
        companies_in_doc = {
            (r.get("company") or "").strip()
            for r in extracted["rates"]
            if r.get("company")
        }
        if companies_in_doc:
            existing_rates_q = await db.execute(
                select(CommissionRate).where(
                    CommissionRate.user_id == user.id,
                    CommissionRate.company_name.in_(companies_in_doc),
                )
            )
            existing_by_co = {r.company_name: r for r in existing_rates_q.scalars().all()}
            _upsert_rates_from_doc(db, user.id, doc.id, extracted["rates"], existing_by_co)

    await db.commit()
    await db.refresh(doc)
    return doc


@router.get("", response_model=list[AiDocumentListItem])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_paid_user),
):
    q = await db.execute(
        select(AiDocument)
        .where(AiDocument.user_id == user.id)
        .order_by(desc(AiDocument.uploaded_at))
    )
    return q.scalars().all()


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_paid_user),
):
    q = await db.execute(
        select(AiDocument).where(
            and_(AiDocument.id == doc_id, AiDocument.user_id == user.id)
        )
    )
    doc = q.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="מסמך לא נמצא")
    stored_path = doc.file_path
    await db.delete(doc)
    await db.commit()
    if stored_path:
        try:
            os.remove(stored_path)
        except OSError:
            pass
    return None
