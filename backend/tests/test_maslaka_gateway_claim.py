"""Maslaka Gateway claim-loop tests — the OUTBOUND leg that must not run on Railway.

    source backend/venv/bin/activate && python backend/tests/test_maslaka_gateway_claim.py

Runs against the local dev DB and a throwaway temp vault. Every row it creates is
deleted in `finally` (`submit_inquiry` commits, so it cannot wrap itself in one
transaction — same constraint as test_mail_intake.py).

What actually carries weight here:
  * a `pending` row is claimed, its XML lands in the vault OUTBOX, and only THEN
    does the row advance to `submitted` — the ordering invariant #3 is about;
  * a second concurrent claimer SKIPs the locked row instead of double-sending;
  * the worker REFUSES to start on a relative MASLAKA_LOCAL_* path, which would
    otherwise auto-create an empty vault that passes healthcheck() forever.

NOT covered, and not coverable today: a real Transporter picking the file out of
OUT, real XSD-shaped XML (adapter.py still has TODO(XSD)), the IN round-trip.
"""

import asyncio
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'} — {label}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILURES.append(label)


async def test_claim_and_skip_locked() -> None:
    from sqlalchemy import delete, select
    from app.config import settings
    from app.database import async_session
    from app.models.pension_audit import PensionAuditLog, PensionRawPayload
    from app.models.pension_inquiry import PensionInquiry
    from app.models.user import User
    from app.services.maslaka import orchestration
    from app.services.maslaka.transport import reset_transport_for_tests

    # A throwaway vault so the test never writes into a real Transporter folder.
    vault = Path(tempfile.mkdtemp(prefix="maslaka_test_"))
    settings.MASLAKA_TRANSPORT = "local"
    settings.MASLAKA_LOCAL_OUTBOX = str(vault / "outbox")
    settings.MASLAKA_LOCAL_INBOX = str(vault / "inbox")
    settings.MASLAKA_LOCAL_ARCHIVE = str(vault / "archive")
    settings.MASLAKA_AGENT_NUMBER = "TEST-AGENT-1"
    settings.MASLAKA_AGENT_ID = "123456789"
    settings.MASLAKA_ENCRYPTION_KEY = __import__("cryptography.fernet", fromlist=["Fernet"]).Fernet.generate_key().decode()
    reset_transport_for_tests()

    created: list[uuid.UUID] = []
    try:
        async with async_session() as db:
            user = (await db.execute(select(User).limit(1))).scalars().first()
            if not user:
                print("  SKIP — no user in local db")
                return

            inq = await orchestration.create_inquiry(
                db, user_id=user.id, customer_id_number="058661554", customer_name="בדיקה",
            )
            created.append(inq.id)
            check("create_inquiry leaves the row pending (cloud never sends)",
                  inq.status == "pending", inq.status)
            check("customer id is leading-zero stripped",
                  inq.customer_id_number == "58661554", inq.customer_id_number)

        # ── the claim itself ────────────────────────────────────────────────
        async with async_session() as db:
            claimed = await orchestration.claim_and_submit_one(db)
        check("claim_and_submit_one returns the pending row", claimed == created[0], str(claimed))

        outbox = Path(settings.MASLAKA_LOCAL_OUTBOX)
        files = [p for p in outbox.iterdir() if p.is_file()]
        check("exactly one XML landed in the vault OUTBOX", len(files) == 1,
              ", ".join(p.name for p in files))
        check("no .tmp left behind (atomic write completed)",
              not any(p.suffix == ".tmp" for p in files))

        async with async_session() as db:
            row = await db.get(PensionInquiry, created[0])
            check("row advanced to submitted", row.status == "submitted", row.status)
            check("vault filename recorded on the row",
                  bool(row.vault_outbound_filename) and row.vault_outbound_filename == files[0].name,
                  str(row.vault_outbound_filename))
            check("submitted_at stamped", row.submitted_at is not None)

        # ── the queue is now empty ──────────────────────────────────────────
        async with async_session() as db:
            check("empty queue returns None", await orchestration.claim_and_submit_one(db) is None)

        # ── SKIP LOCKED: two claimers, one row ──────────────────────────────
        async with async_session() as db:
            inq2 = await orchestration.create_inquiry(
                db, user_id=user.id, customer_id_number="11122233", customer_name="נעילה",
            )
            created.append(inq2.id)

        # Session A takes the row lock and HOLDS it (no commit) while session B tries.
        async with async_session() as db_a, async_session() as db_b:
            locked = (await db_a.execute(
                select(PensionInquiry.id)
                .where(PensionInquiry.status == "pending")
                .order_by(PensionInquiry.created_at).limit(1)
                .with_for_update(skip_locked=True)
            )).scalar_one_or_none()
            check("session A locks the pending row", locked == inq2.id, str(locked))
            second = await orchestration.claim_and_submit_one(db_b)
            check("session B SKIPs the locked row (no double-send)", second is None, str(second))
            await db_a.rollback()

        files_after = [p for p in outbox.iterdir() if p.is_file()]
        check("the skipped row produced NO second file", len(files_after) == 1,
              f"{len(files_after)} files")

        # ── identity refusal (invariant #1) ─────────────────────────────────
        settings.MASLAKA_AGENT_NUMBER = ""
        async with async_session() as db:
            await orchestration.claim_and_submit_one(db)
            row2 = await db.get(PensionInquiry, inq2.id)
            await db.refresh(row2)
        check("unidentified request fails the row instead of sending",
              row2.status == "failed" and row2.error_code == "identity_not_configured",
              f"{row2.status}/{row2.error_code}")
        files_final = [p for p in outbox.iterdir() if p.is_file()]
        check("still no file written for the unidentified request", len(files_final) == 1,
              f"{len(files_final)} files")

    finally:
        settings.MASLAKA_AGENT_NUMBER = "TEST-AGENT-1"
        if created:
            async with async_session() as db:
                await db.execute(delete(PensionRawPayload).where(PensionRawPayload.inquiry_id.in_(created)))
                await db.execute(delete(PensionAuditLog).where(PensionAuditLog.inquiry_id.in_(created)))
                await db.execute(delete(PensionInquiry).where(PensionInquiry.id.in_(created)))
                await db.commit()
        shutil.rmtree(vault, ignore_errors=True)
        reset_transport_for_tests()


