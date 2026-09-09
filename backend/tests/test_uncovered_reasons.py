"""Why a company contributes ₪0 to expected commission — four causes, not two.

    source backend/venv/bin/activate && python backend/tests/test_uncovered_reasons.py

QA 2026-09-09 item 7 said the exclusion messages were wrong for all three
companies they named. Measured against kikohib's live production book, two were
TRUE and one was FALSE — but the UI could not tell them apart, because the
backend counted only `no_rate` / `no_base` and the frontend picked between two
sentences with `u.no_rate >= u.no_base`.

Each cause implies a completely different action:

  מגדל   224 rows  no_company       → the agent has NO agreement for מגדל.
                                      Old text: "אין שיעור בהסכם" — reads as
                                      "the agreement is missing a rate", so the
                                      agent goes looking at an agreement that
                                      does not exist.
  הפניקס 314 rows  risk_no_premium  → rows hold ₪51.2M of צבירה, but a risk
                                      product is priced off PREMIUM and the file
                                      has none. Old text: "אין צבירה או פרמיה
                                      בקובץ" — plainly false about the צבירה.
  הראל  1240 rows  no_base          → true: the ר.ת. vault reports leave both
                                      money columns empty on all 1,672 rows.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.production import _uncovered_bucket, UNCOVERED_BUCKETS  # noqa: E402

failures = []


def check(name, got, want):
    if got == want:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}\n         got  {got!r}\n         want {want!r}")
        failures.append(name)


print("\n[1] the three live cases from QA #7")
# מגדל — zero rate rows for the insurer; select_rate signals it with route "none".
check("מגדל: no agreement at all → no_company",
      _uncovered_bucket(rate=0.0, route="none", is_accum=False,
                        premium=150.0, accum=0.0, expected=0.0), "no_company")
# הפניקס — ₪51.2M accumulation, risk product, no premium in the file.
check("הפניקס: risk product with צבירה but no premium → risk_no_premium",
      _uncovered_bucket(rate=0.05, route="stem:default", is_accum=False,
                        premium=0.0, accum=162_000.0, expected=0.0), "risk_no_premium")
# הראל — vault catalogue rows: both money columns empty.
check("הראל: no premium AND no accumulation → no_base",
      _uncovered_bucket(rate=0.05, route="stem:default", is_accum=False,
                        premium=0.0, accum=0.0, expected=0.0), "no_base")

print("\n[2] an agreement that exists but doesn't cover this product")
check("rate 0 with a matched company → no_rate",
      _uncovered_bucket(rate=0.0, route="exact:default", is_accum=True,
                        premium=0.0, accum=500_000.0, expected=0.0), "no_rate")

print("\n[3] records that DO contribute are never bucketed")
check("premium-based contributor",
      _uncovered_bucket(rate=0.05, route="exact:product", is_accum=False,
                        premium=1_000.0, accum=0.0, expected=50.0), None)
check("accumulation-based contributor",
      _uncovered_bucket(rate=0.0024, route="exact:default", is_accum=True,
                        premium=0.0, accum=1_000_000.0, expected=200.0), None)
check("a risk product WITH premium and also accumulation still contributes",
      _uncovered_bucket(rate=0.05, route="exact:product", is_accum=False,
                        premium=1_000.0, accum=90_000.0, expected=50.0), None)

print("\n[4] edge: a positive rate that still computes to zero")
# Accumulation basis, rate > 0, but the accumulation is 0 → nothing to price.
check("accum basis with zero accumulation → no_base",
      _uncovered_bucket(rate=0.0024, route="exact:default", is_accum=True,
                        premium=0.0, accum=0.0, expected=0.0), "no_base")

print("\n[5] every bucket the function can return is declared")
returned = set()
for args in [
    (0.0, "none", False, 1.0, 0.0, 0.0),
    (0.0, "exact:default", False, 1.0, 0.0, 0.0),
    (0.05, "exact:default", False, 0.0, 1.0, 0.0),
    (0.05, "exact:default", False, 0.0, 0.0, 0.0),
]:
    returned.add(_uncovered_bucket(*args))
check("no undeclared bucket leaks to the UI", returned - set(UNCOVERED_BUCKETS), set())
check("all four are reachable", returned, set(UNCOVERED_BUCKETS))

print()
if failures:
    print(f"FAILED ({len(failures)}): {failures}")
    sys.exit(1)
print("all checks passed")
