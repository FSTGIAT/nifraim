"""Pension clearinghouse (המסלקה הפנסיונית) HTTP surface.

All routes are auth-gated via `get_paid_user` (same dep used by uploads).
Strict `user.id` scoping — a customer-id passed in a URL only resolves
against records owned by the requesting user; missing → 404.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_paid_user as get_current_user
from app.database import get_db
from app.models.pension_audit import PensionAuditLog
from app.models.pension_holding import PensionHolding
from app.models.pension_inquiry import PensionInquiry
from app.models.user import User
from app.schemas.maslaka import (
    AuditEntryOut,
    EnrichedPictureOut,
    InquiryCreateRequest,
    InquiryDetailOut,
    InquiryOut,
    PollStatsOut,
)
from pathlib import Path

from app.config import settings
from app.services.maslaka import orchestration
from app.services.maslaka.filenames import parse_filename
from app.services.mimshak import parse_mimshak_dat

router = APIRouter()


def require_maslaka_enabled() -> None:
    """Master gate: the clearinghouse is OFF until they open our vaults.

    `MASLAKA_ENABLED` is the Y/N switch (see config.py). While it is False the
    vault does not exist, `MASLAKA_AGENT_*` are unset, and the XML adapter still
    has open TODO(XSD) questions — so a request built now would be a guess sent
    to a regulator. Read-only routes stay open (they only touch our own DB);
    only the two routes that TRANSPORT anything are gated.
    """
    if not settings.MASLAKA_ENABLED:
        raise HTTPException(
            status_code=503,
            detail=(
                "המסלקה הפנסיונית עדיין לא פעילה — הכספת טרם נפתחה. "
                "(MASLAKA_ENABLED=false)"
            ),
        )


def require_vault_host() -> None:
    """Second gate: only the Gateway VM may TOUCH the vault.

    `MASLAKA_ENABLED` says the feature is live; `MASLAKA_VAULT_HOST` says this
    process is the Israeli box whose folders the Transporter syncs. On Railway the
    latter is false, so a poll here would list an empty container directory and
    report "0 files" forever. Refusing is honest; succeeding emptily is not.
    """
    if not settings.MASLAKA_VAULT_HOST:
        raise HTTPException(
            status_code=503,
            detail=(
                "פעולה זו רצה רק על שרת הכספת (Maslaka Gateway), לא על השרת בענן. "
                "(MASLAKA_VAULT_HOST=false)"
            ),
        )


# ─── Inquiry creation ──────────────────────────────────────────────────────
@router.post("/inquiry", response_model=InquiryOut, dependencies=[Depends(require_maslaka_enabled)])
async def create_inquiry_endpoint(
    payload: InquiryCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a `pending` inquiry row. **Does not send anything.**

    The send deliberately does NOT happen here. This used to be a FastAPI
    BackgroundTask, which runs on the host that served the request — Railway —
    where `transport.send()` writes the XML to a container disk the Transporter
    cannot see, reports success, and flips the row to `submitted`. The request
    was silently lost (docs/ARCHITECTURE.md §12 invariant #3).

    The row now sits `pending` until the Gateway VM's `maslaka_worker.py` claims
    it. There is no inline fallback, because on this host there is no send that
    could ever work — a pending row waiting for the Gateway is correct behaviour,
    not degraded behaviour.
    """
    inquiry = await orchestration.create_inquiry(
        db,
        user_id=user.id,
        customer_id_number=payload.customer_id_number,
        customer_name=payload.customer_name,
    )
    return _serialize_inquiry(inquiry)


