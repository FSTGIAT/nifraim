"""Server-side company routing for incoming OTP SMS.

The Android forwarder (and iPhone Shortcuts) post only the SMS BODY — the sender
and the company a template matched on the device are discarded before forwarding.
So the backend re-derives which insurer an OTP belongs to from the body, reusing
the SAME `SmsOtpTemplate` patterns the forwarder uses for its allow/drop decision
(single source of truth — see [[portal_batch_full_automation]]).

This is what lets the "run all" batch route each OTP to the right portal: a code
tagged for company X is never consumed by a run for company Y. A NULL tag (no
company template matched) falls back to the runner's time-based matching, so a
missing template never blocks a run — it just isn't routed.
"""

from __future__ import annotations

import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sms_otp_template import SmsOtpTemplate

logger = logging.getLogger(__name__)


async def match_otp_company(
    db: AsyncSession, body: str, sender: str | None = None
) -> tuple[str | None, str | None]:
    """Return (portal_kind, company_name) for an incoming OTP SMS.

    Mirrors the device-side OtpFilter: match `sender + " " + body` against the
    active templates (case-insensitive).
      - a BLOCK template matches  → not a company OTP → (None, None)
      - a company template (portal_kind set) matches → (portal_kind, company_name)
      - the generic template (portal_kind NULL) matches → (None, company_name)
      - nothing matches → (None, None)

    `portal_kind` is the BASE company token (e.g. "phoenix", "migdal") shared by
    all of that company's portals; the runner derives the same base from the
    running credential to route the code.
    """
    hay = f"{sender or ''} {body or ''}"

    result = await db.execute(
        select(SmsOtpTemplate)
        .where(SmsOtpTemplate.active.is_(True))
        .order_by(SmsOtpTemplate.created_at.asc())
    )
    templates = list(result.scalars().all())

    def _matches(t: SmsOtpTemplate) -> bool:
        try:
            return re.search(t.pattern, hay, re.IGNORECASE | re.DOTALL) is not None
        except re.error as e:
            logger.warning("Bad SmsOtpTemplate pattern %r (%s): %s", t.pattern, t.company_name, e)
            return False

    # 1. Block templates win — a code-bearing personal SMS shouldn't be routed.
    for t in templates:
        if t.is_block and _matches(t):
            return None, None

    # 2. Company templates (portal_kind set) — the routable case.
    for t in templates:
        if not t.is_block and t.portal_kind and _matches(t):
            return t.portal_kind, t.company_name

    # 3. Generic OTP template (portal_kind NULL) — recognised as an OTP but not
    #    attributable to a company; tag the display name only.
    for t in templates:
        if not t.is_block and not t.portal_kind and _matches(t):
            return None, t.company_name

    return None, None
