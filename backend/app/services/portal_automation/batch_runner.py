"""Orchestrates a "run all portals" batch.

Runs every active credential SEQUENTIALLY (concurrent OTP would race on the
shared inbox), holding each downloaded production/commission file non-active.
After every site has run, aggregates:

  • all production records → ONE merged production xlsx (active production file)
  • all נפרעים records     → ONE merged commission xlsx (single commission file)

then runs the per-category comparison (גמל + ביטוח) against the merged
production and fires the production snapshot/summary hooks. Partial failures
(one portal down) don't abort the batch.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections import Counter
from datetime import datetime, date, timedelta

from sqlalchemy import select, update

from app.database import async_session
from app.models.portal_credential import PortalCredential
from app.models.portal_run import PortalRun
from app.models.portal_run_batch import PortalRunBatch

logger = logging.getLogger(__name__)

# Reuse the single-run hard timeout per credential.
from app.services.portal_automation.runner import (
    _run_inner,
    _set_status,
    RUN_HARD_TIMEOUT_S,
    OtpTimeout,
)

# Wall-clock cap for a WORKER_ONLY portal (phoenix_terminal). Must exceed the
# orchestrator's own budget — 420s login (incl. up to 300s OTP wait) + 420s export
# + parse — or we kill it from outside before it can say what went wrong.
WORKER_ONLY_TIMEOUT_S = 1500

_HE_MONTHS = {
    1: "ינואר", 2: "פברואר", 3: "מרץ", 4: "אפריל", 5: "מאי", 6: "יוני",
    7: "יולי", 8: "אוגוסט", 9: "ספטמבר", 10: "אוקטובר", 11: "נובמבר", 12: "דצמבר",
}

# Minimum wall-clock gap (seconds) between the PRECEDING run's browser process
# closing and a reCAPTCHA-Enterprise-gated portal (mor/meitav, `use_persistent_
# profile=True`) launching its own. Measured, not guessed: reordering mor/meitav
# to the FRONT of the batch (see the `creds.sort` below, fixed 2026-07-14) did
# NOT fix mor — batch 9e708cbc (2026-07-19) still failed with the IDENTICAL
# `400 {"resultCode":"Bad Request"}` with mor running 2nd, right after meitav.
# Queried `portal_runs.started_at`/`finished_at` for BOTH live failures:
#   2026-07-14 189f68cb: migdal_apm finished 15:50:36.278 → mor started 15:50:37.191 (0.91s gap)
#   2026-07-19 9e708cbc: meitav     finished 16:30:00.481 → mor started 16:30:01.506 (1.02s gap)
# Both failures started ~1s after another portal's Chrome/Edge process had JUST
# closed; the one live STANDALONE success (2026-07-14 12:48, batch_id=NULL) had
# no adjacent automated browser at all. That ~1s adjacency — not cumulative
# batch position/volume (already disproven above) — is the one variable a
# batch run has that a standalone run structurally cannot: `_run_batch_inner`'s
# loop launches the next credential's browser within ~1s of the previous one's
# `context.close()`/`browser.close()`, which is exactly the DB-commit overhead
# between iterations, with no deliberate settle time.
# This does not prove the mechanism (candidate: the outgoing browser process is
# still tearing down — CPU/network/GPU-process contention — while the incoming
# one runs its client-side reCAPTCHA Enterprise risk script, so the token it
# submits is short-changed and the server 400s on a malformed field rather than
# scoring a complete one). It only removes the one measured, reproduced-twice
# variable that IS unique to batch mode. See mor.py's request-payload
# instrumentation for the decisive evidence if this alone doesn't fix it.
RECAPTCHA_SETTLE_S = 12

# Hebrew labels for the comparison categories (for error_message wording).
_CATEGORY_LABELS = {"gemel_hishtalmut": "גמל והשתלמות", "insurance": "ביטוח"}


def _month_label(period: date | None) -> str:
    if not period:
        return ""
    return f"{_HE_MONTHS.get(period.month, '')} {period.year % 100:02d}".strip()


def _record_to_dict(r) -> dict:
    return {
        c.key: getattr(r, c.key)
        for c in r.__table__.columns
        if c.key not in ("id", "user_id", "upload_id")
    }


def _jsonable(obj):
    """Coerce a comparison-result tree into JSON-safe primitives. asyncpg's
    JSONB encoder can't serialise Decimal/date/UUID (DB columns are Numeric →
    Decimal), so walk the tree once. Mirrors comparison.py's helper."""
    from decimal import Decimal
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    return obj


