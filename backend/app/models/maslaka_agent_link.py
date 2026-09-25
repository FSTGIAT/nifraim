"""The agent ↔ בית תוכנה association at the מסלקה — one row per user.

Nifraim is a **בית תוכנה** (software house), ח.פ 558638623: ONE clearinghouse
account and ONE vault serving every agent on the platform. Before an agent may
transact through it, the מסלקה must link that agent to our ח.פ, and the link is
created by a paper form the agent signs and sends to `helpdesk@swiftness.co.il`
(`טופס בקשה – שיוך לבית תוכנה או בית סוכן`).

This table is the app's record of where each agent is in that process. `status`
is the SINGLE source of truth for the מסלקה tab's gate — do not mirror it into
localStorage, which is how the onboarding flags went wrong (see
`utils/userFlags.js`).

**Not to be confused with a ייפוי כוח.** Two separate gates:

    שיוך לבית תוכנה   the AGENT signs     once per agent    → may transact at all
    ייפוי כוח (1700)  the CUSTOMER signs  once per customer → may see THAT saver

Approving this row unlocks the tab; it does not entitle the agent to any
customer's data.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# The lifecycle, in order. `rejected` is terminal-until-resubmitted: the agent
# goes back to `form_downloaded` and sends a corrected form.
NOT_STARTED = "not_started"
FORM_DOWNLOADED = "form_downloaded"
SUBMITTED = "submitted"
APPROVED = "approved"
REJECTED = "rejected"

STATUSES = (NOT_STARTED, FORM_DOWNLOADED, SUBMITTED, APPROVED, REJECTED)


class MaslakaAgentLink(Base):
    __tablename__ = "maslaka_agent_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )

    # ── Who the agent is on the wire ────────────────────────────────────────
    # `agent_id_number` is the ת"ז/ח.פ that goes into MISPAR-MEZAHE-PONE, and
    # `agent_name` into SHEM-GOREM-PONE, inside YeshutGoremPoneLemislaka — the
    # block we currently send entirely nil. The SENDER stays the global Nifraim
    # ח.פ; only this varies per request. Never give a user their own sender id.
    agent_id_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    agent_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Needed later by the ייפוי כוח (1700) builder, not by the association.
    agent_licence_number: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # ── Lifecycle ───────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default=NOT_STARTED)
    form_downloaded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Consent to open monthly production subscriptions (2100) automatically on
    # approval, and to add bodies that appear later. Recorded with its time.
    auto_production: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    auto_production_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejected_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ── The signed form ─────────────────────────────────────────────────────
    # Fernet-encrypted with MASLAKA_ENCRYPTION_KEY, same key as the raw wire
    # payloads: it carries a signature and an identity document, so it never
    # sits on disk or in the DB in the clear.
    signed_pdf: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    signed_pdf_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delivery_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Approval watcher audit (services/maslaka/approval_watch.py) ──────────
    # Message-ID of the form we sent — so the watcher never mistakes our own
    # outgoing mail for the helpdesk's answer (in dev, helpdesk == agent inbox).
    sent_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # The helpdesk reply the watcher matched — recorded whether or not it could
    # classify it, so an automated approval is always traceable to one email.
    reply_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reply_received_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reply_subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reply_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Who flipped the status: 'mailbox' (the watcher) or 'admin' (manual route).
    decided_via: Mapped[str | None] = mapped_column(String(16), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    @property
    def is_approved(self) -> bool:
        return self.status == APPROVED
