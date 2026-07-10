"""Hachshara emailed-production parser regression test.

Runs against the real 2026-04 bundle in `tests/fixtures/`. No DB, no network.

    source backend/venv/bin/activate && python backend/tests/test_hachshara_prod_parser.py

The two checks that matter most, because both fail *silently* and produce
plausible-looking data:

  1. `_reverse_visual_hebrew` must leave numeric runs alone. A whole-field
     `[::-1]` (what menora_legacy/phoenix_mu do for their pure-Hebrew names)
     turns the product 'בסט פרט 02/16' into 'בסט פרט 61/20'.
  2. SP accumulation is WHOLE SHEKELS; RM fund amounts are AGOROT. Getting the
     scaling wrong is a 100x error in the production totals.
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.hachshara_prod import (  # noqa: E402
    _read_members,
    _reverse_visual_hebrew,
    is_hachshara_prod_zip,
    parse_hachshara_prod_zip,
)

FIXTURE = Path(__file__).parent / "fixtures" / "Ild_prod_1_09344_30042026.zip"

# The fixture is the real 2026-04 bundle with the six clients' IDs, names, addresses
# and occupations replaced by fakes — byte layout, offsets and every financial field
# untouched. Real client PII must never enter git history.
EXPECTED_IDS = {"51111118", "52222226", "83333334", "84444442", "85555550", "86666668"}
ANCHOR_ID = "51111118"
ANCHOR_ACCUMULATION = 492358.0      # whole shekels, NOT 49235800 agorot
ANCHOR_FUNDS_TOTAL = 492315.82      # sum of RM fund blocks, in shekels
ANCHOR_PRODUCT = "בסט פרט 02/16"
ACC_DRIFT_MAX = 0.005               # valuation-date drift, not a scaling bug


def _check(label, got, expected):
    ok = got == expected
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}: {got!r}" + ("" if ok else f" != {expected!r}"))
    return ok


def main() -> int:
    if not FIXTURE.exists():
        print(f"SKIP — fixture missing: {FIXTURE}")
        return 0

    content = FIXTURE.read_bytes()
    failures = 0

    print("visual-Hebrew reversal (numeric runs must survive):")
    # The regression that a whole-field reverse would produce is '61/20'.
    failures += not _check("product with date", _reverse_visual_hebrew("02/16 טרפ טסב"), ANCHOR_PRODUCT)
    failures += not _check("pure-Hebrew surname", _reverse_visual_hebrew("יחרזמ"), "מזרחי")
    failures += not _check("fund name", _reverse_visual_hebrew("תוינמ רומ"), "מור מניות")
    failures += not _check("empty field", _reverse_visual_hebrew("      "), "")

    print("\ndetection:")
    failures += not _check("is_hachshara_prod_zip", is_hachshara_prod_zip(content), True)
    failures += not _check("rejects non-zip", is_hachshara_prod_zip(b"not a zip"), False)

    print("\nall-blank RP/RB members yield no lines and never raise:")
    members = _read_members(content)
    failures += not _check("RP lines", len(members.get("RP", [])), 0)
    failures += not _check("RB lines", len(members.get("RB", [])), 0)

    result = parse_hachshara_prod_zip(content, FIXTURE.name)
    records = {r["id_number"]: r for r in result["records"]}

    print("\nbundle shape:")
    failures += not _check("format", result["format"], "production")
    failures += not _check("company_source", result["company_source"], "הכשרה")
    failures += not _check("period_month (from filename DDMMYYYY)", result["period_month"], date(2026, 4, 1))
    failures += not _check("record count", len(result["records"]), 6)
    # Joined by id_number, never by record index — SP/SB/RM happen to be aligned.
    failures += not _check("ids (deduped by join key)", set(records), EXPECTED_IDS)

    print("\nanchor client:")
    rec = records[ANCHOR_ID]
    failures += not _check("last_name", rec["last_name"], "כהן")
    failures += not _check("first_name", rec["first_name"], "דוד")
    failures += not _check("product", rec["product"], ANCHOR_PRODUCT)
    failures += not _check("accumulation (whole shekels)", rec["accumulation"], ANCHOR_ACCUMULATION)
    failures += not _check("sign_date", rec["sign_date"], date(2019, 5, 1))
    failures += not _check("track (dominant fund)", rec["track"], "מור מניות")
    failures += not _check("agent_number", rec["agent_number"], "09344")
    failures += not _check("processing_date", rec["processing_date"], "2026-04-30")

    print("\nfields absent from the source file — must stay None, never synthesised:")
    failures += not _check("total_premium", rec["total_premium"], None)
    failures += not _check("fund_policy_number", rec["fund_policy_number"], None)

    print("\nshekels-vs-agorot cross-check (RM funds sum ≈ SP accumulation):")
    drift = abs(ANCHOR_FUNDS_TOTAL - rec["accumulation"]) / rec["accumulation"]
    ok = drift < ACC_DRIFT_MAX
    print(f"  [{'PASS' if ok else 'FAIL'}] drift {drift * 100:.3f}% < {ACC_DRIFT_MAX * 100}%")
    failures += not ok

    # Every client, not just the anchor: a shifted offset would blow this up.
    for rid, r in sorted(records.items()):
        if r["accumulation"] is None or r["accumulation"] <= 0:
            print(f"  [FAIL] {rid}: accumulation missing")
            failures += 1

    print(f"\n{'ALL PASS' if not failures else str(failures) + ' FAILURE(S)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
