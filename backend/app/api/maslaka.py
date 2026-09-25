"""Pension clearinghouse (המסלקה הפנסיונית) HTTP surface.

All routes are auth-gated via `get_paid_user` (same dep used by uploads).
Strict `user.id` scoping — a customer-id passed in a URL only resolves
against records owned by the requesting user; missing → 404.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
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
    ProductionReportRequest,
)
from pathlib import Path

from app.config import settings
from app.services.maslaka import orchestration
from app.services.maslaka.events import ACTION_CODES, build_events_request, maslaka_now
from app.services.maslaka.filenames import build_filename, parse_filename
from app.services.maslaka.xsd import schema_for, validate as xsd_validate
from app.services.mimshak import parse_mimshak_dat

logger = logging.getLogger(__name__)

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
                "המסלקה הפנסיונית כבויה בסביבה הזו (MASLAKA_ENABLED=false). "
                "הכספת עצמה כן פתוחה — קבצים נשלחים אליה בהצלחה מה-Gateway. "
                "מה שחסר הוא הפעלה שלנו כבעל רישיון שולח אצל המסלקה."
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


async def require_association_approved(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Third gate: this AGENT is linked to our ח.פ at the מסלקה.

    `MASLAKA_ENABLED` says the feature is live and `MASLAKA_VAULT_HOST` says who
    owns the folders — neither says anything about the caller. Without this an
    agent whose שיוך was never approved could still create an inquiry, and the
    Gateway worker would dutifully transport it: unauthorised traffic to a
    regulator, under our ח.פ, with the app reporting success.

    Client-side gating cannot cover this. The tab hides the form, but the route
    is what has to refuse.
    """
    from app.services.maslaka import association

    link = await association.get_or_create_link(
        db, user_id=user.id, agent_name=user.full_name)
    if link.status != "approved":
        raise HTTPException(
            status_code=403,
            detail=(
                "השיוך לבית התוכנה במסלקה טרם אושר — לא ניתן לשלוח בקשות מידע. "
                "השלימו את טופס השיוך בלשונית המסלקה."
            ),
            headers={"X-Maslaka-Association-Status": link.status},
        )


# ─── Inquiry creation ──────────────────────────────────────────────────────
@router.post("/inquiry", response_model=InquiryOut,
             dependencies=[Depends(require_maslaka_enabled),
                           Depends(require_association_approved)])
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


