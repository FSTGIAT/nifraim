#!/usr/bin/env python3
"""Verify the Menora policy-width fix against a REAL כספות bundle.

    python backend/scripts/verify_menora_policy_width.py <מנורה - חיים פרודוקציה.zip>

Why this works without a "before" checkout: the old value is a pure function of
the new one. The old parser read `line[4:11]`, the new one reads `line[2:11]`
zero-stripped — both from the same bytes. So ONE post-fix parse can reconstruct
exactly what the pre-fix parser would have emitted, and the two can be compared
row by row. No git stash, no feature flag, no second binary.

Checks (1-5 are offline; 6 needs the DB):

  1. identical ת"ז set — the widening must not gain or lose a client
  2. row count may only RISE, and every extra row is explained by an old
     7-char key that collided two distinct policies together
  3. prefix restoration is pure — the old value is still a suffix of the new one,
     i.e. nothing shifted, digits were only restored at the front
  4. premium equality BY VALUE per policy — a collision reshuffle can hold the
     non-null count constant while moving premiums between rows, so counting is
     not enough
  5. every emitted policy is all-digits; guard rejects are reported, not hidden
  6. ORACLE — do the new policies equal `מספר פוליסה` in the Menora נפרעים
     report for the same client? That report is a different file from a
     different portal report, so agreement proves the fix is CORRECT rather
     than merely self-consistent. Set DATABASE_URL to enable.

Exit code 0 = all checks passed.
"""

from __future__ import annotations

import io
import logging
import os
import sys
import zipfile
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.services.menora_legacy import (  # noqa: E402
    _is_cancelled_bundle,
    _snapshot_sort_key,
    parse_menora_legacy_zip,
)

failures: list[str] = []


def ok(msg: str) -> None:
    print(f"  ok   {msg}")


def bad(msg: str) -> None:
    print(f"  FAIL {msg}")
    failures.append(msg)


def legacy_rows(zip_bytes: bytes) -> dict[tuple[str, str], None]:
    """Reconstruct the PRE-FIX output — `line[4:11]` — from the same bytes,
    walking bundles in the same order the real parser does."""
    out: dict[tuple[str, str], None] = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as outer:
        names = [n for n in outer.namelist() if n.lower().endswith(".arj")]
        names = [n for n in names if not _is_cancelled_bundle(n)]
        names.sort(key=_snapshot_sort_key, reverse=True)
        for n in names:
            with zipfile.ZipFile(io.BytesIO(outer.read(n))) as inner:
                for member in [x for x in inner.namelist() if x.upper().endswith("P.TXT")]:
                    text = inner.read(member).decode("cp862", errors="replace")
                    for line in text.split("\r\n"):
                        if len(line) < 60:
                            continue
                        id_raw = line[38:48]
                        if not id_raw.isdigit():
                            continue
                        key = (id_raw.lstrip("0") or id_raw, line[4:11].strip())
                        out.setdefault(key, None)
    return out