# ─── Inquiry listing + detail ──────────────────────────────────────────────
@router.get("/inquiries", response_model=list[InquiryOut])
async def list_inquiries(
    status: str | None = Query(default=None),
    customer_id_number: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(PensionInquiry).where(PensionInquiry.user_id == user.id)
    if status:
        q = q.where(PensionInquiry.status == status)
    if customer_id_number:
        normalized = customer_id_number.lstrip("0") or "0"
        q = q.where(PensionInquiry.customer_id_number == normalized)
    q = q.order_by(desc(PensionInquiry.created_at)).limit(200)
    rows = (await db.execute(q)).scalars().all()
    return [_serialize_inquiry(r) for r in rows]


@router.get("/inquiry/{inquiry_id}", response_model=InquiryDetailOut)
async def inquiry_detail(
    inquiry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    inquiry = await db.get(PensionInquiry, inquiry_id)
    if inquiry is None or inquiry.user_id != user.id:
        raise HTTPException(status_code=404, detail="Inquiry not found")

    audit_rows = (await db.execute(
        select(PensionAuditLog)
        .where(PensionAuditLog.inquiry_id == inquiry.id)
        .order_by(PensionAuditLog.created_at.asc())
    )).scalars().all()
    holdings_count = (await db.execute(
        select(func.count()).select_from(PensionHolding).where(PensionHolding.inquiry_id == inquiry.id)
    )).scalar_one()

    base = _serialize_inquiry(inquiry)
    return InquiryDetailOut(
        **base.model_dump(),
        audit=[
            AuditEntryOut(
                event_type=a.event_type,
                from_status=a.from_status,
                to_status=a.to_status,
                actor=a.actor,
                detail=a.detail,
                created_at=a.created_at,
            ) for a in audit_rows
        ],
        holdings_count=holdings_count,
    )


# ─── Enriched per-customer view ────────────────────────────────────────────
@router.get("/customer/{id_number}", response_model=EnrichedPictureOut)
async def enriched_picture(
    id_number: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    picture = await orchestration.get_enriched_picture(db, user_id=user.id, id_number=id_number)
    if picture is None:
        raise HTTPException(status_code=404, detail="No clearinghouse holdings for this customer")
    return picture


# ─── Manual poll (for dev / on-demand refresh) ─────────────────────────────
@router.post("/poll", response_model=PollStatsOut,
             dependencies=[Depends(require_maslaka_enabled), Depends(require_vault_host)])
async def manual_poll(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """User-scoped poll — only matches inbox files whose request_reference
    belongs to one of this user's inquiries. Safe to call repeatedly; the
    scheduler runs the same code system-wide on a timer."""
    stats = await orchestration.poll_and_ingest(db, user_id=user.id)
    return stats


# ─── Test console ──────────────────────────────────────────────────────────
# Replays REAL מסלקה wire files (Swiftness's published sample pack, vendored at
# tests/fixtures/maslaka/swiftness_samples) through the live parser and returns
# the source XML next to the rows we would store.
#
# Deliberately reads fixtures rather than the vault: the vault is empty until
# Swiftness whitelists our TST host, and every parser defect found so far was
# found this way. When live sending arrives this same screen gains a Send panel;
# the inspection half stays useful either way.
_SAMPLE_DIR = (
    Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "maslaka" / "swiftness_samples"
)


def _sample_path(name: str) -> Path:
    """Resolve a sample by name, refusing anything that escapes the directory."""
    candidate = (_SAMPLE_DIR / name).resolve()
    if not str(candidate).startswith(str(_SAMPLE_DIR.resolve())) or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Sample not found")
    return candidate


@router.get("/samples")
async def list_samples(user: User = Depends(get_current_user)):
    """Every vendored sample, with its filename decoded per נספח ו'."""
    if not _SAMPLE_DIR.is_dir():
        return []
    out = []
    for p in sorted(_SAMPLE_DIR.iterdir()):
        if not p.is_file():
            continue
        parsed = parse_filename(p.name)
        out.append({
            "name": p.name,
            "size": p.stat().st_size,
            "filename": parsed.to_dict() if parsed else None,
            "filename_valid": parsed is not None,
        })
    return out


@router.get("/samples/{name}")
async def inspect_sample(name: str, user: User = Depends(get_current_user)):
    """Source XML + the rows the parser produces from it + diagnostics.

    The diagnostics are the point: `rows_missing_id` and `duplicate_rows` are
    exactly the two defects the first real-data run exposed, so they stay visible
    rather than needing a re-discovery.
    """
    path = _sample_path(name)
    raw = path.read_bytes()
    parsed_name = parse_filename(path.name)

    text = raw.decode("utf-8", errors="replace")
    MAX_CHARS = 200_000        # keep a 180KB CONSLT from blowing up the browser
    payload = {
        "name": path.name,
        "size": len(raw),
        "filename": parsed_name.to_dict() if parsed_name else None,
        "filename_valid": parsed_name is not None,
        "xml": text[:MAX_CHARS],
        "xml_truncated": len(text) > MAX_CHARS,
        "rows": [],
        "diagnostics": {},
        "error": None,
    }

    service = parsed_name.service if parsed_name else ""
    if service in ("FEDBKA", "FEDBKB"):
        # Feedback carries no holdings — surface its correlation keys instead,
        # since MISPAR-MISLAKA is what a response is matched on.
        import xml.etree.ElementTree as ET

        def _local(t: str) -> str:
            return t.rsplit("}", 1)[-1] if "}" in t else t

        try:
            root = ET.fromstring(raw)
            wanted = {
                "SUG-MIMSHAK", "MISPAR-GIRSAT-XML", "SHEM-HAKOVETZ", "MISPAR-MISLAKA",
                "SUG-MASHOV", "RAMAT-MASHOV", "STATUS-RESHUMA",
                "KOD-SHGIHA-BERAMAT-RESHUMA", "MAANE-BERAMAT-RESHUMA",
                "KAMUT-RESHUMOT-TKINOT", "KAMUT-RESHUMOT-KOLEL",
            }
            found: dict[str, str] = {}
            for el in root.iter():
                tag = _local(el.tag)
                if tag in wanted and tag not in found:
                    found[tag] = (el.text or "").strip()
            payload["diagnostics"] = {"kind": "feedback", "fields": found}
        except ET.ParseError as e:
            payload["error"] = f"XML parse error: {e}"
        return payload

    try:
        result = parse_mimshak_dat(raw, path.name)
        rows = result.get("records", [])
        seen: set[tuple] = set()
        dupes = 0
        for r in rows:
            key = (r.get("id_number"), r.get("fund_policy_number"))
            if key in seen:
                dupes += 1
            seen.add(key)
        payload["rows"] = rows
        payload["diagnostics"] = {
            "kind": "holdings",
            "format": result.get("format"),
            "company_source": result.get("company_source"),
            "rows": len(rows),
            "rows_missing_id": sum(1 for r in rows if not r.get("id_number")),
            "duplicate_rows": dupes,
            "product_types": sorted({str(r.get("product_type") or "—") for r in rows}),
            "total_accumulation": round(sum(float(r.get("accumulation") or 0) for r in rows), 2),
            "distinct_customers": len({r.get("id_number") for r in rows if r.get("id_number")}),
        }
    except Exception as e:                                   # noqa: BLE001
        payload["error"] = f"{type(e).__name__}: {e}"
    return payload


# ─── Internal: serializer ──────────────────────────────────────────────────
def _serialize_inquiry(inq: PensionInquiry) -> InquiryOut:
    return InquiryOut(
        id=str(inq.id),
        user_id=str(inq.user_id),
        customer_id_number=inq.customer_id_number,
        customer_name=inq.customer_name,
        status=inq.status,
        interface_code=inq.interface_code,
        request_reference=inq.request_reference,
        vault_outbound_filename=inq.vault_outbound_filename,
        submitted_at=inq.submitted_at,
        acknowledged_at=inq.acknowledged_at,
        completed_at=inq.completed_at,
        expires_at=inq.expires_at,
        error_code=inq.error_code,
        error_detail=inq.error_detail,
        providers_expected=inq.providers_expected,
        providers_received=inq.providers_received,
        created_at=inq.created_at,
    )
