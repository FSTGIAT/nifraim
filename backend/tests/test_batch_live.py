"""Full LIVE end-to-end test of the "run all portals" batch.

Goal (user): press the auto-download button → every company logs into its site,
passes OTP (auto-routed per company by the otp_routing layer), downloads, and the
results aggregate into ONE production file + ONE נפרעים file. This harness drives
the REAL batch (real browsers, real logins, real OTP) and then asserts the two
merged files cover the expected companies.

Why a standalone script (not pytest): a live run blocks on each portal's SMS OTP,
which the user forwards from their phone. Running `run_batch` directly here (NOT
through the reloading uvicorn API) makes the in-flight run immune to
`uvicorn --reload` restarts (this process owns its own browser + DB session).

Phoenix note: the manual Phoenix production flow opens a legacy Ericom green-screen
terminal that Playwright cannot drive (see phoenix.py docstring); the automation
uses the modern Angular SPA via `phoenix_nifraim` instead, which downloads the
Phoenix נפרעים reports and reshapes them to production. So Phoenix appears on the
PRODUCTION side only — there is no separate Phoenix נפרעים file by design.

Modes:
    python tests/test_batch_live.py preflight        # cred readiness matrix, no run
    python tests/test_batch_live.py report [batch_id]# coverage report on a batch (latest if omitted)
    python tests/test_batch_live.py run              # LIVE: seed a batch, run it, report

Run:
    source /home/roygi/test/backend/venv/bin/activate
    python3 /home/roygi/test/backend/tests/test_batch_live.py run
"""

import asyncio
import sys
import uuid
from datetime import datetime

sys.path.insert(0, "/home/roygi/test/backend")

from sqlalchemy import select, func

from app.database import async_session
from app.models.user import User
from app.models.portal_credential import PortalCredential
from app.models.portal_run import PortalRun
from app.models.portal_run_batch import PortalRunBatch
from app.models.upload import FileUpload
from app.models.record import ClientRecord
from app.models.commission_comparison import CommissionComparison

# ── Target coverage: 5 companies, ONE consolidated credential each that
# downloads BOTH production AND נפרעים in a single run (Part E). ─────────────────
COMPANIES = ["כלל", "מגדל", "מנורה", "הראל", "הפניקס"]
# The single batch credential per company (its consolidated plugin yields both
# categories). The standalone נפרעים/sfe plugins are include_in_batch=False.
CONSOLIDATED_PORTAL = {
    "כלל": "clal",
    "מגדל": "migdal",
    "מנורה": "menora",
    "הראל": "harel_savings",
    "הפניקס": "phoenix_nifraim",
}
# Each consolidated credential is expected to produce BOTH a production and a
# נפרעים file → merged production = 5 companies, merged נפרעים = 5 companies.
PRODUCTION_PORTALS = {c: [p] for c, p in CONSOLIDATED_PORTAL.items()}
NIFRAIM_PORTALS = {c: [p] for c, p in CONSOLIDATED_PORTAL.items()}


def normalize_company(name: str | None) -> str | None:
    """Map a record's receiving_company to its base company group.
    e.g. 'הפניקס גמל'→'הפניקס', 'הראל מגוון'→'הראל'."""
    if not name:
        return None
    n = str(name)
    for base, needles in {
        "הפניקס": ["פניקס", "fnx", "phoenix"],
        "מגדל": ["מגדל", "migdal"],
        "מנורה": ["מנורה", "menora"],
        "הראל": ["הראל", "harel"],
        "כלל": ["כלל", "clal"],
    }.items():
        if any(x in n.lower() or x in n for x in needles):
            return base
    return n  # unknown — surface as-is


async def _cred_owner_id(db) -> uuid.UUID | None:
    """User with the most active portal credentials (the batch's owner)."""
    q = await db.execute(
        select(PortalCredential.user_id, func.count(PortalCredential.id))
        .where(PortalCredential.is_active.is_(True))
        .group_by(PortalCredential.user_id)
        .order_by(func.count(PortalCredential.id).desc())
    )
    row = q.first()
    return row[0] if row else None


async def _active_portal_kinds(db, user_id) -> set[str]:
    q = await db.execute(
        select(PortalCredential.portal_kind).where(
            PortalCredential.user_id == user_id,
            PortalCredential.is_active.is_(True),
        )
    )
    return {k for (k,) in q.all()}


async def preflight(db, user_id) -> bool:
    """Print the company×category credential-readiness matrix. Returns True if
    every company has at least a production source (the minimum to be useful)."""
    active = await _active_portal_kinds(db, user_id)
    print("\n=== CREDENTIAL READINESS (active creds for batch user) ===")
    print(f"{'company':8} {'production':28} {'נפרעים':28}")
    all_prod_ok = True
    missing: list[str] = []
    for c in COMPANIES:
        prod_kinds = PRODUCTION_PORTALS[c]
        nif_kinds = NIFRAIM_PORTALS[c]
        prod_have = [k for k in prod_kinds if k in active]
        nif_have = [k for k in nif_kinds if k in active]
        prod_cell = ("✅ " + ",".join(prod_have)) if prod_have else "❌ " + "/".join(prod_kinds)
        if nif_kinds:
            nif_cell = ("✅ " + ",".join(nif_have)) if nif_have else "❌ " + "/".join(nif_kinds)
        else:
            nif_cell = "— (production-only)"
        print(f"{c:8} {prod_cell:28} {nif_cell:28}")
        if not prod_have:
            all_prod_ok = False
            missing.extend(prod_kinds)
        if nif_kinds and not nif_have:
            missing.extend(nif_kinds)
    if missing:
        print(f"\n⚠️  Missing creds (add via UI with real passwords): {sorted(set(missing))}")
    else:
        print("\n✅ All target portals have an active credential.")
    return all_prod_ok


