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
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select, desc, and_, delete as sql_delete
from sqlalchemy.exc import IntegrityError
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


def _parse_iso_date(value) -> date | None:
    """Parse a YYYY-MM-DD string from Claude. Lenient — silently returns None
    on garbage so a malformed date doesn't blow up the whole upsert."""
    if not value:
        return None
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except (ValueError, TypeError):
        return None


def _upsert_rates_from_doc(
    db: AsyncSession,
    user_id: UUID,
    doc_id: UUID,
    rates: list[dict],
    existing_rates_by_key: dict[tuple[str, str | None, str | None, Decimal, date | None, str | None], CommissionRate],
) -> int:
    """Insert/update commission_rates rows for the extracted entries.

    Each extracted `rate` row now carries a `components[]` array (book /
    reward / addition / total / single), each optionally tagged with a
    policy-year `scope` (e.g. "שנה 1-5"). We unfold each row into one DB row
    PER component, tagged with `rate_kind` + `rate_scope`, plus an optional
    `total` row when the document literally printed a סה״כ value. `addition`
    components are intentionally NOT inserted as standalone DB rows — they
    only make sense alongside a `book`.

    Upsert key matches the DB-level uniqueness index `uq_commission_rates_keys`:
    (user_id, company_name, product, frequency, rate, effective_from, rate_scope).
    `rate_kind` is NOT part of the key so re-extracting the same rate as a
    different kind is treated as the same row (the new label wins). `rate_scope`
    IS part of the key so same-value year tiers of a product don't collapse.
    """
    touched = 0
    seen_keys: set[tuple[str, str | None, str | None, Decimal, date | None, str | None]] = set()

    def _flat_components(r: dict) -> list[tuple[str, Decimal, str | None]]:
        """Yield (kind, rate_decimal, scope) tuples from the extracted row.
        Falls back to the legacy rate_percent when components[] is empty."""
        out: list[tuple[str, Decimal, str | None]] = []
        comps = r.get("components")
        if isinstance(comps, list) and comps:
            for c in comps:
                if not isinstance(c, dict):
                    continue
                kind = (c.get("kind") or "single").strip().lower()
                # addition rows are deltas, not standalone — skip insert
                if kind == "addition":
                    continue
                try:
                    p = Decimal(str(c.get("rate_percent")))
                except (InvalidOperation, TypeError):
                    continue
                if p <= 0 or p > 100:
                    continue
                scope_raw = c.get("scope")
                scope = (str(scope_raw).strip()[:40] or None) if scope_raw else None
                out.append((kind, p, scope))
        # `total` is its own row if literally printed in the doc
        total = r.get("total_rate_percent")
        if total is not None:
            try:
                t = Decimal(str(total))
                if 0 < t <= 100:
                    out.append(("total", t, None))
            except (InvalidOperation, TypeError):
                pass
        # Legacy single-number fallback
        if not out and r.get("rate_percent") is not None:
            try:
                p = Decimal(str(r.get("rate_percent")))
                if 0 < p <= 100:
                    out.append(("single", p, None))
            except (InvalidOperation, TypeError):
                pass
        return out

    for r in rates:
        company = (r.get("company") or "").strip()
        if not company:
            continue
        product_raw = r.get("product")
        product = (str(product_raw).strip()[:200] or None) if product_raw else None
        frequency_raw = r.get("frequency")
        frequency = (str(frequency_raw).strip()[:20] or None) if frequency_raw else None
        eff_from = _parse_iso_date(r.get("effective_from"))
        eff_to = _parse_iso_date(r.get("effective_to"))

        for kind, percent, scope in _flat_components(r):
            rate_val = (percent / Decimal(100)).quantize(Decimal("0.0001"))
            key = (company[:100], product, frequency, rate_val, eff_from, scope)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            existing = existing_rates_by_key.get(key)
            if existing is not None:
                # Same key already in DB — retag with the new doc + refresh the
                # end-date (in case the agreement was reuploaded with a longer
                # validity window). Also update rate_kind if we now know better.
                existing.source_document_id = doc_id
                existing.rate_kind = kind
                if eff_to is not None:
                    existing.effective_to = eff_to
            else:
                new_row = CommissionRate(
                    user_id=user_id,
                    company_name=company[:100],
                    product=product,
                    rate=rate_val,
                    rate_kind=kind,
                    rate_scope=scope,
                    payment_frequency=frequency,
                    effective_from=eff_from,
                    effective_to=eff_to,
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
        # Validity-dates were added to the extraction schema later. If the
        # cached rates don't carry effective_from/to we need a fresh run.
        cached_rates = (existing.structured_data or {}).get("rates") or []
        rates_have_dates = (
            not cached_rates
            or any(r.get("effective_from") or r.get("effective_to") for r in cached_rates)
        )
        # A ready doc with NO extracted rates but a rate-table-looking text
        # layer is an extraction miss (the מנורה case: ~40 products captured
        # into full_content, rates[] empty). Force a fresh run so the improved
        # prompt + rates-only fallback recover them.
        rates_missing = (not cached_rates) and (existing.extracted_text or "").count("%") >= 15
        if (existing.status == "ready" and cached_full and has_file
                and looks_complete and has_text_layer and rates_have_dates
                and not rates_missing):
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

            # Also refresh the commission_rates rows tied to this doc — the
            # reason we re-extracted in the first place is that the cached
            # rates were missing data (typically the new validity dates).
            # We first drop the doc's existing rate rows so old dateless
            # versions don't linger alongside the freshly-dated ones (the
            # upsert key includes effective_from, so a NULL-date row and a
            # dated row look like different keys).
            if extracted.get("rates"):
                await db.execute(sql_delete(CommissionRate).where(
                    CommissionRate.user_id == user.id,
                    CommissionRate.source_document_id == existing.id,
                ))
                await db.flush()
                _upsert_rates_from_doc(db, user.id, existing.id, extracted["rates"], {})
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
            existing_by_key: dict[tuple[str, str | None, str | None, Decimal, date | None, str | None], CommissionRate] = {
                (r.company_name, r.product, r.payment_frequency, r.rate, r.effective_from, r.rate_scope): r
                for r in existing_rates_q.scalars().all()
            }
            _upsert_rates_from_doc(db, user.id, doc.id, extracted["rates"], existing_by_key)

    try:
        await db.commit()
    except IntegrityError as e:
        msg = str(e.orig)
        # Race condition: another concurrent upload of the same PDF (same
        # user + sha) committed between our dedupe SELECT and this commit.
        # Roll back, fetch the row that won, and return it.
        if "uq_ai_documents_user_sha" in msg:
            await db.rollback()
            winner_q = await db.execute(
                select(AiDocument).where(
                    AiDocument.user_id == user.id,
                    AiDocument.sha256 == sha,
                )
            )
            winner = winner_q.scalar_one_or_none()
            if winner is None:
                raise
            return winner
        # Duplicate commission_rate slipped through the in-memory dedupe
        # (e.g. two extractions inserting identical (user, company, product,
        # freq, rate) at the same time). Re-run the upsert with the DB's
        # post-conflict view: read the now-existing rows back and let the
        # second try see them as "existing" so nothing new is inserted.
        if "uq_commission_rates_keys" in msg:
            await db.rollback()
            # Re-fetch the doc row in this fresh transaction, plus the
            # winning commission_rate rows. The AiDocument was created in the
            # rolled-back transaction, so we have to start fresh.
            existing_doc_q = await db.execute(
                select(AiDocument).where(
                    AiDocument.user_id == user.id,
                    AiDocument.sha256 == sha,
                )
            )
            cached_doc = existing_doc_q.scalar_one_or_none()
            if cached_doc is not None:
                return cached_doc
        raise
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
