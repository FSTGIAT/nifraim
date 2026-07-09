import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# A browser heartbeats every ~20s; 50s tolerates two missed beats without the
# online dot flapping. Deliberately NOT the worker's 90s window.
PRESENCE_WINDOW_S = 50


class DmPresence(Base):
    """Liveness beacon for a PERSON (their browser has the app open).

    Distinct from ``worker_heartbeats``, which tracks a *Windows PC* running the
    Playwright automation and can be alive at 3am while its owner is asleep. The
    two mean different things and must be able to change independently, so this
    copies that table's narrow-side-table shape without sharing it.

    Narrow table rather than a ``users.last_seen`` column: this row is rewritten
    every ~20s per active user, and ``users`` is read by ``get_current_user`` on
    every single request — churning it would cost vacuum pressure and lock
    contention on the identity table for purely ephemeral data.
    """

    __tablename__ = "dm_presence"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    last_seen: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