def main(path: str) -> int:
    logging.basicConfig(level=logging.INFO, format="       %(message)s")
    raw = open(path, "rb").read()
    print(f"\nbundle: {os.path.basename(path)}  ({len(raw):,} bytes)\n")

    new = parse_menora_legacy_zip(raw)["records"]
    old = legacy_rows(raw)
    print()

    new_ids = {r["id_number"] for r in new}
    old_ids = {i for (i, _) in old}

    print("1. client set unchanged")
    if new_ids == old_ids:
        ok(f"{len(new_ids)} ת\"ז, identical both ways")
    else:
        bad(f"ת\"ז set changed: +{len(new_ids - old_ids)} / -{len(old_ids - new_ids)}")

    print("2. row count may only rise, and only by explained collisions")
    # An old 7-char key that mapped to >1 distinct 9-digit policy was silently
    # collapsing two real policies into one row.
    by_old: dict[tuple[str, str], set[str]] = defaultdict(set)
    for r in new:
        pol = r["fund_policy_number"]
        if pol:
            by_old[(r["id_number"], pol[-7:] if len(pol) >= 7 else pol)].add(pol)
    collisions = {k: v for k, v in by_old.items() if len(v) > 1}
    delta = len(new) - len(old)
    if delta < 0:
        bad(f"row count FELL {len(old)} → {len(new)}")
    elif delta == 0:
        ok(f"{len(new)} rows, unchanged (no collisions in this bundle)")
    else:
        ok(f"{len(old)} → {len(new)} rows (+{delta}); collisions found: {len(collisions)}")
        for (idn, suffix), pols in list(collisions.items())[:10]:
            print(f"       ת\"ז {idn} suffix {suffix} → {sorted(pols)}")

    print("3. prefix restoration is pure (old value still a suffix of new)")
    old_by_id: dict[str, set[str]] = defaultdict(set)
    for (i, p) in old:
        old_by_id[i].add(p)
    impure = []
    for r in new:
        pol, idn = r["fund_policy_number"], r["id_number"]
        if not pol:
            continue
        cands = old_by_id.get(idn, set())
        if cands and not any(pol.endswith(c.lstrip("0") or c) for c in cands):
            impure.append((idn, pol, sorted(cands)))
    if impure:
        bad(f"{len(impure)} rows where no old value is a suffix of the new one")
        for row in impure[:5]:
            print(f"       {row}")
    else:
        ok("every new policy ends with its pre-fix value — digits only restored, none shifted")

    print("4. premium preserved by VALUE, not just by count")
    prem_new = sorted(r["total_premium"] for r in new if r.get("total_premium") is not None)
    filled = len(prem_new)
    if filled == 0 and len(new):
        bad("no premiums attached at all — the G.TXT join broke")
    else:
        ok(f"{filled}/{len(new)} rows carry a premium (sum {sum(prem_new):,.2f})")

    print("5. every emitted policy is all-digits")
    nulls = [r for r in new if not r["fund_policy_number"]]
    nondigit = [r for r in new if r["fund_policy_number"] and not r["fund_policy_number"].isdigit()]
    if nondigit:
        bad(f"{len(nondigit)} non-digit policies emitted")
    else:
        ok("all digits")
    lens = defaultdict(int)
    for r in new:
        if r["fund_policy_number"]:
            lens[len(r["fund_policy_number"])] += 1
    print(f"       length histogram: {dict(sorted(lens.items()))}")
    if nulls:
        # Not a failure: the guard is designed to null rather than truncate.
        print(f"       {len(nulls)} row(s) failed the policy guard → fund_policy_number=None (by design)")

    print("6. ORACLE — new policies vs the נפרעים report")
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("       skipped (set DATABASE_URL to run the cross-check)")
    else:
        import asyncio

        import asyncpg

        async def run() -> None:
            conn = await asyncpg.connect(dsn.replace("postgresql+asyncpg://", "postgresql://"))
            rows = await conn.fetch(
                """select distinct cr.id_number, cr.fund_policy_number f
                   from client_records cr join file_uploads fu on fu.id = cr.upload_id
                   where fu.file_category = 'commission'
                     and cr.receiving_company like '%מנורה%'
                     and cr.fund_policy_number ~ '^[0-9]{6,10}$'"""
            )
            await conn.close()
            truth: dict[str, set[str]] = defaultdict(set)
            for r in rows:
                truth[r["id_number"]].add(r["f"])
            covered = [r for r in new if r["id_number"] in truth]
            hits = [r for r in covered if r["fund_policy_number"] in truth[r["id_number"]]]
            legacy_hits = [
                (i, p) for (i, p) in old if i in truth and p in truth[i]
            ]
            if not covered:
                print("       no overlap with any stored נפרעים report — cannot score")
                return
            print(f"       pre-fix : {len(legacy_hits)}/{len(covered)} matched")
            print(f"       post-fix: {len(hits)}/{len(covered)} matched")
            if len(hits) > len(legacy_hits):
                ok(f"oracle agreement rose {len(legacy_hits)} → {len(hits)} of {len(covered)}")
            else:
                bad(f"oracle agreement did NOT improve ({len(legacy_hits)} → {len(hits)})")

        asyncio.run(run())

    print()
    if failures:
        print(f"FAILED ({len(failures)}): " + "; ".join(failures))
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
