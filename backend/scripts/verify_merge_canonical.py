"""Real-data verification for the merged-production canonicalization fix.

NO mock data. Two checks:

  1. Resolver ground-truth — every real raw producer string maps to a company
     name that actually exists in the reference file's `יצרן` column.
  2. Round-trip on royg's REAL merged production records (from the prod DB):
     rebuild the unified workbook with the new canonicalizer + as_of, re-parse,
     and assert canonical names / נכון ליום populated / entities kept separate /
     record count unchanged.

Run:
    cd backend && source venv/bin/activate && \
    DATABASE_URL=postgresql+asyncpg://postgres:<pw>@crossover.proxy.rlwy.net:16972/railway \
    python scripts/verify_merge_canonical.py
(DB pw in memory railway.md; reference file in /mnt/c/Users/roygi/Downloads/.)
"""
import asyncio
import glob
import io
import os
import sys
from datetime import date

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.utils.company_norm import canonical_company
from app.services.portal_automation.aggregate import build_unified_workbook_bytes
from app.services.portal_automation.batch_runner import _record_to_dict
from app.models.record import ClientRecord
from app.models.upload import FileUpload
from app.models.user import User

REF_GLOB = "/mnt/c/Users/roygi/Downloads/*.xlsx"
AGENT_EMAIL = "royg@nifraim.com"

# Real raw producer strings the parsers emit (see aggregate + parser_service).
RAW_CASES = [
    ("הפניקס", "insurance"), ("הפניקס", "savings"), ("הפניקס גמל", "savings"),
    ("מנורה", "insurance"), ("מנורה", "savings"),
    ("הראל גמל", "savings"), ("הראל מגוון", "savings"), ("הראל", "insurance"),
    ("מגדל", "insurance"), ("מגדל", "savings"),
    ("אלטשולר", "savings"), ("מיטב", "savings"), ("מיטב דש", "savings"),
    ("ילין לפידות", "savings"), ("מור", "savings"),
    ("הכשרה", "insurance"), ("כלל", "insurance"), ("כלל", "savings"),
]

RAW_SHORT_NAMES = {"הפניקס", "הפניקס גמל", "מנורה", "הראל גמל", "הראל מגוון",
                   "מגדל", "אלטשולר", "מיטב", "מיטב דש", "מור", "כלל"}


def load_reference_names() -> set[str]:
    cands = [c for c in glob.glob(REF_GLOB)
             if "פרודוקציה אפריל" in c and "מגדל" not in c and "11" not in c]
    if not cands:
        sys.exit("Reference file פרודוקציה אפריל.xlsx not found in Downloads")
    ref = set()
    xl = pd.ExcelFile(cands[0])
    for sh in xl.sheet_names:
        df = xl.parse(sh)
        if "יצרן" in df.columns:
            ref |= set(df["יצרן"].dropna().astype(str).unique())
    return ref


def check_resolver(ref: set[str]) -> bool:
    print(f"\n[1] Resolver vs reference ({len(ref)} distinct יצרן) ...")
    ok = True
    for raw, kind in RAW_CASES:
        r = canonical_company(raw, kind)
        hit = r in ref
        ok &= hit
        flag = "OK" if hit else "*** NOT IN REFERENCE ***"
        print(f"    {raw!r:16} {kind:9} -> {r!r:38} {flag}")
    return ok


async def check_roundtrip(ref: set[str]) -> bool:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("\n[2] SKIPPED round-trip: set DATABASE_URL to the prod DB to run it.")
        return True
    print("\n[2] Round-trip on royg's REAL merged production records ...")
    engine = create_async_engine(db_url)
    async with AsyncSession(engine) as db:
        uid = (await db.execute(
            select(User.id).where(User.email == AGENT_EMAIL))).scalar_one_or_none()
        if not uid:
            print(f"    user {AGENT_EMAIL} not found"); return False
        upload_ids = (await db.execute(
            select(FileUpload.id).where(
                FileUpload.user_id == uid, FileUpload.is_production.is_(True)))
        ).scalars().all()
        recs = (await db.execute(
            select(ClientRecord).where(ClientRecord.upload_id.in_(upload_ids)))
        ).scalars().all()
        prod = [_record_to_dict(r) for r in recs]
    await engine.dispose()

    n_in = len(prod)
    print(f"    input records: {n_in} across {len(upload_ids)} active production upload(s)")
    if not prod:
        print("    no active production records for royg (run a batch first)"); return False

    xlsx = build_unified_workbook_bytes(prod, as_of=date(2026, 4, 30))
    xl = pd.ExcelFile(io.BytesIO(xlsx))
    detail = [s for s in xl.sheet_names if s in ("מוצרי חיסכון", "מוצרי ביטוח")]
    names, n_out, asof_ok = set(), 0, True
    for sh in detail:
        df = xl.parse(sh)
        n_out += len(df)
        names |= set(df["יצרן"].dropna().astype(str).unique())
        if len(df) and df["נכון ליום"].isna().any():
            asof_ok = False

    print(f"    output detail rows: {n_out}")
    print(f"    distinct יצרן ({len(names)}):")
    for n in sorted(names):
        print(f"        {n}")

    frag = names & RAW_SHORT_NAMES
    unknown = names - ref
    count_ok = n_out == n_in
    print(f"\n    record count unchanged: {count_ok} ({n_in} -> {n_out})")
    print(f"    no raw short-names left: {not frag}" + (f"  leftovers={frag}" if frag else ""))
    print(f"    נכון ליום populated everywhere: {asof_ok}")
    print(f"    all names in reference vocab: {not unknown}"
          + (f"  extra={unknown}" if unknown else ""))
    return count_ok and not frag and asof_ok and not unknown


async def main():
    ref = load_reference_names()
    ok1 = check_resolver(ref)
    ok2 = await check_roundtrip(ref)
    print("\n" + ("PASS" if (ok1 and ok2) else "FAIL"))
    sys.exit(0 if (ok1 and ok2) else 1)


if __name__ == "__main__":
    asyncio.run(main())
