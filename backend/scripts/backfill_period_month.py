"""Backfill `file_uploads.period_month` for rows that pre-date the column.

Runs `detect_period_month()` against each upload's records (data-dates-first
priority) + filename, and writes the result. Idempotent — re-running won't
clobber existing values unless --force is passed.

Usage (locally):
    cd backend
    python -m scripts.backfill_period_month [--force] [--dry-run]

Or in Railway shell:
    railway run --service nifraim python -m scripts.backfill_period_month

The script connects via DATABASE_URL_SYNC (preferred) or DATABASE_URL.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
from collections import Counter

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.upload import FileUpload
from app.models.record import ClientRecord
from app.services.parser_service import detect_period_month


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("backfill_period_month")


async def backfill(force: bool, dry_run: bool) -> None:
    """Walk every FileUpload row, detect period_month, and write.
    With --force, overrides existing non-NULL values (use when detection
    rules change). Without --force, only NULL rows are touched."""
    results: Counter[str] = Counter()
    updates: list[tuple[str, str | None]] = []

    async with async_session() as db:
        q = await db.execute(select(FileUpload).order_by(FileUpload.uploaded_at.desc()))
        uploads = list(q.scalars().all())
        logger.info("Scanning %d file_uploads rows", len(uploads))

        for u in uploads:
            if u.period_month is not None and not force:
                results["already_set"] += 1
                continue

            # Pull a minimal record set for date detection — only the date
            # columns we care about, not the full row payload. Column names
            # must match detect_period_month's expectations.
            recs_q = await db.execute(
                select(
                    ClientRecord.sign_date,
                    ClientRecord.transfer_date,
                    ClientRecord.rights_assignment_date,
                    ClientRecord.processing_date,
                ).where(ClientRecord.upload_id == u.id)
            )
            records = [
                {
                    "sign_date": r[0],
                    "transfer_date": r[1],
                    "rights_assignment_date": r[2],
                    "processing_date": r[3],
                }
                for r in recs_q.all()
            ]

            detected = detect_period_month(u.filename, records, uploaded_at=u.uploaded_at)

            if detected is None:
                results["no_period_detected"] += 1
                logger.warning(
                    "no period detected: upload_id=%s filename=%s records=%d",
                    u.id, u.filename, len(records),
                )
                continue

            if u.period_month == detected:
                results["unchanged"] += 1
                continue

            updates.append((str(u.id), detected.isoformat()))
            if dry_run:
                results["would_update"] += 1
                continue

            await db.execute(
                update(FileUpload)
                .where(FileUpload.id == u.id)
                .values(period_month=detected)
            )
            results["updated"] += 1

        if not dry_run:
            await db.commit()

    logger.info("Done. Summary: %s", dict(results))
    if updates and dry_run:
        logger.info("First 10 would-be updates: %s", updates[:10])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force",
        action="store_true",
        help="Override existing non-NULL period_month values (use after detection-rule changes).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't commit; just log what would change.",
    )
    args = parser.parse_args()
    asyncio.run(backfill(force=args.force, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
