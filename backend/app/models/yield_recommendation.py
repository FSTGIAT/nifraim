"""Persisted yield-track recommendations for the workspace insights hub.

Each row pairs one of the agent's production products with the best-performing
mygemel.net track in the same category, so the UI, the Excel export, and the
AI knowledge endpoint can all read from the same source of truth instead of
recomputing on every request.

Refreshed via POST /api/yield-recommendations/generate — that endpoint deletes
the user's existing rows and re-inserts. Lifetime of a row is "until the user
asks for fresh recommendations" — there is no per-day history table here.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class YieldRecommendation(Base):
    __tablename__ = "yield_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    production_upload_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("file_uploads.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ─── Client / product ───────────────────────────────────────────────
    id_number: Mapped[str | None] = mapped_column(String(40))
    client_name: Mapped[str | None] = mapped_column(String(200))
    fund_policy_number: Mapped[str | None] = mapped_column(String(50))
    product_type: Mapped[str | None] = mapped_column(String(100))

    # ─── Current state (where the money is now) ────────────────────────
    current_company: Mapped[str | None] = mapped_column(String(100))
    current_track: Mapped[str | None] = mapped_column(String(120))
    current_yield_1y: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    current_yield_3y: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    current_yield_5y: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))

    # ─── Recommendation (the best alternative track in the same category)
    recommended_track_id: Mapped[str] = mapped_column(String(64), nullable=False)
    recommended_track_name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Specific top fund within the recommended track (e.g. "כלל תמר מניות"
    # under גמל-מניות). Adds variety vs. "everyone → חיסכון מניות".
    recommended_fund_name: Mapped[str | None] = mapped_column(String(160))
    recommended_yield_1y: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    recommended_yield_3y: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    recommended_yield_5y: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    # 'stocks' | 'general' — risk class of the recommendation. Used by the
    # UI to filter/group and tell the agent whether this is a same-risk
    # move or an aggressive upgrade.
    risk_class: Mapped[str] = mapped_column(String(16), nullable=False, server_default="general")
    # 'same' (matches current risk) | 'aggressive' (crosses into stocks)
    # Lets the modal label moves clearly so agents don't accidentally push
    # a conservative client into all-equity.
    move_type: Mapped[str] = mapped_column(String(16), nullable=False, server_default="same")

    # ─── Scoring inputs / output ───────────────────────────────────────
    accumulation: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, server_default="0"
    )
    # potential_annual_gain = accumulation × (rec_3y_avg − current_3y_avg) / 100
    potential_annual_gain: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, server_default="0"
    )

    # ─── Provenance ────────────────────────────────────────────────────
    reasoning: Mapped[str | None] = mapped_column(String(500))
    confidence: Mapped[str] = mapped_column(String(10), nullable=False, server_default="medium")
    generated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