async def _tag_source_accounts_from_filename(db, upload_ids: list[uuid.UUID]) -> None:
    """Set lead_source = source-portal account (from the filename) on the records
    of uploads whose filename carries one. Harel agency logins download one file
    PER מספר-חשבון named `… - 113061826 …`; without this the account is lost when
    the per-account files merge into one נפרעים workbook. Only fills a NULL
    lead_source (never clobbers a real value). Best-effort per upload."""
    if not upload_ids:
        return
    import re as _re
    from sqlalchemy import update as sql_update
    from app.models.upload import FileUpload
    from app.models.record import ClientRecord
    rows = (await db.execute(
        select(FileUpload).where(FileUpload.id.in_(upload_ids))
    )).scalars().all()
    for u in rows:
        m = _re.search(r"-\s*(\d{6,})", u.filename or "")
        if not m:
            continue
        await db.execute(
            sql_update(ClientRecord)
            .where(
                ClientRecord.upload_id == u.id,
                ClientRecord.lead_source.is_(None),
            )
            .values(lead_source=m.group(1))
        )
    await db.flush()


async def _delete_uploads(db, upload_ids: list[uuid.UUID]) -> None:
    """Delete held per-company uploads after their data has been folded into a
    merged file. Cascade removes their ClientRecord rows; NULL any
    portal_runs.upload_id first (that FK has no ON DELETE rule)."""
    if not upload_ids:
        return
    from sqlalchemy import update as sql_update, delete as sql_delete
    from app.models.upload import FileUpload
    await db.execute(
        sql_update(PortalRun).where(PortalRun.upload_id.in_(upload_ids)).values(upload_id=None)
    )
    # ORM delete per row so the records cascade fires.
    rows = (await db.execute(select(FileUpload).where(FileUpload.id.in_(upload_ids)))).scalars().all()
    for u in rows:
        await db.delete(u)
    await db.flush()


async def _run_worker_only_portal(db, run, cred):
    """Dispatch a non-Playwright portal (phoenix_terminal) to its native Windows
    orchestrator subprocess. Returns (success, upload_id). Failure-tolerant — a
    crash here marks only this child failed; the rest of the batch continues."""
    import subprocess, sys, os
    from pathlib import Path
    from app.services.portal_automation.companies import WORKER_ONLY_PORTALS
    rel = WORKER_ONLY_PORTALS.get(cred.portal_kind)
    script = Path(__file__).resolve().parents[3] / rel if rel else None
    if not script or not script.exists():
        await _set_status(db, run, status="failed", error="orchestrator not found", finished=True)
        return False, None
    # PYTHONIOENCODING is NOT optional here. We capture the child's output, so its
    # stdout is a PIPE — and on Windows Python then encodes stdout with the locale
    # codepage (cp1255), not UTF-8. The first '→' it printed raised
    # UnicodeEncodeError and killed a run that had already opened the terminal and
    # downloaded the file. A standalone run never hit this because it inherits a
    # console instead of a pipe. (phoenix_terminal_run._run_child guards its own
    # children the same way.)
    env = {
        **os.environ,
        "PHOENIX_MBT_WAIT_S": os.environ.get("PHOENIX_MBT_WAIT_S", "150"),
        "PYTHONIOENCODING": "utf-8",
    }
    loop = asyncio.get_event_loop()
    try:
        # The orchestrator's own budget is 420s login + 420s export + parse — and the
        # login alone can spend 300s waiting for an OTP. A 330s cap here killed it
        # from OUTSIDE, mid-flight, before it could report why (live: "timed out after
        # 330.0 seconds"). Stay above the sum, and keep the child's output: it is the
        # only account of what the green-screen actually did.
        proc = await loop.run_in_executor(None, lambda: subprocess.run(
            [sys.executable, str(script), str(run.id)], timeout=WORKER_ONLY_TIMEOUT_S,
            env=env, capture_output=True, text=True, errors="replace"))
        if proc.returncode != 0:
            tail = ((proc.stdout or "") + (proc.stderr or ""))[-1500:]
            logger.warning("worker-only portal %s exited %s: %s",
                           cred.portal_kind, proc.returncode, tail)
    except Exception as e:
        logger.exception("worker-only portal %s failed", cred.portal_kind)
        await _set_status(db, run, status="failed", error=str(e)[:300], finished=True)
        return False, None
    await db.refresh(run)
    return (run.status == "success", run.upload_id)


