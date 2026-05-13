"""Twilio number provisioning for Nifraim agents.

One Nifraim Twilio account owns the regulatory bundle. We buy +972 mobile
numbers under it, assign them per-agent, and configure each number's inbound
SMS webhook to point at our portal-automation endpoint. When an agent is
released (e.g. subscription canceled), we delete the number from Twilio,
mark the row released, and the +972 returns to inventory.

The provisioning calls are sync (Twilio's Python SDK is sync-only); we run
them via `asyncio.to_thread` from the FastAPI handlers.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client as TwilioClient

from app.config import settings
from app.models.agent_twilio_number import AgentTwilioNumber

logger = logging.getLogger(__name__)


WEBHOOK_PATH = "/api/portal-automation/twilio-webhook"


def _client() -> TwilioClient:
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        raise RuntimeError(
            "Twilio not configured — set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN"
        )
    return TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def _webhook_url() -> str:
    base = settings.TWILIO_PUBLIC_WEBHOOK_BASE.rstrip("/")
    return f"{base}{WEBHOOK_PATH}"


def _buy_one_sync(country: str) -> tuple[str, str]:
    """Search the country's mobile inventory for an SMS-capable number and buy
    the first match. Returns (phone_number, twilio_sid). Sync — call via to_thread."""
    client = _client()
    available = client.available_phone_numbers(country).mobile.list(
        sms_enabled=True, limit=5
    )
    if not available:
        raise RuntimeError(
            f"No SMS-capable mobile numbers available in {country} on Twilio right now"
        )
    chosen = available[0]
    purchased = client.incoming_phone_numbers.create(
        phone_number=chosen.phone_number,
        sms_url=_webhook_url(),
        sms_method="POST",
    )
    return purchased.phone_number, purchased.sid


def _release_sync(twilio_sid: str) -> None:
    """Delete the number from Twilio. Idempotent — 404 is treated as success."""
    client = _client()
    try:
        client.incoming_phone_numbers(twilio_sid).delete()
    except TwilioRestException as e:
        if e.status == 404:
            logger.info("Twilio number %s already released", twilio_sid)
            return
        raise


# ─────────────────────────────────────────────────────────────────────────────
# Async DB-backed API consumed by the FastAPI routes
# ─────────────────────────────────────────────────────────────────────────────

async def get_active_for_user(db: AsyncSession, user_id: uuid.UUID) -> AgentTwilioNumber | None:
    result = await db.execute(
        select(AgentTwilioNumber).where(
            AgentTwilioNumber.user_id == user_id,
            AgentTwilioNumber.released_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def provision_for_user(db: AsyncSession, user_id: uuid.UUID) -> AgentTwilioNumber:
    """Buy a +972 mobile number and bind it to this user.

    Idempotent: if the user already has an active number, returns it.
    """
    import asyncio

    existing = await get_active_for_user(db, user_id)
    if existing:
        return existing

    phone_number, sid = await asyncio.to_thread(
        _buy_one_sync, settings.TWILIO_PROVISION_COUNTRY
    )

    row = AgentTwilioNumber(
        user_id=user_id,
        phone_number=phone_number,
        twilio_sid=sid,
        provisioned_at=datetime.utcnow(),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    logger.info("Provisioned Twilio %s for user %s", phone_number, user_id)
    return row


async def release_for_user(db: AsyncSession, user_id: uuid.UUID) -> bool:
    """Release the user's active number back to Twilio. Returns True if a
    release happened, False if the user had no active number."""
    import asyncio

    row = await get_active_for_user(db, user_id)
    if not row:
        return False

    await asyncio.to_thread(_release_sync, row.twilio_sid)
    row.released_at = datetime.utcnow()
    await db.commit()
    return True
