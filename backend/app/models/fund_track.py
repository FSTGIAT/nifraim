from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, Integer, Numeric, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FundTrack(Base):
    """Latest published returns for an Israeli pension/savings fund track.

    One row per track (10 total). Scraper overwrites returns on each run —
    `scraped_at` is the freshness signal. No history table; if AI insights
    later need trends, add a sibling `fund_track_history` keyed by
    (track_id, period_label).
    """

    __tablename__ = "fund_tracks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    label_he: Mapped[str] = mapped_column(String(80), nullable=False)
    # kupot_gemel | keren_hishtalmut | polisot_hisachon | gemel_lehashkaa
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    # under50 | 50to60 | over60 | stocks | klali
    maslul: Mapped[str] = mapped_column(String(32), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    month_return: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    ytd_return: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    y1_return: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    y3_return: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    y5_return: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)

    period_label: Mapped[str | None] = mapped_column(String(16), nullable=True)
    scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
