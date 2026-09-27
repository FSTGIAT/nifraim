import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AgentPortalOffer(Base):
    """An extra service the agent offers customers in their portal (step 3 of
    the setup wizard): a card that opens the agent's OWN purchase link. Saved
    once per agent and reused for every customer; each link picks which ones
    to show (`customer_portal_links.settings.offers`)."""
    __tablename__ = "agent_portal_offers"
    __table_args__ = (UniqueConstraint("user_id", "service_key", name="uq_agent_portal_offer"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    service_key: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)  # https only (validated in the API)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PortalOfferClick(Base):
    """A customer opened an offer card — lets the agent see what interested them."""
    __tablename__ = "portal_offer_clicks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portal_link_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customer_portal_links.id", ondelete="CASCADE"), nullable=False, index=True
    )
    service_key: Mapped[str] = mapped_column(String(32), nullable=False)
    clicked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
