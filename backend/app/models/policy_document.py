import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

SOURCES = ("harb_portfolio", "harb_policy", "pdf")


class PolicyDocument(Base):
    """A customer's policy as MARKDOWN — the form the AI reads, embeds (doc_chunks) and links
    from the data map (customers/<id>/policies.md).

    harb_portfolio / harb_policy: built deterministically from a הר הביטוח fetch (no LLM),
    replaced on the next fetch for that customer. pdf: a policy copy the agent uploaded,
    converted by Claude (services/policies/pdf_policy.py); kept until the agent deletes it."""
    __tablename__ = "policy_documents"
    __table_args__ = (
        UniqueConstraint("user_id", "sha256", name="uq_policy_documents_user_sha"),
        Index("ix_policy_documents_user_customer", "user_id", "customer_id_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    customer_id_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    company: Mapped[str | None] = mapped_column(String(160), nullable=True)
    policy_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    filename: Mapped[str | None] = mapped_column(String(300), nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    harb_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("harb_requests.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ready")  # processing|ready|failed
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    index_tries: Mapped[int] = mapped_column(default=0, nullable=False)
    is_current: Mapped[bool] = mapped_column(default=True, nullable=False)   # False = a superseded הר הביטוח fetch
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