async def test_worker_tick() -> None:
    """One real `_tick()` — the only path in maslaka_worker.py with no other cover.

    Exercises both branches: the outbound drain AND the inbox poll, including that
    `_last_poll_at` (module-level, mutated via `global`) actually advances so the
    poll does not re-fire every 10s.
    """
    from sqlalchemy import delete, select
    from app.config import settings
    from app.database import async_session
    from app.models.pension_audit import PensionAuditLog, PensionRawPayload
    from app.models.pension_inquiry import PensionInquiry
    from app.models.user import User
    from app.services.maslaka import orchestration
    from app.services.maslaka.transport import reset_transport_for_tests
    import maslaka_worker

    vault = Path(tempfile.mkdtemp(prefix="maslaka_tick_"))
    settings.MASLAKA_TRANSPORT = "local"
    settings.MASLAKA_LOCAL_OUTBOX = str(vault / "outbox")
    settings.MASLAKA_LOCAL_INBOX = str(vault / "inbox")
    settings.MASLAKA_LOCAL_ARCHIVE = str(vault / "archive")
    settings.MASLAKA_AGENT_NUMBER = "TEST-AGENT-1"
    settings.MASLAKA_AGENT_ID = "123456789"
    settings.MASLAKA_POLL_INTERVAL_MINUTES = 15
    reset_transport_for_tests()

    created: list[uuid.UUID] = []
    try:
        async with async_session() as db:
            user = (await db.execute(select(User).limit(1))).scalars().first()
            if not user:
                print("  SKIP — no user in local db")
                return
            inq = await orchestration.create_inquiry(
                db, user_id=user.id, customer_id_number="99887766", customer_name="tick",
            )
            created.append(inq.id)

        check("first tick polls immediately (datetime.min, not utcnow)",
              maslaka_worker._last_poll_at == __import__("datetime").datetime.min)

        await maslaka_worker._tick()

        files = [p for p in Path(settings.MASLAKA_LOCAL_OUTBOX).iterdir() if p.is_file()]
        check("_tick drained the outbound queue", len(files) == 1, f"{len(files)} files")

        # REGRESSION (2026-09-10): the submit path used to write
        # `events_v007_<hex>.xml`, which is not a legal name under נספח ו' at
        # all. The מסלקה matches on the NAME before it parses any XML, so every
        # request the app sent by itself was unidentifiable. Guard the grammar,
        # and guard that the suffix agrees with the payload's KOD-SVIVAT-AVODA —
        # a `.DAT` name over a `KOD-SVIVAT-AVODA=2` body is what we actually
        # shipped into the TST vault, and nothing ever answered it.
        from app.services.maslaka.filenames import parse_filename
        from app.services.maslaka.events import environment
        parsed = parse_filename(files[0].name)
        check("vault filename is legal under נספח ו'", parsed is not None, files[0].name)
        if parsed:
            env_code, file_type = environment()
            check("filename suffix agrees with the environment code",
                  parsed.file_type == file_type, f"{parsed.file_type} vs {file_type}")
            check("outbound direction is בעל רישיון → מסלקה",
                  parsed.direction == "001", parsed.direction)
            check("service is EVENTS v007",
                  parsed.service == "EVENTS" and parsed.version == "007",
                  f"{parsed.service}/{parsed.version}")
            body = files[0].read_bytes().decode("utf-8")
            check("payload KOD-SVIVAT-AVODA matches the suffix",
                  f"<KOD-SVIVAT-AVODA>{env_code}</KOD-SVIVAT-AVODA>" in body)
        async with async_session() as db:
            row = await db.get(PensionInquiry, created[0])
        check("_tick advanced the row to submitted", row.status == "submitted", row.status)
        check("_tick ran the inbox poll and advanced _last_poll_at",
              maslaka_worker._last_poll_at > __import__("datetime").datetime.min)

        # REGRESSION (2026-09-10): the daily sequence must be UNIQUE per sender
        # per day. `submit_pending_inquiries` drains up to 20 rows per tick, so
        # a hardcoded sequence gives every file in the batch the SAME name —
        # the Transporter uploads one and silently drops the rest, with no
        # error in any log. One file proves nothing; three must differ.
        before_n = len(files)
        async with async_session() as db:
            for i in range(3):
                inq = await orchestration.create_inquiry(
                    db, user_id=user.id, customer_id_number=f"9988770{i}", customer_name="batch",
                )
                created.append(inq.id)
        await maslaka_worker._tick()

        batch = sorted(p.name for p in Path(settings.MASLAKA_LOCAL_OUTBOX).iterdir() if p.is_file())
        new_names = batch[-3:] if len(batch) >= before_n + 3 else []
        check("the 3-row batch drained", len(batch) == before_n + 3, f"{len(batch)} files")
        check("every filename in the batch is DISTINCT (no sequence collision)",
              len(set(new_names)) == 3, ", ".join(new_names))
        seqs = [parse_filename(n).sequence for n in new_names if parse_filename(n)]
        check("all three parse and carry distinct sequences",
              len(seqs) == 3 and len(set(seqs)) == 3, ",".join(seqs))

        # Second tick must NOT re-poll (interval not elapsed) but must still drain.
        before = maslaka_worker._last_poll_at
        await maslaka_worker._tick()
        check("second tick does not re-poll inside the interval",
              maslaka_worker._last_poll_at == before)
    finally:
        if created:
            async with async_session() as db:
                await db.execute(delete(PensionRawPayload).where(PensionRawPayload.inquiry_id.in_(created)))
                await db.execute(delete(PensionAuditLog).where(PensionAuditLog.inquiry_id.in_(created)))
                await db.execute(delete(PensionInquiry).where(PensionInquiry.id.in_(created)))
                await db.commit()
        shutil.rmtree(vault, ignore_errors=True)
        reset_transport_for_tests()


