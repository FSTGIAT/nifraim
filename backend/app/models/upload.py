import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FileUpload(Base):
    __tablename__ = "file_uploads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    company_source: Mapped[str] = mapped_column(String(100), nullable=True)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    format_type: Mapped[str | None] = mapped_column(String(30))
    is_production: Mapped[bool] = mapped_column(Boolean, default=False)
    file_category: Mapped[str | None] = mapped_column(String(20), default="general")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="uploads")
    records = relationship("ClientRecord", back_populates="upload", cascade="all, delete-orphan")
