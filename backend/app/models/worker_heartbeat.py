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
    # Set by the "עדכן עובד" UI button (POST /worker/request-update). The worker
    # checks this on each heartbeat; if it's newer than the worker's own start
    # time it self-updates (git pull) + reloads, then clears it. NULL = nothing
    # requested. Lets the user update the worker without touching git/the machine.
    update_requested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # PIN this account's worker to ONE machine. NULL = unpinned (any machine holding
    # the token may run — the original behaviour).
    #
    # Why this exists: a worker's identity is its token, not its hardware. When one
    # agent's installer link is run on a SECOND PC, that PC becomes a full copy of
    # their worker — it heartbeats as them, claims their batches, logs into the
    # insurers with their credentials and writes their clients' files to its own
    # disk. Live: kiko's token was installed on a colleague's laptop; whichever
    # machine happened to be powered on took the batch, and since only kiko's own
    # desktop has the PowerTerm client, Phoenix's terminal worked or failed
    # depending on hardware nobody was tracking.
    #
    # Pin the good machine BY NAME. An unpinned account behaves exactly as before,
    # so this can't lock anyone out; a pinned one refuses every other machine.
    approved_hostname: Mapped[str | None] = mapped_column(String(120), nullable=True)
