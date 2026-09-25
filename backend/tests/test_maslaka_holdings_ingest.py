"""Holdings / CONSLT ingest — REAL מסלקה answer files reach the DB and the right request.

    source backend/venv/bin/activate && python backend/tests/test_maslaka_holdings_ingest.py

Runs against the local dev DB with Swiftness's own published sample files
(fixtures/maslaka/swiftness_samples). Every row it creates is deleted in `finally`.

What this locks down (all found 2026-09-25, before the first live answer arrived):
  * `_ingest_holdings` used the stub parser (`<Product>`/`<RequestReference>`, tags that
    exist in no real file) — a real answer parsed to nothing and was ARCHIVED anyway.
  * The only real correlation key is MISPAR-MISLAKA (the מסלקה's request GUID): the
    receipt carries it next to our filename, every data file carries it per product.
  * An unroutable file must stay in the inbox (retried next poll), not be archived.
  * A production request (2000) must not expire before its due date; 2100 never.
"""

import asyncio
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SAMPLES = Path(__file__).parent / "fixtures" / "maslaka" / "swiftness_samples"
FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'} — {label}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILURES.append(label)


def sample(fragment: str) -> Path:
    return next(p for p in SAMPLES.iterdir() if fragment in p.name)


async def main() -> None:
    from sqlalchemy import delete, select
    from cryptography.fernet import Fernet
    from app.config import settings
    from app.database import async_session
    from app.models.pension_audit import PensionAuditLog, PensionRawPayload
    from app.models.pension_holding import PensionHolding
    from app.models.pension_inquiry import PensionInquiry
    from app.models.user import User
    from app.services.maslaka import adapter, orchestration

    assert "localhost" in settings.DATABASE_URL, "local dev DB only"
    settings.MASLAKA_ENCRYPTION_KEY = Fernet.generate_key().decode()
    import os
    os.environ["MASLAKA_ENCRYPTION_KEY"] = settings.MASLAKA_ENCRYPTION_KEY

    print("\nReceipts carry the request GUID:")
    fb = adapter.parse_feedback(sample("FEDBKA000009202412050929186535").read_bytes())
    check("FEDBKA → MISPAR-MISLAKA", fb.mislaka_number == "D825890C-EED8-459D-A005-6AF4A7DFC960",
          str(fb.mislaka_number))
    check("FEDBKA → the filename it answers", bool(fb.acked_filename), str(fb.acked_filename))

    print("\nholdings_index reads the real Mimshak paths:")
    ing = sample("CONSLTING").read_bytes()
    idx = adapter.holdings_index(ing)
    check("ING: customer 327824520 indexed", "327824520" in idx, str(list(idx)[:3]))
    check("ING: its GUID", idx.get("327824520", {}).get("guid") == "21808FCA-E800-40A8-B2C7-C93BD4022C62",
          str(idx.get("327824520")))
    check("ING: its body (מגדל ביטוח)", idx.get("327824520", {}).get("yatzran") == "520004896")
    kgm = adapter.holdings_index(sample("CONSLTKGM").read_bytes())
    check("KGM: one file answers several requests (distinct GUIDs)",
          len({v["guid"] for v in kgm.values()}) > 1, f"{len(kgm)} customers")

    created: list[uuid.UUID] = []
    try:
        async with async_session() as db:
            user = (await db.execute(select(User).where(User.email == "test@test.com"))).scalar_one()

        print("\nA data file whose GUID matches a request lands under that request:")
        async with async_session() as db:
            inq = PensionInquiry(
                user_id=user.id, customer_id_number="327824520", customer_name="בדיקה",
                status="acknowledged", interface_code="events_v007:9100",
                request_reference=f"test-hold-{uuid.uuid4().hex[:8]}",
                submitted_at=datetime.utcnow(), acknowledged_at=datetime.utcnow(),
                mislaka_number="21808FCA-E800-40A8-B2C7-C93BD4022C62",
            )
            db.add(inq)
            await db.commit()
            created.append(inq.id)
        async with async_session() as db:
            ok = await orchestration._ingest_holdings(db, ing, source_filename="ING.DAT", scope_user_id=None)
            await db.commit()
        check("routed → True (the caller archives)", ok is True)
        async with async_session() as db:
            rows = (await db.execute(select(PensionHolding).where(PensionHolding.inquiry_id == created[0]))).scalars().all()
            row = await db.get(PensionInquiry, created[0])
        check("holdings rows written", len(rows) >= 1, str(len(rows)))
        check("rows carry the customer", all(r.customer_id_number == "327824520" for r in rows))
        check("rows carry a balance", any((r.accumulation or 0) > 0 for r in rows),
              str([float(r.accumulation or 0) for r in rows]))
        check("rows carry the insurer", all(r.receiving_company for r in rows), rows[0].receiving_company if rows else "")
        check("request counted one answering body", row.providers_received == 1, str(row.providers_received))
        check("9100 → partial (other bodies may still answer)", row.status == "partial", row.status)

        print("\nA file nobody asked for stays in the inbox, nothing written:")
        async with async_session() as db:
            before = (await db.execute(select(PensionHolding.id))).scalars().all()
            ok = await orchestration._ingest_holdings(
                db, sample("CONSLTKGM").read_bytes(), source_filename="KGM.DAT", scope_user_id=None)
            await db.commit()
            after = (await db.execute(select(PensionHolding.id))).scalars().all()
        check("unroutable → False (left in inbox)", ok is False)
        check("no rows written for it", len(after) == len(before), f"{len(before)} → {len(after)}")

        print("\nExpiry: production requests keep their own clock:")
        async with async_session() as db:
            past = datetime.utcnow() - timedelta(days=1)
            one_off = PensionInquiry(
                user_id=user.id, customer_id_number="40336281", status="acknowledged",
                interface_code="events_v007:2000", request_reference=f"test-exp-{uuid.uuid4().hex[:8]}",
                target_yatzran_id="514956465", submitted_at=datetime.utcnow(), expires_at=past,
            )
            monthly = PensionInquiry(
                user_id=user.id, customer_id_number="40336281", status="acknowledged",
                interface_code="events_v007:2100", request_reference=f"test-exp-{uuid.uuid4().hex[:8]}",
                target_yatzran_id="514956465", submitted_at=datetime.utcnow() - timedelta(days=90), expires_at=past,
            )
            db.add_all([one_off, monthly])
            await db.commit()
            created += [one_off.id, monthly.id]
        async with async_session() as db:
            await orchestration.expire_stale_inquiries(db)
        async with async_session() as db:
            a = await db.get(PensionInquiry, one_off.id)
            b = await db.get(PensionInquiry, monthly.id)
        check("2000 not expired before its due date", a.status == "acknowledged", a.status)
        check("2100 never expires", b.status == "acknowledged", b.status)
    finally:
        if created:
            async with async_session() as db:
                await db.execute(delete(PensionHolding).where(PensionHolding.inquiry_id.in_(created)))
                await db.execute(delete(PensionRawPayload).where(PensionRawPayload.inquiry_id.in_(created)))
                await db.execute(delete(PensionAuditLog).where(PensionAuditLog.inquiry_id.in_(created)))
                await db.execute(delete(PensionInquiry).where(PensionInquiry.id.in_(created)))
                await db.commit()

    print("\n" + ("ALL PASS" if not FAILURES else f"{len(FAILURES)} FAILURE(S): " + "; ".join(FAILURES)))
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    asyncio.run(main())
