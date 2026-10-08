"""Customer policies: הר הביטוח request status (the chat follower), a customer's policies for the
contacts card, and policy PDF upload (→ Claude Markdown → embedded). All user-scoped."""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_paid_user
from app.database import async_session, get_db
from app.models.harb_request import HarbRequest
from app.models.policy_document import PolicyDocument
from app.models.portal_run import PortalRun
from app.models.user import User
from app.services.policies import harb_jobs, store

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_PDF = 25 * 1024 * 1024
_BG: set = set()   # strong refs — a bare create_task can be garbage-collected mid-conversion
STUCK = timedelta(minutes=15)


async def _expire_processing(db, user_id) -> None:
    """A restart mid-conversion leaves a document 'processing' forever (and the drill polling)."""
    from sqlalchemy import update
    await db.execute(update(PolicyDocument).where(
        PolicyDocument.user_id == user_id, PolicyDocument.status == "processing",
        PolicyDocument.created_at < datetime.utcnow() - STUCK)
        .values(status="failed", error="הקריאה נקטעה — העלו את הפוליסה שוב"))
    await db.commit()
# The docker volume in production; a repo-local folder in dev (no /app there).
STORAGE = Path(os.environ.get("POLICY_DOC_STORAGE_DIR")
               or ("/app/data/policy_documents" if Path("/app/data").is_dir()
                   else str(Path(__file__).resolve().parents[2] / "data" / "policy_documents")))

STATUS_HE = {
    "pending": "ממתין בתור", "running": "מתחבר להר הביטוח…", "awaiting_otp": "ממתין לקוד SMS…",
    "downloading": "מוריד את התיק הביטוחי…", "done": "התיק הביטוחי התקבל",
    "failed": "השליפה נכשלה", "not_found": "הר הביטוח לא מצא את הלקוח",
}


@router.get("/harb-requests/{request_id}")
async def harb_request_status(request_id: UUID, db: AsyncSession = Depends(get_db),
                              user: User = Depends(get_paid_user)):
    req = await db.get(HarbRequest, request_id)
    if not req or req.user_id != user.id:
        raise HTTPException(404, "לא נמצא")
    if await harb_jobs.repair_stale(db, user.id):
        await db.refresh(req)
    run = await db.get(PortalRun, req.portal_run_id) if req.portal_run_id else await harb_jobs.active_run(db, user.id)
    st = harb_jobs.effective_status(req, run)
    err = req.error or (run.error_message if st == "failed" and run else None)
    return {"id": str(req.id), "status": st, "status_he": STATUS_HE.get(st, st), "error": err,
            "customer_id_number": req.customer_id_number, "customer_name": req.customer_name,
            "policies_count": req.policies_count, "completed_at": req.completed_at}


