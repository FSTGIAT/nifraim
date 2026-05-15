"""Scrape Israeli pension/savings fund returns from mygemel.net.

mygemel.net is server-rendered HTML — each comparison page contains multiple
`<h2 class="title">` sections, each followed by a `<table class="comparison-table">`
with rows for individual funds. Each numeric `<td>` has a `data-value` attribute
shaped like "-4.82%". Columns in order: month, 1Y, 3Y, 5Y.

We compute the group average across all funds per section to populate the
`fund_tracks` rows. On failure (network/parse) we log and leave existing
values untouched so the ticker keeps showing the last known data.
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fund_track import FundTrack
from app.models.fund_track_fund import FundTrackFund

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; NifraimBot/1.0; +https://nifraim-production.up.railway.app)"
REQUEST_TIMEOUT_S = 20

# Maps each (page_url, section_title_exact_or_contains) → fund_tracks.id.
# Section titles taken verbatim from the live pages (2026-05). If mygemel
# rewords a heading the matcher fails closed — track stays NULL, log warns.
PAGE_SECTIONS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "https://www.mygemel.net/%D7%A7%D7%95%D7%A4%D7%95%D7%AA-%D7%92%D7%9E%D7%9C",
        [
            ("עד גיל 50",      "gemel-under50"),
            ("מגיל 50 עד 60",  "gemel-50to60"),
            ("מגיל 60",        "gemel-over60"),
            ("קופת גמל - מניות", "gemel-stocks"),
        ],
    ),
    (
        "https://www.mygemel.net/%D7%A7%D7%A8%D7%A0%D7%95%D7%AA-%D7%94%D7%A9%D7%AA%D7%9C%D7%9E%D7%95%D7%AA",
        [
            ("באפיק כללי",         "hish-klali"),
            ("קרן השתלמות - מניות", "hish-stocks"),
        ],
    ),
    (
        "https://www.mygemel.net/%D7%A4%D7%95%D7%9C%D7%99%D7%A1%D7%95%D7%AA-%D7%97%D7%99%D7%A1%D7%9B%D7%95%D7%9F",
        [
            ("פוליסות חיסכון - כללי", "polisa-klali"),
            ("פוליסות חיסכון - מניות", "polisa-stocks"),
        ],
    ),
    (
        "https://www.mygemel.net/%D7%A7%D7%95%D7%A4%D7%AA-%D7%92%D7%9E%D7%9C-%D7%9C%D7%94%D7%A9%D7%A7%D7%A2%D7%94",
        [
            ("קופת גמל להשקעה - כללי", "gle-klali"),
            ("קופת גמל להשקעה - מניות", "gle-stocks"),
        ],
    ),
]

_PCT_RE = re.compile(r"-?\d+(?:\.\d+)?")


MAX_FUNDS_PER_TRACK = 10


@dataclass
class FundRow:
    name: str
    month: float | None = None
    y1: float | None = None
    y3: float | None = None
    y5: float | None = None


@dataclass
class TrackReturns:
    month: float | None = None
    y1: float | None = None
    y3: float | None = None
    y5: float | None = None
    period_label: str | None = None
    funds: list[FundRow] = None  # type: ignore[assignment]


def _parse_pct(text: str | None) -> float | None:
    if not text:
        return None
    m = _PCT_RE.search(text)
    return float(m.group()) if m else None


def _parse_table(table) -> TrackReturns | None:
    """Parse all fund rows from a comparison-table. Returns the group-average
    TrackReturns plus a list of individual FundRow entries (capped per row)."""
    rows = table.select("tbody tr")
    if not rows:
        return None

    sums = [0.0, 0.0, 0.0, 0.0]
    counts = [0, 0, 0, 0]
    funds: list[FundRow] = []

    for tr in rows:
        cells = tr.select("td.text-center")
        if len(cells) < 4:
            continue
        nums: list[float | None] = [None, None, None, None]
        for i in range(4):
            v = _parse_pct(cells[i].get("data-value") or cells[i].get_text())
            nums[i] = v
            if v is not None:
                sums[i] += v
                counts[i] += 1

        # Fund name: first td (scope="row"). Strip down to its visible text.
        first_td = tr.find("td", attrs={"scope": "row"}) or tr.find("td")
        name = first_td.get_text(strip=True) if first_td else ""
        # Some mygemel tables include trailing whitespace + double-spaces in names
        name = re.sub(r"\s+", " ", name)[:120]
        if name:
            funds.append(FundRow(name=name, month=nums[0], y1=nums[1], y3=nums[2], y5=nums[3]))

    if not any(counts):
        return None

    avg = [round(sums[i] / counts[i], 2) if counts[i] else None for i in range(4)]

    # Period label = month header text (e.g. "מרץ").
    period_label = None
    headers = table.select("thead th")
    if len(headers) > 1:
        period_label = headers[1].get_text(strip=True)[:16]

    return TrackReturns(
        month=avg[0], y1=avg[1], y3=avg[2], y5=avg[3],
        period_label=period_label, funds=funds,
    )


def _find_table_after(soup: BeautifulSoup, needle: str):
    """Return the first `<table class~='comparison-table'>` whose preceding
    `<h2 class='title'>` text contains `needle`."""
    for h2 in soup.select("h2.title"):
        if needle in h2.get_text():
            t = h2.find_next("table", class_="comparison-table")
            if t is not None:
                return t
    return None


async def _scrape_page(client: httpx.AsyncClient, url: str, sections: Iterable[tuple[str, str]]) -> dict[str, TrackReturns]:
    out: dict[str, TrackReturns] = {}
    try:
        resp = await client.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT_S, follow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        logger.warning("fund_scraper: GET %s failed: %s", url, e)
        return out

    soup = BeautifulSoup(resp.text, "html.parser")
    for needle, track_id in sections:
        table = _find_table_after(soup, needle)
        if table is None:
            logger.warning("fund_scraper: no table for '%s' in %s", needle, url)
            continue
        parsed = _parse_table(table)
        if parsed is None:
            logger.warning("fund_scraper: empty/unparsable table for '%s' in %s", needle, url)
            continue
        out[track_id] = parsed
    return out


async def scrape_fund_returns() -> dict[str, TrackReturns]:
    """Fetch all four pages concurrently, parse each. Returns dict keyed by track_id."""
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            *(_scrape_page(client, url, sections) for url, sections in PAGE_SECTIONS),
            return_exceptions=True,
        )
    merged: dict[str, TrackReturns] = {}
    for r in results:
        if isinstance(r, dict):
            merged.update(r)
        else:
            logger.warning("fund_scraper: page task failed: %s", r)
    return merged


async def update_fund_tracks(db: AsyncSession) -> int:
    """Scrape + overwrite returns + commit. Returns count of updated tracks.

    Per-fund detail rows (FundTrackFund) are refreshed via delete-then-insert
    per track — simpler than diff-by-name, and the table is small (<200 rows).
    """
    parsed = await scrape_fund_returns()
    if not parsed:
        logger.warning("fund_scraper: nothing scraped, leaving DB untouched")
        return 0

    rows = (await db.execute(select(FundTrack))).scalars().all()
    by_id = {r.id: r for r in rows}
    now = datetime.now(timezone.utc)
    updated = 0
    fund_rows_inserted = 0

    for track_id, ret in parsed.items():
        row = by_id.get(track_id)
        if row is None:
            logger.warning("fund_scraper: no fund_tracks row for id=%s (skipping)", track_id)
            continue
        row.month_return = ret.month
        row.y1_return = ret.y1
        row.y3_return = ret.y3
        row.y5_return = ret.y5
        row.period_label = ret.period_label
        row.scraped_at = now
        updated += 1

        # Refresh per-fund detail. Delete first, then insert the top N as
        # ordered by the source page (mygemel sorts by month-% desc by default).
        await db.execute(delete(FundTrackFund).where(FundTrackFund.track_id == track_id))
        for rank, f in enumerate((ret.funds or [])[:MAX_FUNDS_PER_TRACK], start=1):
            db.add(FundTrackFund(
                track_id=track_id,
                fund_name=f.name,
                rank=rank,
                month_return=f.month,
                y1_return=f.y1,
                y3_return=f.y3,
                y5_return=f.y5,
                scraped_at=now,
            ))
            fund_rows_inserted += 1

    await db.commit()
    logger.info(
        "fund_scraper: updated %d/%d tracks, inserted %d fund detail rows",
        updated, len(rows), fund_rows_inserted,
    )
    return updated
