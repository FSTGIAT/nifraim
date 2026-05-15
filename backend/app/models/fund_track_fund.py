from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FundTrackFund(Base):
    """Individual fund row within a maslul (e.g. 'כלל תמר מניות' under גמל-מניות).

    Refreshed on every scrape via delete-then-insert keyed on `track_id`, so
    `rank` reflects current ordering on mygemel.net (which defaults to month-%
    descending). Powers AI questions like "מי הקופה הכי טובה ב..." without
    bloating the lightweight `/api/funds/ticker` payload.
    """

    __tablename__ = "fund_track_funds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("fund_tracks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fund_name: Mapped[str] = mapped_column(String(120), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    month_return: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    y1_return: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    y3_return: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    y5_return: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)

    scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