@router.get("/customers/{id_number}")
async def customer_policies(id_number: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    await _expire_processing(db, user.id)
    return await store.customer_picture(db, user.id, id_number)


@router.get("/documents/{doc_id}")
async def get_document(doc_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    d = await db.get(PolicyDocument, doc_id)
    if not d or d.user_id != user.id:
        raise HTTPException(404, "לא נמצא")
    return {"id": str(d.id), "title": d.title, "source": d.source, "company": d.company,
            "policy_number": d.policy_number, "customer_id_number": d.customer_id_number,
            "status": d.status, "error": d.error, "markdown": d.markdown, "has_file": bool(d.file_path),
            "filename": d.filename, "created_at": d.created_at}


@router.get("/documents/{doc_id}/file")
async def get_document_file(doc_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    d = await db.get(PolicyDocument, doc_id)
    if not d or d.user_id != user.id or not d.file_path or not Path(d.file_path).exists():
        raise HTTPException(404, "הקובץ לא נמצא")
    name = quote(d.filename or "policy.pdf")
    return FileResponse(d.file_path, media_type="application/pdf",
                        headers={"Content-Disposition": f"inline; filename*=UTF-8''{name}"})


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    d = await db.get(PolicyDocument, doc_id)
    if not d or d.user_id != user.id:
        raise HTTPException(404, "לא נמצא")
    if d.file_path:
        try:
            Path(d.file_path).unlink(missing_ok=True)
        except OSError:
            pass
    await db.delete(d)
    await db.commit()
    return {"ok": True}


@router.post("/upload")
async def upload_policy(file: UploadFile = File(...), id_number: str = Form(""),
                        db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    """Store the PDF now, convert in the background (a 15-page policy is ~100s of Claude).
    The card polls GET /documents/{id} until status leaves 'processing'."""
    data = await file.read()
    if not data or len(data) > MAX_PDF:
        raise HTTPException(400, "קובץ ריק או גדול מ-25MB")
    if not data[:5] == b"%PDF-":
        raise HTTPException(400, "אפשר להעלות רק PDF של פוליסה")
    digest = store.sha(data)
    dup = (await db.execute(select(PolicyDocument).where(PolicyDocument.user_id == user.id,
                                                         PolicyDocument.sha256 == digest))).scalar_one_or_none()
    if dup:
        stuck = dup.status == "processing" and dup.created_at < datetime.utcnow() - STUCK
        if dup.status != "failed" and not stuck:
            return {"id": str(dup.id), "status": dup.status, "duplicate": True}
        # the same file again after a failure / a restart mid-conversion → convert it again (same row)
        dup.status, dup.error, dup.created_at = "processing", None, datetime.utcnow()
        await db.commit()
        task = asyncio.create_task(_convert(dup.id, data, file.filename or "policy.pdf", store.norm_id(id_number) or None))
        _BG.add(task)
        task.add_done_callback(_BG.discard)
        return {"id": str(dup.id), "status": "processing", "retried": True}
    idn = store.norm_id(id_number) or None
    doc = PolicyDocument(user_id=user.id, customer_id_number=idn, source="pdf",
                         title=(file.filename or "פוליסה")[:300], filename=(file.filename or "policy.pdf")[:300],
                         sha256=digest, status="processing")
    db.add(doc)
    await db.flush()
    folder = STORAGE / str(user.id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{doc.id}.pdf"
    path.write_bytes(data)
    doc.file_path = str(path)
    await db.commit()
    task = asyncio.create_task(_convert(doc.id, data, file.filename or "policy.pdf", idn))
    _BG.add(task)
    task.add_done_callback(_BG.discard)
    return {"id": str(doc.id), "status": "processing"}


async def _convert(doc_id: UUID, data: bytes, filename: str, idn: str | None) -> None:
    from app.services.policies.embeddings import index_safely
    from app.services.policies.pdf_policy import extract_policy_pdf
    async with async_session() as db:
        doc = await db.get(PolicyDocument, doc_id)
        if doc is None:
            return
        try:
            out = await extract_policy_pdf(data, filename)
            doc.markdown = out["markdown"]
            doc.title = out["title"]
            doc.company = (out.get("company") or None)
            doc.policy_number = (out.get("policy_number") or None)
            insured = [i for i in out.get("insured") or [] if i.get("id_number")]
            if not idn and insured:
                # the agent didn't say whose — the first insured the policy names
                doc.customer_id_number = insured[0]["id_number"]
            who = next((i for i in insured if i["id_number"] == doc.customer_id_number), None)
            doc.customer_name = (who or {}).get("name") or None
            doc.status = "ready" if doc.markdown else "failed"
            doc.error = (None if doc.markdown else
                         "המסמך ריק או שאינו פוליסת ביטוח" if not out.get("is_policy", True) else "לא הצלחנו לקרוא את הפוליסה")
            await db.commit()
            logger.info("policies: %s converted in %ss", doc_id, out.get("timing", {}).get("total"))
            if doc.status == "ready":
                await index_safely(db, doc)
        except Exception as e:  # noqa: BLE001
            logger.exception("policies: converting %s failed", doc_id)
            await db.rollback()
            doc = await db.get(PolicyDocument, doc_id)
            if doc:
                doc.status, doc.error = "failed", f"קריאת הפוליסה נכשלה: {str(e)[:300]}"
                await db.commit()


@router.get("/customers")
async def customers(db: AsyncSession = Depends(get_db), user: User = Depends(get_paid_user)):
    """Every customer with policies (הר הביטוח or an uploaded PDF), with totals — the contacts app."""
    await _expire_processing(db, user.id)
    pics = await store.all_pictures(db, user.id)
    loose = (await db.execute(select(PolicyDocument).where(
        PolicyDocument.user_id == user.id, PolicyDocument.customer_id_number.is_(None))
        .order_by(PolicyDocument.created_at.desc()).limit(50))).scalars().all()
    return {
        "customers": [{"id_number": i, "customer_name": p["customer_name"], "totals": p["totals"],
                       "fetched_at": p["fetched_at"], "documents": len(p["documents"]),
                       "processing": sum(1 for d in p["documents"] if d["status"] == "processing")}
                      for i, p in pics.items()],
        # uploaded PDFs whose customer is not known yet (no ID given, none found in the policy)
        "unassigned": [{"id": str(d.id), "title": d.title, "status": d.status, "error": d.error,
                        "company": d.company, "created_at": d.created_at} for d in loose],
    }