async def run_batch(batch_id: uuid.UUID) -> None:
    """Top-level entry point. Owns its own DB session and never raises."""
    async with async_session() as db:
        batch_q = await db.execute(select(PortalRunBatch).where(PortalRunBatch.id == batch_id))
        batch = batch_q.scalar_one_or_none()
        if batch is None:
            logger.error("PortalRunBatch %s not found", batch_id)
            return

        try:
            await _run_batch_inner(db, batch)
        except Exception as e:
            logger.exception("Batch %s failed", batch_id)
            batch.status = "failed"
            batch.error_message = str(e)[:500]
            batch.finished_at = datetime.utcnow()
            await db.commit()


async def _run_batch_inner(db, batch: PortalRunBatch) -> None:
    from app.models.upload import FileUpload
    from app.models.record import ClientRecord

    user_id = batch.user_id

    from app.services.portal_automation.companies import REGISTRY, WORKER_ONLY_PORTALS

    creds_q = await db.execute(
        select(PortalCredential)
        .where(PortalCredential.user_id == user_id, PortalCredential.is_active.is_(True))
        .order_by(PortalCredential.portal_kind)
    )
    all_creds = list(creds_q.scalars().all())

    # Only run credentials whose portal is (a) implemented (registered) and
    # (b) batch-eligible. Skips junk creds (unknown portal_kind, e.g. a leftover
    # "test_production") and dead-end / folded portals (phoenix terminal,
    # phoenix_nifraim_gemel) so the batch doesn't burn an OTP on a guaranteed
    # failure. Single manual runs are unaffected.
    creds: list[PortalCredential] = []
    skipped: list[str] = []
    for c in all_creds:
        if c.portal_kind in WORKER_ONLY_PORTALS:
            # WORKER_ONLY portals (phoenix_terminal) drive a native Windows
            # green-screen via SendInput and are the ONLY source of Phoenix
            # production. They REQUIRE an elevated (admin) worker — on a non-elevated
            # worker they fail "login script exit 1". The agent's worker is elevated,
            # so include them in the batch (manual single-runs work either way).
            creds.append(c)
            continue
        plugin_cls = REGISTRY.get(c.portal_kind)
        if plugin_cls is None or not getattr(plugin_cls, "include_in_batch", True):
            skipped.append(c.portal_kind)
        else:
            creds.append(c)
    if skipped:
        logger.info("Batch %s: skipping non-batch portals: %s", batch.id, skipped)

    # Run reCAPTCHA-Enterprise-gated portals (mor, meitav — `use_persistent_profile`)
    # FIRST, before the batch's OTHER automated logins add session/IP volume that
    # can sink Enterprise's bot score for them. Proven live 2026-07-14 (batch
    # 189f68cb): the same Mor credential that succeeded standalone at 12:48 (490
    # records) failed at 15:50 with a bare `400 {"resultCode":"Bad Request"}` —
    # ONLY after 9 other portal logins had already run from the same worker/IP in
    # the preceding ~14 minutes (altshuler→migdal_apm). No other variable changed
    # (same creds, same warm persistent profile, same machine) — the credential
    # itself is proven fine; batch-induced score pressure is the best-supported
    # explanation. A stable sort keeps every other portal's relative (alphabetical)
    # order — this only moves the 1-2 Enterprise-gated creds to the front.
    # `mor` gets its OWN rank ahead of the other persistent-profile portals, so
    # it runs with NOTHING before it in the worker process. Every Mor run ever
    # recorded, with the gap from the preceding run in the same batch:
    #   2026-07-14 12:48  STANDALONE  prev=none        n/a     SUCCESS
    #   2026-07-14 15:50  BATCH pos 9 prev=migdal_apm  0.9s    failed
    #   2026-07-19 16:30  BATCH pos 2 prev=meitav      1.0s    failed
    #   2026-07-19 20:00  BATCH pos 2 prev=meitav     13.0s    failed   <- settle gap DID apply
    # The 13.0s run proves RECAPTCHA_SETTLE_S does not help: the gap is not the
    # variable. What tracks perfectly is whether ANY portal ran before Mor in
    # this worker process — the one condition never yet tested in a batch,
    # because meitav is also persistent-profile and sorts alphabetically first
    # under the previous binary key.
    #
    # If Mor still fails at position 1 with no predecessor, then batch-vs-
    # standalone is NOT about preceding browsers at all, and the next thing to
    # examine is what the batch path itself holds open (DB transaction, otp_since
    # anchoring) rather than anything browser-related. Do not add a third timing
    # hypothesis — that well is dry.
    # REVERTED to the known-good order (meitav → mor → rest). Running mor first
    # was tested live on 2026-07-20 (batch 439b46ce) and it FAILED on both counts:
    #   • mor still failed with the identical 400 at position 1, nothing before it
    #     — so "a preceding portal poisons it" is disproven, like the reorder and
    #     the 13s settle gap before it.
    #   • meitav, which had succeeded 3/3 while running FIRST, failed at position 2
    #     with `לא נמצאו שדות ת"ז/טלפון בטופס ההתחברות` — and Railway logged
    #     `persistent browser=chrome` for that run, so it was NOT the bundled-
    #     Chromium fallback either.
    # Net: no gain on mor, a regression on meitav. Restore what worked.
    # Do not re-try a positional/timing fix here — four have now been disproven
    # by measurement. The open lead is the CREDENTIAL SHAPE: royg's working mor
    # username is 8-digit ('40336281|40336281', 4 live successes) while kiko's
    # failing one is 9-digit with a leading zero ('040336281|040336281'), and the
    # instrumentation confirms the wire payload differs (licenseId=len8 vs len9).
    creds.sort(key=lambda c: 0 if getattr(REGISTRY.get(c.portal_kind), "use_persistent_profile", False) else 1)

    batch.total = len(creds)
    batch.status = "running"
    await db.commit()

    prod_upload_ids: list[uuid.UUID] = []
    comm_upload_ids: list[uuid.UUID] = []
    prod_periods: list[date] = []

    # OTP-timeout failures get ONE end-of-batch retry (section 1b). Their codes
    # DID arrive (verified in run 5947ff2e) — just minutes late, after the phone's
    # Doze/battery-opt queue flushed in a burst. Retrying after the rest of the
    # batch (phone now warm, fresh login → fresh code) recovers most of them. We
    # retry ONLY OtpTimeout — a genuinely-broken portal (export/login error) is
    # not re-attempted, so we never burn extra OTPs on a guaranteed failure.
    otp_failed: list[PortalCredential] = []

    # Data-loss notes from runs that finished "success" but lost rows on the
    # way (a folded נפרעים leg failed, or a file ingested with an unrecognized
    # format and was excluded from the merge). _run_inner records them on
    # run.error_message; collecting them here downgrades the batch to partial
    # so the loss is visible instead of shipping a quietly-thin merged file.
    partial_notes: list[str] = []

    # See RECAPTCHA_SETTLE_S above — tracks when the last Playwright browser in
    # THIS loop closed, so a reCAPTCHA-Enterprise-gated portal never launches
    # within that gap of the previous one's teardown. Monotonic clock (loop.time())
    # since only elapsed duration matters, not wall time.
    _loop = asyncio.get_event_loop()
    _last_browser_close_mono: float | None = None

    # ── 1. Run every credential sequentially ─────────────────────────────
    for cred in creds:
        # reCAPTCHA-Enterprise settle gap (measured — see RECAPTCHA_SETTLE_S).
        # Only applies to persistent-profile portals (mor, meitav); every other
        # portal keeps running back-to-back exactly as before.
        if _last_browser_close_mono is not None and getattr(
            REGISTRY.get(cred.portal_kind), "use_persistent_profile", False
        ):
            _elapsed = _loop.time() - _last_browser_close_mono
            _wait_s = RECAPTCHA_SETTLE_S - _elapsed
            if _wait_s > 0:
                logger.info(
                    "Batch %s: settling %.1fs before %s (reCAPTCHA-gated; "
                    "previous browser closed %.1fs ago)",
                    batch.id, _wait_s, cred.portal_kind, _elapsed,
                )
                await asyncio.sleep(_wait_s)

        run = PortalRun(
            user_id=user_id,
            credential_id=cred.id,
            status="pending",
            started_at=datetime.utcnow(),
            batch_id=batch.id,
        )
        db.add(run)
        await db.flush()
        batch.current_run_id = run.id
        await db.commit()

        if cred.portal_kind in WORKER_ONLY_PORTALS:
            ok, up = await _run_worker_only_portal(db, run, cred)
            if ok and up:
                prod_upload_ids.append(up)
                batch.succeeded += 1
                cred.last_run_status = "success"; cred.last_error = None
            else:
                batch.failed += 1
                cred.last_run_status = "failed"
            cred.last_run_at = datetime.utcnow()
            await db.commit()
            continue

        try:
            ingested = await asyncio.wait_for(
                _run_inner(db, run, make_active=False, defer_post_ingest=True),
                timeout=RUN_HARD_TIMEOUT_S,
            )
            cred.last_run_status = "success"
            cred.last_error = None
            batch.succeeded += 1
            for upload_id, file_category, _company in (ingested or []):
                if file_category == "production":
                    prod_upload_ids.append(upload_id)
                elif file_category == "commission":
                    comm_upload_ids.append(upload_id)
            if run.error_message:  # success-with-losses (see partial_notes above)
                partial_notes.append(f"{cred.portal_kind}: {run.error_message}")
        except OtpTimeout as e:
            await _set_status(db, run, status="failed", error=str(e), finished=True)
            cred.last_run_status = "failed"
            cred.last_error = str(e)
            batch.failed += 1
            otp_failed.append(cred)
        except asyncio.TimeoutError:
            await _set_status(db, run, status="timeout",
                              error=f"Run exceeded {RUN_HARD_TIMEOUT_S}s", finished=True)
            cred.last_run_status = "timeout"
            cred.last_error = f"Run exceeded {RUN_HARD_TIMEOUT_S}s"
            batch.failed += 1
        except Exception as e:
            logger.exception("Batch child run %s failed", run.id)
            # _run_inner may have left the run un-finalized; mark it failed.
            await _set_status(db, run, status="failed", error=str(e), finished=True)
            cred.last_run_status = "failed"
            cred.last_error = str(e)
            batch.failed += 1
        finally:
            cred.last_run_at = datetime.utcnow()
            await db.commit()
            # This credential's Playwright browser/context is now closed
            # (`_run_inner`'s own `finally` already ran) — start the settle
            # clock for whichever portal runs next.
            _last_browser_close_mono = _loop.time()

    batch.current_run_id = None
    await db.commit()

    # ── 1b. One retry pass for OTP-timeout failures ───────────────────────
    # Runs BEFORE the merge so any recovered file is folded into the unified
    # production/commission workbooks. A new PortalRun row is created per retry
    # (preserves the pass-1 failure in history); on success we flip the batch
    # tally (failed-1, succeeded+1) so totals stay consistent.
    if otp_failed:
        logger.info(
            "Batch %s: retrying %d OTP-timeout portal(s): %s",
            batch.id, len(otp_failed), [c.portal_kind for c in otp_failed],
        )
        for cred in otp_failed:
            # Same reCAPTCHA settle gap as the main pass (RECAPTCHA_SETTLE_S) —
            # a retried persistent-profile portal must not launch right on the
            # heels of the previous retry's browser closing either.
            if _last_browser_close_mono is not None and getattr(
                REGISTRY.get(cred.portal_kind), "use_persistent_profile", False
            ):
                _elapsed = _loop.time() - _last_browser_close_mono
                _wait_s = RECAPTCHA_SETTLE_S - _elapsed
                if _wait_s > 0:
                    await asyncio.sleep(_wait_s)

            run = PortalRun(
                user_id=user_id,
                credential_id=cred.id,
                status="pending",
                started_at=datetime.utcnow(),
                batch_id=batch.id,
            )
            db.add(run)
            await db.flush()
            batch.current_run_id = run.id
            await db.commit()

            try:
                ingested = await asyncio.wait_for(
                    _run_inner(db, run, make_active=False, defer_post_ingest=True),
                    timeout=RUN_HARD_TIMEOUT_S,
                )
                cred.last_run_status = "success"
                cred.last_error = None
                batch.succeeded += 1
                batch.failed -= 1  # undo the pass-1 OtpTimeout increment
                for upload_id, file_category, _company in (ingested or []):
                    if file_category == "production":
                        prod_upload_ids.append(upload_id)
                    elif file_category == "commission":
                        comm_upload_ids.append(upload_id)
                if run.error_message:  # success-with-losses (see partial_notes above)
                    partial_notes.append(f"{cred.portal_kind}: {run.error_message}")
            except OtpTimeout as e:
                # Still no OTP — leave the pass-1 failed tally as-is.
                await _set_status(db, run, status="failed", error=str(e), finished=True)
                cred.last_error = str(e)
            except asyncio.TimeoutError:
                await _set_status(db, run, status="timeout",
                                  error=f"Run exceeded {RUN_HARD_TIMEOUT_S}s", finished=True)
                cred.last_error = f"Run exceeded {RUN_HARD_TIMEOUT_S}s"
            except Exception as e:
                logger.exception("Batch retry run %s failed", run.id)
                await _set_status(db, run, status="failed", error=str(e), finished=True)
                cred.last_error = str(e)
            finally:
                cred.last_run_at = datetime.utcnow()
                await db.commit()
                _last_browser_close_mono = _loop.time()

        batch.current_run_id = None
        await db.commit()

    # Resolve held upload period months (for naming + batch.period_month).
    if prod_upload_ids:
        periods_q = await db.execute(
            select(FileUpload.period_month).where(FileUpload.id.in_(prod_upload_ids))
        )
        prod_periods = [p for (p,) in periods_q.all() if p]
    batch_period = Counter(prod_periods).most_common(1)[0][0] if prod_periods else None
    if batch_period is None:
        # No period detected on any held production upload. Israeli insurers
        # report ~30 days late, so the batch almost always describes the
        # PREVIOUS calendar month. Falling back keeps batch.period_month
        # non-NULL and — critically — keeps the Hebrew month in the merged
        # filenames below, so detect_period_month resolves from the filename
        # instead of drifting to record dates / uploaded_at.
        batch_period = (date.today().replace(day=1) - timedelta(days=1)).replace(day=1)
    batch.period_month = batch_period
    month_label = _month_label(batch_period)
    # Valuation date (נכון ליום) = last day of the period month — matches the
    # reference production file, which stamps every row with the month-end.
    if batch_period.month == 12:
        _next_month = batch_period.replace(year=batch_period.year + 1, month=1, day=1)
    else:
        _next_month = batch_period.replace(month=batch_period.month + 1, day=1)
    batch_as_of = _next_month - timedelta(days=1)

    # ── 2. Merge production → ONE active upload ───────────────────────────
    merged_prod_upload = None
    if prod_upload_ids:
        from app.services.portal_automation.aggregate import build_unified_workbook_bytes
        from app.services.upload_ingest import ingest_file_bytes

        prod_recs_q = await db.execute(
            select(ClientRecord).where(ClientRecord.upload_id.in_(prod_upload_ids))
        )
        prod_records = [_record_to_dict(r) for r in prod_recs_q.scalars().all()]
        if prod_records:
            xlsx_bytes = build_unified_workbook_bytes(prod_records, as_of=batch_as_of)
            fname = f"פרודוקציה מאוחד {month_label}.xlsx".replace("  ", " ").strip()
            merged_prod_upload, _ = await ingest_file_bytes(
                db, user_id=user_id, content=xlsx_bytes, filename=fname,
                commit=False, make_active=True, company_source_override="מאוחד",
            )
            batch.merged_upload_id = merged_prod_upload.id
            # The merged "מאוחד" file supersedes every other active production
            # (a prior single-run active from before the batch must go inactive).
            await db.execute(
                update(FileUpload)
                .where(
                    FileUpload.user_id == user_id,
                    FileUpload.is_production.is_(True),
                    FileUpload.id != merged_prod_upload.id,
                )
                .values(is_production=False)
            )
            # Held per-company production data now lives in the merged file —
            # delete the held uploads so stray records can't be miscounted by
            # the generic comparison path (which treats every non-active-
            # production record as commission).
            await _delete_uploads(db, prod_upload_ids)
            await db.commit()

            # Invariant: exactly one active production upload remains.
            active_q = await db.execute(
                select(FileUpload.id).where(
                    FileUpload.user_id == user_id,
                    FileUpload.is_production.is_(True),
                )
            )
            active_ids = [i for (i,) in active_q.all()]
            if active_ids != [merged_prod_upload.id]:
                logger.error(
                    "Batch %s: expected 1 active production (%s), found %s",
                    batch.id, merged_prod_upload.id, active_ids,
                )

    # ── 3. Merge נפרעים → ONE commission upload ───────────────────────────
    merged_comm_upload = None
    if comm_upload_ids:
        from app.services.portal_automation.aggregate import build_unified_nifraim_bytes
        from app.services.upload_ingest import ingest_file_bytes

        # Stamp the source account (Harel agency logins download one נפרעים file
        # PER account — the account is in the filename) onto each record's
        # lead_source, so the merged file / download export shows which account
        # each row came from. Production already carries it via a per-row column.
        await _tag_source_accounts_from_filename(db, comm_upload_ids)

        comm_recs_q = await db.execute(
            select(ClientRecord).where(ClientRecord.upload_id.in_(comm_upload_ids))
        )
        comm_records = [_record_to_dict(r) for r in comm_recs_q.scalars().all()]
        if comm_records:
            nif_bytes = build_unified_nifraim_bytes(comm_records, period_label=month_label)
            fname = f"נפרעים מאוחד {month_label}.xlsx".replace("  ", " ").strip()
            merged_comm_upload, _ = await ingest_file_bytes(
                db, user_id=user_id, content=nif_bytes, filename=fname,
                commit=False, make_active=True, company_source_override="מאוחד",
            )
            batch.merged_commission_upload_id = merged_comm_upload.id
            # Delete the held per-company commission uploads so the merged file
            # is the single canonical commission source (no double-count, no
            # stray per-company rows in the comparison company list).
            held_comm = [cid for cid in comm_upload_ids if cid != merged_comm_upload.id]
            await _delete_uploads(db, held_comm)
            await db.commit()

    # ── 4. Per-category comparison (גמל + ביטוח) ──────────────────────────
    compared_categories: list[str] = []
    failed_categories: list[str] = []
    compare_skip_reason: str | None = None
    if merged_comm_upload is not None:
        compared_categories, failed_categories, compare_skip_reason = await _compare_merged(
            db, user_id, merged_comm_upload.id,
            merged_prod_upload_id=merged_prod_upload.id if merged_prod_upload else None,
            held_files_count=len(comm_upload_ids),
        )

    # ── 5. Production snapshot/summary hooks ──────────────────────────────
    if merged_prod_upload is not None:
        from app.services.upload_ingest import schedule_post_ingest
        try:
            schedule_post_ingest(user_id, merged_prod_upload.id, "production")
        except Exception as e:
            logger.warning("Batch %s: production post-ingest failed: %s", batch.id, e)

    # ── 6. Finalize status ────────────────────────────────────────────────
    if batch.failed == 0:
        batch.status = "success"
    elif batch.succeeded == 0:
        batch.status = "failed"
    else:
        batch.status = "partial"

    # A batch that downloaded commission data but produced no (or only partial)
    # comparisons must not finish green with empty comparison tabs — downgrade
    # a would-be success to partial and surface the reason.
    comparison_missing = bool(comm_upload_ids) and (
        merged_comm_upload is None or not compared_categories or bool(failed_categories)
    )
    if comparison_missing:
        if batch.status == "success":
            batch.status = "partial"
        if failed_categories:
            labels = [_CATEGORY_LABELS.get(c, c) for c in failed_categories]
            reason = "השוואת נפרעים נכשלה בקטגוריות: " + ", ".join(labels)
        elif compare_skip_reason == "no_production":
            # The נפרעים side succeeded — there was simply nothing to compare
            # against. Don't blame the commission downloads.
            reason = "השוואת נפרעים לא הופקה — אין קובץ פרודוקציה להשוואה"
        else:
            reason = "השוואת נפרעים לא הופקה — בדוק את הורדות הנפרעים"
        batch.error_message = (
            f"{batch.error_message} | {reason}" if batch.error_message else reason
        )

    # Success-with-losses: some run downloaded data that never reached the
    # merged files (failed fold leg / unrecognized format). The merged נפרעים
    # LOOKS fine but is missing whole companies — that must read as partial,
    # with the per-portal notes in the batch error (surfaced by the results
    # toast), not as a green batch.
    if partial_notes:
        if batch.status == "success":
            batch.status = "partial"
        note = "חברות עם נתונים חסרים באיחוד: " + " ; ".join(partial_notes)
        batch.error_message = (
            f"{batch.error_message} | {note}" if batch.error_message else note
        )[:2000]
    batch.finished_at = datetime.utcnow()
    await db.commit()