def test_preflight_refusals() -> None:
    """The worker must refuse to boot on the misconfigurations that otherwise
    fail silently. Run as a subprocess so we test the real entrypoint."""
    worker = Path(__file__).resolve().parents[1] / "maslaka_worker.py"
    import os

    def run(env_extra: dict[str, str]) -> tuple[int, str]:
        env = {**os.environ, **env_extra}
        p = subprocess.run([sys.executable, str(worker)], capture_output=True,
                           text=True, timeout=120, env=env, cwd=str(worker.parent))
        return p.returncode, (p.stdout + p.stderr)

    base = {
        "MASLAKA_ENABLED": "true", "MASLAKA_VAULT_HOST": "true",
        "MASLAKA_AGENT_NUMBER": "A1", "MASLAKA_AGENT_ID": "123456789",
        "MASLAKA_TRANSPORT": "local",
        "MASLAKA_LOCAL_OUTBOX": "/tmp/mk/out", "MASLAKA_LOCAL_INBOX": "/tmp/mk/in",
        "MASLAKA_LOCAL_ARCHIVE": "/tmp/mk/arch",
    }

    rc, out = run({**base, "MASLAKA_VAULT_HOST": "false"})
    check("refuses to start when MASLAKA_VAULT_HOST=false", rc == 2 and "VAULT_HOST" in out, f"rc={rc}")

    rc, out = run({**base, "MASLAKA_ENABLED": "false"})
    check("refuses to start when MASLAKA_ENABLED=false", rc == 2 and "MASLAKA_ENABLED" in out, f"rc={rc}")

    rc, out = run({**base, "MASLAKA_AGENT_NUMBER": "", "MASLAKA_AGENT_ID": ""})
    check("refuses to start with no clearinghouse identity", rc == 2 and "AGENT_NUMBER" in out, f"rc={rc}")

    rc, out = run({**base, "MASLAKA_LOCAL_OUTBOX": "./maslaka_vault/outbox"})
    check("refuses to start on a RELATIVE vault path (invariant #4)",
          rc == 2 and "RELATIVE" in out, f"rc={rc}")


if __name__ == "__main__":
    print("Maslaka Gateway claim loop")
    print("\nPreflight refusals (subprocess, real entrypoint):")
    test_preflight_refusals()
    # One event loop for every async test: the SQLAlchemy async engine caches
    # connections bound to the loop that created them, so a second asyncio.run()
    # fails with "attached to a different loop".
    async def _db_tests() -> None:
        print("\nClaim / SKIP LOCKED / identity (local dev DB + temp vault):")
        await test_claim_and_skip_locked()
        print("\nWorker _tick() — drain + poll cadence:")
        await test_worker_tick()

    asyncio.run(_db_tests())
    print("\n" + ("ALL PASS" if not FAILURES else f"{len(FAILURES)} FAILURE(S): " + "; ".join(FAILURES)))
    sys.exit(1 if FAILURES else 0)
