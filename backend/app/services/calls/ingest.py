"""One way in for a call recording, whoever sends it.

The browser widget (POST /api/calls) and the agent's phone (POST
/api/portal-automation/phone-forward/{token}/call) both land here: create the
call_recordings row, stream the audio to calls-gateway, mark it queued. The rest of
the pipeline (transcriber → events_consumer → Claude) doesn't know or care where the
audio came from.

Phone calls also carry the number from the call log, which links the call to the
customer directly (`id_number`) instead of guessing from names in the transcript.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import AsyncIterator

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.call_recording import CallRecording
from app.models.user import User
from app.services.calls import contract as C

EXT_BY_MIME = {
    "audio/webm": ".webm", "video/webm": ".webm", "audio/ogg": ".ogg",
    "audio/mp4": ".m4a", "audio/x-m4a": ".m4a", "audio/aac": ".m4a", "audio/m4a": ".m4a",
    "audio/wav": ".wav", "audio/x-wav": ".wav", "audio/mpeg": ".mp3", "audio/mp3": ".mp3",
    # older Xiaomi / some Samsung dialers
    "audio/amr": ".amr", "audio/3gpp": ".3gp", "video/3gpp": ".3gp",
}


def phone_key(raw: str | None) -> str | None:
    """The comparable form of a phone number: the national number without its 0.

    Files and devices spell the same number as 050-1234567, 0501234567, 501234567
    (Excel dropped the 0), +972501234567 or 972-50-123-4567 — all reduce to 501234567;
    a landline 03-1234567 / +972-3-1234567 to 31234567. Fewer than 8 digits is not a
    phone (a short code, a junk cell).
    """
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("972") and len(digits) >= 11:
        digits = digits[3:]
    digits = digits.lstrip("0")
    if not 8 <= len(digits) <= 9:
        return None
    return digits


def phone_display(raw: str | None) -> str | None:
    """Local Israeli spelling for display/storage: 050…, 03…"""
    key = phone_key(raw)
    return "0" + key if key else None


def phone_hash(key: str) -> str:
    """What the device compares against. Not a secret — the space of Israeli phone
    numbers is small enough to brute-force — it only keeps the plain customer list
    out of the phone's storage."""
    return hashlib.sha256(key.encode()).hexdigest()


async def customer_phones(db: AsyncSession, user: User) -> dict[str, list[str]]:
    """phone_key → distinct customer id_numbers, from this month's production book."""
    from app.api.production import _get_production_upload_ids
    from app.models.record import ClientRecord

    ids = await _get_production_upload_ids(db, user.id)
    if not ids:
        return {}
    rows = (await db.execute(
        select(ClientRecord.client_phone, ClientRecord.id_number)
        .where(ClientRecord.user_id == user.id, ClientRecord.upload_id.in_(ids),
               ClientRecord.client_phone.is_not(None), ClientRecord.id_number.is_not(None))
        .group_by(ClientRecord.client_phone, ClientRecord.id_number)
    )).all()
    out: dict[str, list[str]] = {}
    for phone, idn in rows:
        key = phone_key(phone)
        idn = (str(idn).strip().lstrip("0") or "0") if idn else None
        if key and idn and idn not in out.setdefault(key, []):
            out[key].append(idn)
    return out


async def match_phone(db: AsyncSession, user: User, phone: str | None) -> str | None:
    """The customer's id_number when exactly one customer has this phone. A number
    shared by a family stays unmatched here; the transcript names decide later."""
    key = phone_key(phone)
    if not key:
        return None
    ids = (await customer_phones(db, user)).get(key) or []
    return ids[0] if len(ids) == 1 else None


def _gateway() -> str:
    if not (settings.CALLS_ENABLED and settings.CALLS_GATEWAY_URL):
        raise HTTPException(503, "שירות השיחות עדיין לא הופעל")
    return settings.CALLS_GATEWAY_URL.rstrip("/")


async def ingest_call(
    db: AsyncSession,
    user: User,
    chunks: AsyncIterator[bytes],
    mime: str,
    duration_s: float | None = None,
    *,
    source: str = "widget",
    phone_number: str | None = None,
    direction: str | None = None,
    started_at: datetime | None = None,
    id_number: str | None = None,
    source_ref: str | None = None,
) -> CallRecording:
    """Create the row, stream `chunks` to the gateway, return the queued call.
    Raises HTTPException (415 / 413 / 502 / 503) with a Hebrew message."""
    gateway = _gateway()
    mime = (mime or "").split(";")[0].strip().lower()
    ext = EXT_BY_MIME.get(mime)
    if not ext:
        raise HTTPException(415, "פורמט הקלטה לא נתמך")

    call = CallRecording(
        user_id=user.id, status="uploaded", mime_type=mime,
        duration_s=duration_s if duration_s and duration_s > 0 else None,
        source=source, phone_number=phone_number, direction=direction,
        started_at=started_at, id_number=id_number, source_ref=source_ref,
    )
    db.add(call)
    await db.commit()
    await db.refresh(call)

    size = 0

    async def body():
        nonlocal size
        async for chunk in chunks:
            size += len(chunk)
            if size > settings.CALLS_MAX_BYTES:
                raise HTTPException(413, "ההקלטה ארוכה מדי")
            yield chunk

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(300, connect=10)) as http:
            resp = await http.post(f"{gateway}/ingest/{call.id}", params={"ext": ext}, content=body(),
                                   headers={C.SECRET_HEADER: settings.CALLS_SECRET,
                                            "Content-Type": "application/octet-stream"})
            resp.raise_for_status()
    except HTTPException as e:
        call.status, call.error = "failed", str(e.detail)
        await db.commit()
        raise
    except Exception:
        call.status, call.error = "failed", "שרת ההקלטות לא זמין — נסו שוב בעוד רגע"
        await db.commit()
        raise HTTPException(502, call.error)

    call.status, call.audio_bytes = "queued", size
    await db.commit()
    return call


async def already_uploaded(db: AsyncSession, user: User, source_ref: str) -> CallRecording | None:
    """A phone retrying the same recording gets the existing call back, not a second one."""
    return (await db.execute(
        select(CallRecording).where(CallRecording.user_id == user.id, CallRecording.source_ref == source_ref,
                                    CallRecording.status != "failed")
        .order_by(CallRecording.created_at.desc()).limit(1)
    )).scalar_one_or_none()


async def upload_chunks(upload) -> AsyncIterator[bytes]:
    """Read a FastAPI UploadFile in 1MB chunks."""
    while chunk := await upload.read(1024 * 1024):
        yield chunk


