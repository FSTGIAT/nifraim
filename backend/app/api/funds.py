"""Pension/savings fund ticker API.

`/api/funds/ticker` is consumed by the workspace top ticker (StockTicker.vue).
Data is populated by app.services.fund_scraper on a weekly cron + startup
backfill — this endpoint just serves the cached rows.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.fund_track import FundTrack
from app.models.fund_track_fund import FundTrackFund
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter()


def _num(v) -> float | None:
    return float(v) if v is not None else None


@router.get("/ticker")
async def get_ticker(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Return ordered list of fund tracks with the latest month %.

    Auth: any logged-in user. We gate this so competitors can't trivially
    consume our cached scrape, even though the source itself is public.
    """
    rows = (
        await db.execute(select(FundTrack).order_by(FundTrack.sort_order))
    ).scalars().all()

    updated_at = max((r.scraped_at for r in rows if r.scraped_at), default=None)
    return {
        "updated_at": updated_at.isoformat() if updated_at else None,
        "source": "mygemel.net",
        "tracks": [
            {
                "id": r.id,
                "label": r.label_he,
                "category": r.category,
                "maslul": r.maslul,
                "month": _num(r.month_return),
                "period_label": r.period_label,
            }
            for r in rows
        ],
    }


@router.get("/{track_id}")
async def get_track_detail(
    track_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Return the track plus its ranked funds (month/1Y/3Y/5Y) for the click-to-detail viz."""
    track = (
        await db.execute(select(FundTrack).where(FundTrack.id == track_id))
    ).scalars().first()
    if track is None:
        raise HTTPException(status_code=404, detail="track not found")

    funds = (
        await db.execute(
            select(FundTrackFund)
            .where(FundTrackFund.track_id == track_id)
            .order_by(FundTrackFund.rank)
        )
    ).scalars().all()

    return {
        "id": track.id,
        "label": track.label_he,
        "category": track.category,
        "maslul": track.maslul,
        "period_label": track.period_label,
        "scraped_at": track.scraped_at.isoformat() if track.scraped_at else None,
        "averages": {
            "month": _num(track.month_return),
            "y1": _num(track.y1_return),
            "y3": _num(track.y3_return),
            "y5": _num(track.y5_return),
        },
        "funds": [
            {
                "rank": f.rank,
                "name": f.fund_name,
                "month": _num(f.month_return),
                "y1": _num(f.y1_return),
                "y3": _num(f.y3_return),
                "y5": _num(f.y5_return),
            }
            for f in funds
        ],
    }
