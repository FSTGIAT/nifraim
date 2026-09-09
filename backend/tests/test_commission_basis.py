"""Which commission column is EX-VAT — decided by measurement, not a table.

    source backend/venv/bin/activate && python backend/tests/test_commission_basis.py

QA 2026-09-09 item 6 asked for ONE commission column. The two the pipeline
carries mean different things per insurer, measured live:

    מור      18,394.45 / 18,394.45   identical  → summing both would double
    מנורה         0.00 /  7,758.32   one populated
    הכשרה    40,160.53 / 47,223.69   both real, ratio exactly 1.18 = VAT

and the parsers disagree on naming: Harel savings maps `עמלה לפני מע"מ` to
`commission_paid`, the opposite of Hachshara. So no blanket COALESCE is safe.

Decision (user): report commission EXCLUDING VAT. This detects the VAT pair
from the rows themselves rather than hardcoding insurers, and refuses to guess
when the ratio is not a VAT relationship.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.commission_basis import detect_vat_basis, ex_vat_commission  # noqa: E402

failures = []


def check(name, got, want):
    if got == want:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}\n         got  {got!r}\n         want {want!r}")
        failures.append(name)


def rows(pairs):
    return [{"commission_paid": p, "commission_before_fee": b} for p, b in pairs]


print("\n[1] הכשרה — the real 1.18 VAT pair from the live file")
# Actual rows from KIKO/עמלות נפרעים הכשרה.xlsx.
hachshara = rows([(139.10, 117.88), (376.45, 319.02), (394.56, 334.37),
                  (69.63, 59.00), (598.21, 506.95)])
b = detect_vat_basis(hachshara)
check("ex-VAT column identified", b["field"], "commission_before_fee")
check("verified", b["verified"], True)
check("totals use the ex-VAT figure",
      round(sum(ex_vat_commission(r, b) for r in hachshara), 2), 1337.22)

print("\n[2] 17% VAT (pre-2025 rows) is recognised too")
b17 = detect_vat_basis(rows([(117.0, 100.0), (234.0, 200.0), (351.0, 300.0)]))
check("17% detected", (b17["field"], b17["verified"]),
      ("commission_before_fee", True))

print("\n[3] מור — identical columns must not double-count")
mor = rows([(18394.45, 18394.45), (100.0, 100.0), (250.5, 250.5)])
bm = detect_vat_basis(mor)
check("picks one column", bm["field"], "commission_paid")
check("sum is the figure, not twice it",
      round(sum(ex_vat_commission(r, bm) for r in mor), 2), 18744.95)

print("\n[4] מנורה — only one column populated, the row must still count")
menora = [{"commission_paid": 7758.32, "commission_before_fee": 0.0},
          {"commission_paid": 100.0, "commission_before_fee": None}]
bn = detect_vat_basis(menora)
check("no VAT evidence → unverified", bn["verified"], False)
check("rows are not dropped",
      round(sum(ex_vat_commission(r, bn) for r in menora), 2), 7858.32)

print("\n[5] inverted mapping (Harel savings) still resolves to ex-VAT")
# `commission_paid` holds the PRE-VAT figure here — ratio is 1/1.18.
inv = rows([(100.0, 118.0), (200.0, 236.0), (300.0, 354.0)])
bi = detect_vat_basis(inv)
check("picks the smaller, pre-VAT column", bi["field"], "commission_paid")
check("verified", bi["verified"], True)

print("\n[6] a NON-VAT ratio is refused, not guessed")
bx = detect_vat_basis(rows([(300.0, 100.0), (600.0, 200.0), (900.0, 300.0)]))
check("3x is not VAT → unverified", bx["verified"], False)
check("still returns a usable number", bx["field"], "commission_paid")

print("\n[7] too few samples to decide")
b2 = detect_vat_basis(rows([(118.0, 100.0), (236.0, 200.0)]))
check("2 rows is not evidence", b2["verified"], False)

print("\n[8] a row with neither column falls back without crashing")
bz = detect_vat_basis(rows([(118.0, 100.0), (236.0, 200.0), (354.0, 300.0)]))
check("empty row → 0", ex_vat_commission({}, bz), 0.0)
check("falls through to actual_amount",
      ex_vat_commission({"actual_amount": 42.0}, bz), 42.0)

print()
if failures:
    print(f"FAILED ({len(failures)}): {failures}")
    sys.exit(1)
print("all checks passed")
