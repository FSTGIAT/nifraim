"""A failed ingest must not destroy the upload it was replacing.

`ingest_file_bytes` replaces on (user, filename, category): it DELETES the
prior upload and flushes, then builds the replacement. Before the savepoint,
a failure in between left the delete applied — and nothing rolled it back,
because the portal runner catches the ingest error, continues, and its outer
failure handler ends in `_set_status()` -> `await db.commit()`. That COMMITS
the orphaned delete, so a file that failed to ingest destroyed the good copy.

This test reproduces that exact sequence (ingest with commit=False, fail,
then commit anyway) and asserts the original upload survives.

Runs against the LOCAL dev database and cleans up after itself.
"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from sqlalchemy import delete, select  # noqa: E402

from app.database import async_session, engine  # noqa: E402
from app.models.record import ClientRecord  # noqa: E402
from app.models.upload import FileUpload  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import upload_ingest as ui  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "Ild_prod_1_09344_30042026.zip"
FILENAME = "savepoint-probe.zip"

_fails = 0
_checks = 0


def check(label, got, want):
    global _fails, _checks
    _checks += 1
    ok = got == want
    if not ok:
        _fails += 1
    print(f"  {'PASS' if ok else 'FAIL'}  {label}: got {got!r} want {want!r}")


@pytest.mark.asyncio
async def test_failed_ingest_preserves_prior_upload():
    # The module-level engine pools asyncpg connections bound to whichever
    # event loop first used them. pytest-asyncio gives each test its own loop,
    # so a pooled connection from an earlier DB test raises "attached to a
    # different loop" here. Dispose first for a clean pool on THIS loop.
    await engine.dispose()

    content = FIXTURE.read_bytes()
    uid = None
    try:
        async with async_session() as db:
            user = User(
                email=f"savepoint-{uuid.uuid4().hex[:8]}@test.local",
                username=f"sp{uuid.uuid4().hex[:8]}",
                hashed_password="x",
            )
            db.add(user)
            await db.commit()
            uid = user.id

        # ── 1. the good upload lands ────────────────────────────────────
        async with async_session() as db:
            up, fmt = await ui.ingest_file_bytes(
                db, user_id=uid, content=content, filename=FILENAME,
                commit=True, make_active=False,
            )
            first_id, first_count = up.id, up.record_count
        print(f"\nbaseline: upload {str(first_id)[:8]} fmt={fmt} records={first_count}")
        check("baseline has records", first_count > 0, True)

        # ── 2. re-ingest the SAME filename, failing AFTER the delete ────
        # sanitize_record runs per row, after the old upload is deleted and
        # flushed and the replacement FileUpload is created — the same window
        # the live NameError crashed in.
        original = ui.sanitize_record
        ui.sanitize_record = lambda rec: (_ for _ in ()).throw(
            ValueError("simulated post-delete ingest failure")
        )
        try:
            async with async_session() as db:
                raised = None
                try:
                    # commit=False: exactly how the portal runner calls it.
                    await ui.ingest_file_bytes(
                        db, user_id=uid, content=content, filename=FILENAME,
                        commit=False, make_active=False,
                    )
                except Exception as e:
                    raised = type(e).__name__
                check("ingest raised", raised is not None, True)

                # The runner swallows it, then _set_status() COMMITS.
                # Pre-savepoint this is what persisted the orphaned delete.
                await db.commit()
        finally:
            ui.sanitize_record = original

        # ── 3. the original upload must still be there ──────────────────
        async with async_session() as db:
            rows = (await db.execute(
                select(FileUpload).where(
                    FileUpload.user_id == uid, FileUpload.filename == FILENAME
                )
            )).scalars().all()
            check("exactly one upload still present", len(rows), 1)
            check("it is the ORIGINAL upload", rows and rows[0].id == first_id, True)
            check("record_count intact", rows and rows[0].record_count, first_count)

            n = len((await db.execute(
                select(ClientRecord).where(ClientRecord.upload_id == first_id)
            )).scalars().all())
            check("its client_records intact", n, first_count)

        # ── 4. a real re-ingest still replaces ──────────────────────────
        async with async_session() as db:
            up2, _ = await ui.ingest_file_bytes(
                db, user_id=uid, content=content, filename=FILENAME,
                commit=True, make_active=False,
            )
            check("replacement is a NEW upload", up2.id != first_id, True)
            # The savepoint is RELEASEd, then commit() + refresh() run outside
            # it. Callers read these straight off the returned object
            # (api/uploads.py -> file_type, runner.py -> file_category +
            # company_source, mail_intake -> is_production), so a stale or
            # expired instance here would break them with MissingGreenlet.
            check("returned obj: file_type loads", up2.file_type, "zip")
            check("returned obj: file_category loads", up2.file_category, "production")
            check("returned obj: company_source loads", bool(up2.company_source), True)
            check("returned obj: is_production loads", up2.is_production, False)
            check("returned obj: record_count loads", up2.record_count, first_count)
            rows = (await db.execute(
                select(FileUpload).where(
                    FileUpload.user_id == uid, FileUpload.filename == FILENAME
                )
            )).scalars().all()
            check("still exactly one upload", len(rows), 1)
            gone = (await db.execute(
                select(ClientRecord).where(ClientRecord.upload_id == first_id)
            )).scalars().all()
            check("old records cleaned up", len(gone), 0)
    finally:
        if uid:
            async with async_session() as db:
                ups = (await db.execute(
                    select(FileUpload.id).where(FileUpload.user_id == uid)
                )).scalars().all()
                if ups:
                    await db.execute(
                        delete(ClientRecord).where(ClientRecord.upload_id.in_(ups))
                    )
                    await db.execute(delete(FileUpload).where(FileUpload.user_id == uid))
                await db.execute(delete(User).where(User.id == uid))
                await db.commit()
            print("cleaned up")

    assert _fails == 0, f"{_fails}/{_checks} checks failed"
