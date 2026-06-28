import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WorkerHeartbeat(Base):
    """Liveness beacon for an agent's LOCAL worker (the Windows machine that runs
    the Playwright automation from an Israeli IP).

    The worker writes ``last_seen`` every few seconds straight to the prod DB;
    the Railway API reads it (``GET /portal-automation/worker/status``) so the
    web UI can show a green "מחובר" / red "מנותק" indicator — i.e. whether the
    agent's computer is on and ready to execute a download. One row per user.
    """

    __tablename__ = "worker_heartbeats"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True, index=True
    )
    last_seen: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    hostname: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Free-text label of what the worker is doing now (e.g. "running batch …"),
    # shown in the UI tooltip. NULL = idle.
    current_job: Mapped[str | None] = mapped_column(String(200), nullable=True)