async def report_batch_coverage(db, batch: PortalRunBatch) -> bool:
    """Print the per-company PASS/FAIL matrix for a finished batch and return
    whether production covers 5 companies + נפרעים covers 4."""
    print(f"\n=== BATCH {batch.id} COVERAGE ===")
    print(f"status={batch.status} total={batch.total} ok={batch.succeeded} fail={batch.failed}")
    print(f"merged_production={batch.merged_upload_id}  merged_נפרעים={batch.merged_commission_upload_id}")

    async def _companies(upload_id) -> dict[str, int]:
        if not upload_id:
            return {}
        q = await db.execute(
            select(ClientRecord.receiving_company, func.count(ClientRecord.id))
            .where(ClientRecord.upload_id == upload_id)
            .group_by(ClientRecord.receiving_company)
        )
        out: dict[str, int] = {}
        for name, n in q.all():
            base = normalize_company(name)
            if base:
                out[base] = out.get(base, 0) + n
        return out

    prod = await _companies(batch.merged_upload_id)
    nif = await _companies(batch.merged_commission_upload_id)

    print(f"\n{'company':8} {'production':>16} {'נפרעים':>16}")
    prod_ok = nif_ok = 0
    for c in COMPANIES:
        p = prod.get(c, 0)
        n = nif.get(c, 0)
        expect_nif = bool(NIFRAIM_PORTALS[c])
        p_mark = f"✅ {p}" if p else "❌ 0"
        if expect_nif:
            n_mark = f"✅ {n}" if n else "❌ 0"
        else:
            n_mark = "— prod-only"
        print(f"{c:8} {p_mark:>16} {n_mark:>16}")
        if p:
            prod_ok += 1
        if expect_nif and n:
            nif_ok += 1

    # CommissionComparison rows (both categories should exist after a merge).
    cc = await db.execute(
        select(CommissionComparison.category)
        .where(CommissionComparison.user_id == batch.user_id)
        .order_by(CommissionComparison.id.desc())
        .limit(6)
    )
    cats = {c for (c,) in cc.all()}
    print(f"\nrecent CommissionComparison categories: {sorted(cats)}")

    prod_target, nif_target = 5, 4
    ok = prod_ok >= prod_target and nif_ok >= nif_target
    print(
        f"\nPRODUCTION companies: {prod_ok}/{prod_target}   "
        f"נפרעים companies: {nif_ok}/{nif_target}   "
        f"→ {'PASS ✅' if ok else 'INCOMPLETE ❌'}"
    )
    return ok


async def run_live(db, user_id) -> None:
    """Seed a PortalRunBatch and run it directly, forwarding OTPs via the phone."""
    from app.services.portal_automation.batch_runner import run_batch

    batch = PortalRunBatch(user_id=user_id, status="pending", started_at=datetime.utcnow())
    db.add(batch)
    await db.commit()
    await db.refresh(batch)
    batch_id = batch.id
    print(f"\n[live] PortalRunBatch {batch_id} created — launching run_batch()")
    print("[live] Forward each company's OTP from your phone as it logs in.")
    print("[live] OTPs are auto-routed to the right portal (otp_routing).\n")

    task = asyncio.create_task(run_batch(batch_id))

    last = None
    while not task.done():
        await asyncio.sleep(2)
        async with async_session() as db2:
            b = (await db2.execute(select(PortalRunBatch).where(PortalRunBatch.id == batch_id))).scalar_one()
            cur = b.current_run_id
            label = f"{b.status} ok={b.succeeded} fail={b.failed}"
            if cur:
                cr = (await db2.execute(
                    select(PortalRun.status, PortalCredential.portal_kind)
                    .join(PortalCredential, PortalCredential.id == PortalRun.credential_id)
                    .where(PortalRun.id == cur)
                )).first()
                if cr:
                    label += f" | current: {cr[1]} [{cr[0]}]"
                    if cr[0] == "awaiting_otp":
                        label += "  ⏳ FORWARD THIS COMPANY'S OTP NOW"
        if label != last:
            print(f"[live] {label}")
            last = label

    await task
    async with async_session() as db3:
        b = (await db3.execute(select(PortalRunBatch).where(PortalRunBatch.id == batch_id))).scalar_one()
        ok = await report_batch_coverage(db3, b)
    print("\nLIVE BATCH E2E:", "PASS ✅" if ok else "INCOMPLETE ❌")
    sys.exit(0 if ok else 1)


async def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "preflight"
    async with async_session() as db:
        user_id = await _cred_owner_id(db)
        if user_id is None:
            print("No user has active portal credentials.")
            sys.exit(1)
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
        print(f"Batch user: {user.email} ({user_id})")

        if mode == "preflight":
            await preflight(db, user_id)
        elif mode == "report":
            if len(sys.argv) > 2:
                bid = uuid.UUID(sys.argv[2])
                b = (await db.execute(select(PortalRunBatch).where(PortalRunBatch.id == bid))).scalar_one()
            else:
                b = (await db.execute(
                    select(PortalRunBatch).order_by(PortalRunBatch.started_at.desc()).limit(1)
                )).scalar_one_or_none()
                if b is None:
                    print("No batches found.")
                    sys.exit(1)
            await report_batch_coverage(db, b)
        elif mode == "run":
            await preflight(db, user_id)
            await run_live(db, user_id)
        else:
            print(__doc__)
            sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())