async def _compare_merged(
    db,
    user_id: uuid.UUID,
    merged_comm_upload_id: uuid.UUID,
    *,
    merged_prod_upload_id: uuid.UUID | None = None,
    held_files_count: int = 0,
) -> tuple[list[str], list[str], str | None]:
    """Run the comparison once per category against the batch's merged
    production (falling back to the newest active production) and persist a
    CommissionComparison row per category (so both tabs populate).

    Returns (persisted_categories, failed_categories, skip_reason) so run_batch
    can downgrade the batch status when comparisons are missing AND blame the
    right side — skip_reason is "no_production" when there was nothing to
    compare against (not a נפרעים problem), else None."""
    from app.models.upload import FileUpload
    from app.models.record import ClientRecord
    from app.models.paying_company import PayingCompany
    from app.models.commission_comparison import CommissionComparison
    from app.services.comparison_service import compute_comparison
    from app.services.portal_automation.aggregate import (
        commission_category_token,
        NIFRAIM_CATEGORY_GEMEL,
    )

    # Prefer the batch's just-merged production upload; otherwise the newest
    # active production. LIMIT 1 so a transient violation of the one-active
    # invariant can never raise MultipleResultsFound.
    prod_upload = None
    if merged_prod_upload_id is not None:
        prod_q = await db.execute(
            select(FileUpload).where(
                FileUpload.id == merged_prod_upload_id,
                FileUpload.user_id == user_id,
            )
        )
        prod_upload = prod_q.scalar_one_or_none()
    if prod_upload is None:
        prod_q = await db.execute(
            select(FileUpload)
            .where(
                FileUpload.user_id == user_id,
                FileUpload.is_production.is_(True),
            )
            .order_by(FileUpload.uploaded_at.desc())
            .limit(1)
        )
        prod_upload = prod_q.scalar_one_or_none()
    if not prod_upload:
        return [], [], "no_production"

    prod_recs_q = await db.execute(
        select(ClientRecord).where(ClientRecord.upload_id == prod_upload.id)
    )
    prod_dicts = [_record_to_dict(r) for r in prod_recs_q.scalars().all()]
    if not prod_dicts:
        return [], [], "no_production"

    comm_recs_q = await db.execute(
        select(ClientRecord).where(ClientRecord.upload_id == merged_comm_upload_id)
    )
    comm_dicts = [_record_to_dict(r) for r in comm_recs_q.scalars().all()]
    if not comm_dicts:
        return [], [], None

    paying_q = await db.execute(
        select(PayingCompany).where(PayingCompany.user_id == user_id)
    )
    paying_names = [p.company_name for p in paying_q.scalars().all()]

    # Split commission records by category token; pass only the matching
    # category's records to each comparison so cross-category rows don't leak.
    by_cat = {"gemel_hishtalmut": [], "insurance": []}
    for rec in comm_dicts:
        if commission_category_token(rec) == NIFRAIM_CATEGORY_GEMEL:
            by_cat["gemel_hishtalmut"].append(rec)
        else:
            by_cat["insurance"].append(rec)

    persisted: list[str] = []
    failed: list[str] = []
    for category, recs in by_cat.items():
        if not recs:
            continue
        try:
            comparison = compute_comparison(
                prod_dicts, recs, paying_names, category_override=category
            )
            sources = sorted({
                r.get("receiving_company") for r in recs if r.get("receiving_company")
            })
            comparison["commission_company_sources"] = sources
            comparison["commission_company_source"] = sources[0] if len(sources) == 1 else None
            if prod_upload.period_month is not None:
                comparison["period_month"] = prod_upload.period_month.isoformat()
            # Parity with compare-with-production (api/comparison.py): how many
            # held commission files were folded into this comparison.
            comparison["period_files_count"] = int(held_files_count)
            comparison["period_files_excluded"] = 0

            row = CommissionComparison(
                user_id=user_id,
                category=category,
                production_upload_id=prod_upload.id,
                summary_json=_jsonable(comparison.get("summary") or {}),
                result_json=_jsonable(comparison),
                commission_company_sources=_jsonable(sources),
            )
            db.add(row)
            await db.commit()
            persisted.append(category)

            # Sync the debts table (drives the insights dashboard + the
            # company-summary "gap" column), mirroring compare_with_production.
            try:
                from app.services.debt_service import sync_debts
                await sync_debts(
                    db, user_id, comparison,
                    production_upload_id=prod_upload.id,
                    commission_upload_id=merged_comm_upload_id,
                    category=category,
                )
                await db.commit()
            except Exception as de:
                logger.warning("Batch debt sync (%s) failed: %s", category, de)
                await db.rollback()
        except Exception as e:
            logger.warning("Batch compare (%s) failed: %s", category, e)
            await db.rollback()
            failed.append(category)

    return persisted, failed, None