@router.get("/production-report/bodies")
async def production_report_bodies(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Every body a production report can be asked from, with how many of the
    caller's own customers sit there (from their records) and whether a monthly
    subscription (2100) is already open — so the UI can pre-select the agent's
    actual insurers and never offer a duplicate subscription."""
    from app.models.record import ClientRecord
    from app.services.maslaka.code_tables import PROVIDER_CODE_TO_COMPANY, provider_code_for_company

    counts: dict[str, int] = {}
    rows = (await db.execute(
        select(ClientRecord.receiving_company,
               func.count(func.distinct(func.ltrim(ClientRecord.id_number, "0"))))
        .where(ClientRecord.user_id == user.id)
        .group_by(ClientRecord.receiving_company)
    )).all()
    for company, n in rows:
        code = provider_code_for_company(company)
        if code:
            counts[code] = counts.get(code, 0) + int(n or 0)

    monthly = set((await db.execute(
        select(PensionInquiry.target_yatzran_id).where(
            PensionInquiry.user_id == user.id,
            PensionInquiry.interface_code == "events_v007:2100",
            PensionInquiry.status.notin_(("failed", "expired")),
        )
    )).scalars().all())

    out = [
        {"id": code, "name": name, "clients": counts.get(code, 0), "monthly": code in monthly}
        for code, name in PROVIDER_CODE_TO_COMPANY.items()
    ]
    out.sort(key=lambda b: (-b["clients"], b["name"]))
    return out


@router.post("/production-report", response_model=list[InquiryOut],
             dependencies=[Depends(require_maslaka_enabled),
                           Depends(require_association_approved)])
async def create_production_report_endpoint(
    payload: ProductionReportRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Queue a one-off production report (2000) of the caller's book — one
    `pending` inquiry per institutional body. Sends nothing; the Gateway
    worker claims them like any other inquiry.

    The subject of a production request is the AGENT (SUG-LAKOACH 3 = מפיץ),
    so the row carries the agent's own linked ת"ז, never a customer's.
    """
    from app.services.maslaka import association
    from app.services.maslaka.code_tables import is_known_provider, label_for_provider

    link = await association.get_or_create_link(
        db, user_id=user.id, agent_name=user.full_name)
    ids: list[str] = []
    for raw in payload.yatzran_ids:
        code = "".join(ch for ch in str(raw) if ch.isdigit())
        if not is_known_provider(code):
            raise HTTPException(status_code=400, detail=f"ח.פ יצרן לא מוכר: {raw}")
        if code not in ids:
            ids.append(code)

    if payload.frequency == "monthly":
        already = set((await db.execute(
            select(PensionInquiry.target_yatzran_id).where(
                PensionInquiry.user_id == user.id,
                PensionInquiry.interface_code == "events_v007:2100",
                PensionInquiry.status.notin_(("failed", "expired")),
            )
        )).scalars().all())
        ids = [c for c in ids if c not in already]
        if not ids:
            raise HTTPException(status_code=409, detail="כבר קיים מנוי חודשי לכל הגופים שנבחרו")

    out = []
    for code in ids:
        inquiry = await orchestration.create_inquiry(
            db,
            user_id=user.id,
            customer_id_number=link.agent_id_number,
            customer_name=label_for_provider(code),
            action_code="2100" if payload.frequency == "monthly" else "2000",
            target_yatzran_id=code,
            information_date=payload.information_date,
        )
        out.append(_serialize_inquiry(inquiry))
    return out


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
    # Validate EVERY inbound file, before any branch returns. This sat below the
    # feedback early-return at first, which meant FEDBKA — the exact file we are
    # waiting on — was the one file that skipped validation. A parser is happy to
    # produce plausible numbers from a malformed file; say whether it validates
    # before anyone trusts the fields.
    _decoded = parse_filename(path.name)
    payload["validation"] = xsd_validate(
        raw,
        schema_file=schema_for(
            service=_decoded.service if _decoded else None,
            product_family=_decoded.product_family if _decoded else None,
            xml=raw,   # unrecognised filename → fall back to the file's SUG-MIMSHAK
        ),
    ).to_dict()

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


@router.get("/actions")
async def list_actions(user: User = Depends(get_current_user)):
    """The ממשק אירועים action codes we support (נספח י\"א)."""
    return [
        {
            "code": a.code,
            "label": a.label,
            "note": a.note,
            "needs_customer": a.needs_customer,
        }
        for a in ACTION_CODES.values()
    ]


@router.post("/preview")
async def preview_request(
    payload: dict,
    user: User = Depends(get_current_user),
):
    """Build the EXACT request we would send — XML plus filename — and return it
    WITHOUT transporting anything.

    This is why the console works before Swiftness issues our credentials: the
    envelope, the action code and the נספח ו' filename are all fully determined
    without a vault. `allow_placeholder_identity` fills the agent number with a
    visible `<ת.ז. הסוכן>` marker so it is obvious what is still missing rather
    than looking configured.
    """
    action_code = str(payload.get("action_code") or "").strip()
    if action_code not in ACTION_CODES:
        raise HTTPException(status_code=400, detail=f"קוד פעולה לא מוכר: {action_code}")

    env = str(payload.get("environment") or "TST").upper()
    if env not in ("TST", "PRD"):
        raise HTTPException(status_code=400, detail="environment must be TST or PRD")

    customer_id = str(payload.get("customer_id_number") or "").strip()
    action = ACTION_CODES[action_code]
    if action.needs_customer and not customer_id:
        raise HTTPException(status_code=400, detail="פעולה זו דורשת מספר זהות של לקוח")

    try:
        req = build_events_request(
            action_code=action_code,
            customer_id_number=customer_id or None,
            customer_first_name=str(payload.get("first_name") or ""),
            customer_last_name=str(payload.get("last_name") or ""),
            sequence=int(payload.get("sequence") or 1),
            # 1 = TEST, 2 = PRODUCTION per the official XSD. This endpoint kept
            # its own inline copy of the mapping — and it was the inverted one.
            # Two copies of a rule is how the rule goes wrong; use the shared
            # helper's convention, keyed off the environment the caller picked.
            environment_code="2" if env == "PRD" else "1",
            allow_placeholder_identity=True,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    agent_id = settings.MASLAKA_AGENT_ID or "0"
    filename = build_filename(
        direction="001",                       # בעל רישיון → מסלקה
        sender_id=agent_id,
        service="EVENTS",
        version="007",
        sequence=int(payload.get("sequence") or 1),
        product_family="000",                  # only אחזקות/טרום-ייעוץ files name a family
        file_type="DAT" if env == "PRD" else "TST",
        when=maslaka_now(),                    # Israel clock, never the host's
    )

    # State what is still missing rather than letting a rendered request imply
    # it is ready to send.
    blockers = []
    if not settings.MASLAKA_AGENT_ID:
        blockers.append("חסר MASLAKA_AGENT_ID — מזהה השולח (ח.פ)")
    if not settings.MASLAKA_ENABLED:
        blockers.append("MASLAKA_ENABLED=false — הכספת עדיין סגורה")
    if not settings.MASLAKA_VAULT_HOST:
        blockers.append("השרת הזה אינו שרת הכספת — שליחה מתבצעת רק מה-Gateway")
    if action.needs_customer:
        blockers.append("נדרש ייפוי כוח בתוקף (1700) לפני בקשת מידע על לקוח")

    # Validate what we just built against Swiftness's OWN schema. This is the
    # check that found four fatal defects on 2026-09-10 after four live sends
    # went unanswered — a rendered request that has not been validated tells you
    # nothing about whether the מסלקה will accept it.
    validation = xsd_validate(req.xml, schema_file=schema_for(service="EVENTS"))
    if validation.ok is False:
        blockers.append(f"הקובץ אינו עומד בסכימה הרשמית ({len(validation.errors)} שגיאות)")

    return {
        "validation": validation.to_dict(),
        "action": {"code": action.code, "label": action.label, "note": action.note},
        "environment": env,
        "filename": filename,
        "filename_decoded": (parse_filename(filename).to_dict() if parse_filename(filename) else None),
        "xml": req.xml.decode("utf-8"),
        "record_reference": req.record_reference,
        "blockers": blockers,
        "sent": False,
    }


# ─── Internal: serializer ──────────────────────────────────────────────────
def _serialize_inquiry(inq: PensionInquiry) -> InquiryOut:
    expected_by, expected_basis = orchestration.expected_answer_by(inq)
    return InquiryOut(
        expected_by=expected_by,
        expected_basis=expected_basis,
        information_date=getattr(inq, "information_date", None),
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


@router.get("/sends")
async def list_sends(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Every request this licence has put on the wire, newest first.

    Exists because on 2026-09-10 six live files were sent by hand and the only
    record of them was a terminal scrollback. If a send is not visible here it
    may as well not have happened — you cannot reason about "no response yet"
    without knowing exactly what went out and when.
    """
    rows = (await db.execute(
        select(PensionInquiry)
        .where(PensionInquiry.user_id == user.id)
        .order_by(PensionInquiry.created_at.desc())
        .limit(100)
    )).scalars().all()

    out = []
    for r in rows:
        decoded = parse_filename(r.vault_outbound_filename or "") if r.vault_outbound_filename else None
        out.append({
            "id": str(r.id),
            "customer_id_number": r.customer_id_number,
            "customer_name": r.customer_name,
            "status": r.status,
            "action_code": (r.interface_code or "").rpartition(":")[2] or None,
            "filename": r.vault_outbound_filename,
            "filename_decoded": decoded.to_dict() if decoded else None,
            "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
            "acknowledged_at": r.acknowledged_at.isoformat() if r.acknowledged_at else None,
            "providers_expected": r.providers_expected,
            "providers_received": r.providers_received,
            "error_code": r.error_code,
            "error_detail": r.error_detail,
        })
    return out


@router.get("/vault")
async def vault_state(user: User = Depends(get_current_user)):
    """What is actually sitting in the vault right now, and whether this host
    can even see it.

    `is_vault_host` is the honest part: on the dev box the answer is no, and the
    inbox will read 0 no matter what the מסלקה has sent. Only the Gateway VM
    (MASLAKA_VAULT_HOST=true) watches the real Transporter folders.
    """
    from app.services.maslaka.transport import get_transport

    state = {
        "is_vault_host": bool(settings.MASLAKA_VAULT_HOST),
        "environment": "TST" if settings.MASLAKA_TEST_ENVIRONMENT else "PRD",
        "transport": settings.MASLAKA_TRANSPORT,
        "inbox": [],
        "error": None,
    }
    if not settings.MASLAKA_VAULT_HOST:
        state["note"] = (
            "השרת הזה אינו שרת הכספת — התיקיות האמיתיות נמצאות רק ב-Gateway "
            "(51.58.32.28). מה שמוצג כאן הוא הכספת המקומית בלבד."
        )
    try:
        for f in await get_transport().list_inbox():
            decoded = parse_filename(f.name)
            state["inbox"].append({
                "name": f.name,
                "size": f.bytes_size,
                "decoded": decoded.to_dict() if decoded else None,
                "recognized": decoded is not None,
            })
    except Exception as e:                                   # noqa: BLE001
        state["error"] = f"{type(e).__name__}: {e}"
    return state


# ─── Agent association (שיוך לבית תוכנה) ────────────────────────────────────
# Nifraim is the מסלקה בית תוכנה: one vault, one account, every agent. Before an
# agent may transact, the מסלקה must link them to our ח.פ — a paper form they
# sign. These routes own that process. They are deliberately NOT behind
# `require_maslaka_enabled`: an agent must be able to start the association even
# in an environment where the clearinghouse feature itself is off, otherwise
# onboarding deadlocks on the thing onboarding is meant to unlock.

@router.get("/association")
async def association_status(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Where this agent stands. Drives the מסלקה tab's gate — the single source
    of truth, deliberately server-side (the onboarding flags went wrong exactly
    because state lived in browser-local storage)."""
    from app.services.maslaka import association

    link = await association.get_or_create_link(
        db, user_id=user.id, agent_name=user.full_name
    )
    return {
        "status": link.status,
        "agent_id_number": link.agent_id_number,
        "agent_name": link.agent_name or user.full_name,
        "agent_licence_number": link.agent_licence_number,
        "form_downloaded_at": link.form_downloaded_at.isoformat() if link.form_downloaded_at else None,
        "submitted_at": link.submitted_at.isoformat() if link.submitted_at else None,
        "approved_at": link.approved_at.isoformat() if link.approved_at else None,
        "rejected_reason": link.rejected_reason,
        "signed_pdf_filename": link.signed_pdf_filename,
        # Survives a reload: the wizard shows this after /submit, and without
        # it a failed delivery disappears the moment the page refreshes.
        "delivery_note": link.delivery_note,
        # The approval watcher's audit trail. It records the helpdesk reply it
        # matched WHETHER OR NOT it could classify it, so the wizard can show
        # "התקבלה תשובה מהמסלקה" on an unclassified reply instead of leaving the
        # agent staring at `submitted` while an answer sits in their inbox.
        # `decided_via` says who flipped the status — 'mailbox' or 'admin'.
        "reply_received_at": (
            link.reply_received_at.isoformat() if link.reply_received_at else None),
        "reply_subject": link.reply_subject,
        "reply_snippet": link.reply_snippet,
        "decided_via": link.decided_via,
        # The REAL destination, not the module constant. Reporting the constant
        # told a dev box it was mailing the regulator when the override sent it
        # elsewhere — and would say the same if someone pointed prod away.
        "helpdesk_email": association.helpdesk_email(),
        "beit_tochna": {
            "name": association.BEIT_TOCHNA_NAME,
            "id": association.BEIT_TOCHNA_ID,
        },
        "template_ready": association.template_is_servable(),
    }


@router.post("/association/identity")
async def association_identity(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Record who the agent is. `agent_id_number` is what will ride on the wire
    in `MISPAR-MEZAHE-PONE`; the SENDER stays the global Nifraim ח.פ."""
    from app.services.maslaka import association

    link = await association.get_or_create_link(db, user_id=user.id, agent_name=user.full_name)
    try:
        await association.set_agent_identity(
            db, link,
            agent_id_number=str(payload.get("agent_id_number") or ""),
            agent_name=str(payload.get("agent_name") or user.full_name or ""),
            agent_licence_number=str(payload.get("agent_licence_number") or "") or None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "agent_id_number": link.agent_id_number}


@router.get("/association/form")
async def association_form(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """The מסלקה form, pre-filled with this agent's details.

    Pre-filled rather than blank on purpose: the ח.פ `558638623` and the
    לבית תוכנה tick are the two things an agent can get wrong, and a wrong ח.פ
    associates them to somebody else.
    """
    from fastapi.responses import Response

    from app.services.maslaka import association

    link = await association.get_or_create_link(db, user_id=user.id, agent_name=user.full_name)
    if not link.agent_id_number:
        raise HTTPException(status_code=400, detail="יש להזין מספר זהות לפני הורדת הטופס")
    try:
        pdf = association.build_prefilled_form(
            agent_name=link.agent_name or user.full_name or "",
            agent_id_number=link.agent_id_number,
        )
    except association.FormTemplateMissing as e:
        # 503, not 500: nothing is broken in the code — a file is missing.
        raise HTTPException(
            status_code=503,
            detail="טופס השיוך עדיין לא הוטמע במערכת. פנו לתמיכה.",
        ) from e
    await association.mark_form_downloaded(db, link)
    return Response(
        pdf, media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="maslaka-shiyuch.pdf"'},
    )


@router.post("/association/submit")
async def association_submit(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    file: UploadFile = File(...),
):
    """Take the signed scan, store it encrypted, email it to the מסלקה helpdesk.

    Delivery failure does NOT lose the upload: the form is stored and the row
    flipped to `submitted` first, and a send error comes back as a note the
    agent can act on. Losing a signed document because SMTP hiccuped would be
    the worst outcome here.
    """
    from app.services.maslaka import association

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="הקובץ ריק")
    if len(raw) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="הקובץ גדול מדי (מקסימום 15MB)")
    if not raw.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="יש להעלות קובץ PDF חתום")

    link = await association.get_or_create_link(db, user_id=user.id, agent_name=user.full_name)
    if not link.agent_id_number:
        raise HTTPException(status_code=400, detail="יש להזין מספר זהות לפני שליחת הטופס")

    await association.record_submission(
        db, link, pdf_bytes=raw, filename=file.filename or "shiyuch.pdf",
    )
    try:
        to = await association.deliver_to_helpdesk(
            link=link, pdf_bytes=raw, agent_email=user.email,
        )
        note = f"נשלח ל-{to}"
    except Exception as e:                                       # noqa: BLE001
        logger.error("maslaka.association: delivery failed for %s: %s", user.id, e)
        note = f"הטופס נשמר אך המשלוח נכשל: {e}"
    link.delivery_note = note[:500]
    await db.commit()
    return {"status": link.status, "delivery_note": note}


@router.post("/association/approve")
async def association_approve(
    payload: dict | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mark an association approved (or rejected). **ADMIN ONLY.**

    Manual today: the approval arrives as an email from the מסלקה, and reading
    the agent's mailbox to spot it is a separate project (the existing mail
    integration is read-only and covers different providers). Keep this route
    even once that lands — an automated watcher always needs an override.

    The admin check is the point of the whole gate. Without it an agent could
    approve their own association and unlock the מסלקה tab while the מסלקה had
    never linked them to our ח.פ — every request they then made would be
    unauthorised at the regulator, and the app would have said it was fine.
    `user_id` therefore names WHOSE association to act on, and defaults to the
    caller's own so an admin approving themselves needs no argument.
    """
    from app.services.maslaka import association

    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="רק מנהל מערכת יכול לאשר שיוך — האישור מגיע מהמסלקה",
        )
    target_id = user.id
    raw_target = (payload or {}).get("user_id")
    if raw_target:
        try:
            target_id = uuid.UUID(str(raw_target))
        except ValueError as e:
            raise HTTPException(status_code=400, detail="user_id לא תקין") from e
    target = await db.get(User, target_id)
    if target is None:
        raise HTTPException(status_code=404, detail="משתמש לא נמצא")

    link = await association.get_or_create_link(
        db, user_id=target.id, agent_name=target.full_name)
    # Attribute the decision. Without this an admin flip is indistinguishable
    # from the watcher's, and "why is this agent approved?" has no answer.
    link.decided_via = "admin"
    reason = (payload or {}).get("rejected_reason")
    if reason:
        await association.mark_rejected(db, link, str(reason))
    else:
        await association.mark_approved(db, link)
    return {"status": link.status, "approved_at":
            link.approved_at.isoformat() if link.approved_at else None}
