"""הכשרה: the חודש עיבוד cycle rule, and the guard on what actually downloads.

    source backend/venv/bin/activate && python backend/tests/test_hachshara_month_cycle.py

Reported live 2026-09-14: the נפרעים export was never filtered by חודש עיבוד, so
it returned every client the agent has ever had instead of the ones still under
them that month. The file was well-formed, so it passed the 1 KB size gate, the
column-name signature, record_count and the runner — kikohib's הכשרה slice drifted
350 → 356 → 362 rows across runs while every run reported success.

Two pure functions have to be right for that not to recur:
  * `reporting_months` — which month should exist right now (the 21st rule)
  * `verify_processing_month` — did the file we got actually contain ONLY it
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from app.services.portal_automation.base import reporting_months  # noqa: E402
from app.services.portal_automation.companies.hachshara import (  # noqa: E402
    CYCLE_CUTOFF_DAY,
    verify_processing_month,
)

failures = []


def check(name, got, want):
    if got == want:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}\n         got  {got!r}\n         want {want!r}")
        failures.append(name)


def check_bad(name, result, must_mention=None):
    """The verifier must REJECT, and say something usable about why."""
    ok, reason = result
    if ok:
        print(f"  FAIL {name}\n         accepted a file it should have rejected")
        failures.append(name)
    elif must_mention and must_mention not in reason:
        print(f"  FAIL {name}\n         reason missing {must_mention!r}: {reason}")
        failures.append(name)
    else:
        print(f"  ok   {name}  ({reason[:60]}…)")


print("\n[1] the cycle rule — a month publishes on the 21st, and serves M-1")
# The reported case: on 14/09 the last cycle was 21/08, which served July.
check("14/09/2026 → 07/2026", reporting_months(date(2026, 9, 14), CYCLE_CUTOFF_DAY)[0], (2026, 7))
check("20/09/2026 → 07/2026", reporting_months(date(2026, 9, 20), CYCLE_CUTOFF_DAY)[0], (2026, 7))
# Boundary: the 21st itself rolls the cycle.
check("21/09/2026 → 08/2026", reporting_months(date(2026, 9, 21), CYCLE_CUTOFF_DAY)[0], (2026, 8))
check("25/09/2026 → 08/2026", reporting_months(date(2026, 9, 25), CYCLE_CUTOFF_DAY)[0], (2026, 8))
check("09/08/2026 → 06/2026", reporting_months(date(2026, 8, 9), CYCLE_CUTOFF_DAY)[0], (2026, 6))
# Year rollover in both directions.
check("14/01/2026 → 11/2025", reporting_months(date(2026, 1, 14), CYCLE_CUTOFF_DAY)[0], (2025, 11))
check("25/01/2026 → 12/2025", reporting_months(date(2026, 1, 25), CYCLE_CUTOFF_DAY)[0], (2025, 12))

print("\n[2] fallbacks only ever go BACKWARD")
# A month NEWER than the primary has not published yet. On 14/09 the dropdown
# offers 08/2026, and taking it downloads a report the 21/09 cycle has not built.
cands = reporting_months(date(2026, 9, 14), CYCLE_CUTOFF_DAY)
check("three candidates", len(cands), 3)
check("strictly descending", cands, [(2026, 7), (2026, 6), (2026, 5)])
check("08/2026 is never offered", (2026, 8) in cands, False)
check("rollover fallbacks", reporting_months(date(2026, 1, 14), CYCLE_CUTOFF_DAY),
      [(2025, 11), (2025, 10), (2025, 9)])
# Analyst's own 20th rule must still be reproducible from the shared helper.
check("cutoff_day=20 reproduces analyst", reporting_months(date(2026, 9, 20), 20)[0], (2026, 8))

print("\n[3] the verifier accepts a real single-month export")
# The live column carries a TRAILING SPACE and MM/YYYY strings.
real = pd.DataFrame({"תאריך עיבוד ": ["01/2026"] * 5, "ת.ז מבוטח ": list("abcde")})
check("real file, right month", verify_processing_month(real, 2026, 1), (True, ""))
check_bad("real file, WRONG month asked", verify_processing_month(real, 2026, 7), must_mention="07/2026")

print("\n[4] the verifier rejects what used to pass")
# The actual bug: no filter applied → many months in one file.
mixed = pd.DataFrame({"תאריך עיבוד ": ["07/2026", "06/2026", "07/2026", "11/2025"]})
check_bad("mixed months (the all-clients-ever export)", verify_processing_month(mixed, 2026, 7))
# Headers only — currently passes the 1 KB gate and ingests as a 0-row success.
check_bad("headers-only export", verify_processing_month(
    pd.DataFrame({"תאריך עיבוד ": []}), 2026, 7))
check_bad("all cells blank", verify_processing_month(
    pd.DataFrame({"תאריך עיבוד ": [None, "", float("nan")]}), 2026, 7))
check_bad("column missing entirely", verify_processing_month(
    pd.DataFrame({"ת.ז מבוטח ": ["1"]}), 2026, 7))

print("\n[5] cell formats the same report has been seen to use")
for label, frame in [
    ("MM/YYYY", ["07/2026"]),
    ("M/YYYY (no pad)", ["7/2026"]),
    ("MM-YYYY", ["07-2026"]),
    ("DD/MM/YYYY", ["15/07/2026"]),
    ("ISO date", ["2026-07-15"]),
    ("real datetime", [pd.Timestamp("2026-07-15")]),
]:
    check(label, verify_processing_month(pd.DataFrame({"תאריך עיבוד ": frame}), 2026, 7), (True, ""))

print("\n[6] the real downloaded file on disk, if present")
sample = Path("/mnt/c/Users/roygi/Desktop/KIKO/עמלות נפרעים הכשרה.xlsx")
if sample.exists():
    df = pd.read_excel(sample)
    check(f"{sample.name} is 01/2026", verify_processing_month(df, 2026, 1), (True, ""))
    check_bad(f"{sample.name} is not 07/2026", verify_processing_month(df, 2026, 7))
else:
    print(f"  skip  {sample} not mounted")

print()
if failures:
    print(f"FAILED ({len(failures)}): " + ", ".join(failures))
    sys.exit(1)
print("all checks passed")
