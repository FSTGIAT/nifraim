"""Grounding for the drafts — facts come from the agent's own Nifraim data,
never from the model. Mirrors the in-tab assistant's rules (ai_assistant memory):
no commission computed as rate × premium, nothing claimed for a company with no
נפרעים file."""
from __future__ import annotations

import re
import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.record import ClientRecord
from app.models.upload import FileUpload

_ID_RE = re.compile(r"(?<!\d)\d{7,9}(?!\d)")
MAX_RECORDS = 20


def ids_in(text: str) -> set[str]:
    """Israeli ID-like numbers in free text, leading zeros stripped (the way
    production stores them)."""
    return {m.lstrip("0") or "0" for m in _ID_RE.findall(text or "")}


async def customer_products(
    db: AsyncSession, user_id: uuid.UUID, *, id_numbers: set[str], email: str | None,
) -> list[dict]:
    conds = []
    if id_numbers:
        conds.append(ClientRecord.id_number.in_(sorted(id_numbers)))
    if email:
        conds.append(ClientRecord.client_email.ilike(email))
    if not conds:
        return []
    rows = (await db.execute(
        select(ClientRecord)
        .join(FileUpload, FileUpload.id == ClientRecord.upload_id)
        .where(ClientRecord.user_id == user_id, FileUpload.is_production.is_(True), or_(*conds))
        .limit(MAX_RECORDS)
    )).scalars().all()
    out = []
    for r in rows:
        item = {
            "לקוח": " ".join(x for x in (r.first_name, r.last_name) if x) or None,
            "ת.ז": r.id_number,
            "חברה": r.receiving_company,
            "מוצר": r.product or r.product_type,
            "מספר פוליסה": r.fund_policy_number,
            "סטטוס מוצר": r.product_status,
            "תאריך הצטרפות": r.sign_date.isoformat() if r.sign_date else None,
        }
        if r.total_premium:
            item["פרמיה"] = float(r.total_premium)
        if r.accumulation:
            item["צבירה"] = float(r.accumulation)
        out.append({k: v for k, v in item.items() if v not in (None, "")})
    return out


async def commission_boundaries(db: AsyncSession, user_id: uuid.UUID) -> str:
    from app.services.ai_service import _get_commission_boundaries
    try:
        return await _get_commission_boundaries(db, user_id)
    except Exception:  # noqa: BLE001 — grounding is best-effort, the rules are not
        return ""
