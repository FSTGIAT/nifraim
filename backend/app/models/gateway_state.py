"""One row: the Maslaka Gateway's release + what it reports it is running.

The Gateway (Azure VM, static IP) runs its own copy of the code. It updates
itself only to a version an admin RELEASED (mode A, 2026-10-09 — a human gate in
front of the regulator-facing machine), and reports back every minute so
Admin → תפעול shows deployed · released · running side by side.
See .claude/plans/gateway-self-update.md and services/maslaka/gateway_release.py.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GatewayState(Base):
    __tablename__ = "gateway_state"

    id: Mapped[str] = mapped_column(String(20), primary_key=True, default="main")

    # The version the Gateway may move to (an admin's click). None = never released.
    released_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    released_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Server-side kill switch: while pinned, the Gateway never updates.
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    # What the Gateway itself reports.
    running_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    state: Mapped[str | None] = mapped_column(String(40), nullable=True)   # ok | updating | needs_pip | rolled_back | update_failed
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_tick_ok_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reported_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
