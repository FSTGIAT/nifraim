"""Product wording must collapse to ONE key per product.

    source backend/venv/bin/activate && python backend/tests/test_product_taxonomy.py

Measured on kikohib's live production book: 8 distinct `product_type` strings
describe 4 products, because each portal writes its own wording and Harel writes
the REPORT's filename. Grouping on the raw column reports חיים four times and
makes QA #9/#11's ביטוח-vs-פיננסים split impossible.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.product_taxonomy import canonical_product_type, classify_product  # noqa: E402

failures = []


def check(name, got, want):
    if got == want:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}\n         got  {got!r}\n         want {want!r}")
        failures.append(name)


print("\n[1] the four spellings of חיים in the live book collapse to one key")
# 261 + 147 + 89 + 64 = 561 rows that used to report as four separate products.
for raw in ["חיים", "ביטוח חיים", "ר.ת.-מורחב חיים ביטוחים", "ר.ת.-מורחב חיים פוליסות"]:
    check(f"{raw!r} → 'חיים'", canonical_product_type(raw), "חיים")

print("\n[2] and the three spellings of בריאות")
for raw in ["ביטוח בריאות", "ר.ת.-מורחב בריאות ביטוחים", "ר.ת.-מורחב בריאות פוליסות"]:
    check(f"{raw!r} → 'בריאות'", canonical_product_type(raw), "בריאות")

print("\n[3] financial products")
check("'מור השתלמות'", canonical_product_type("מור השתלמות"), "קרן השתלמות")
check("'אלפא מור תגמולים'", canonical_product_type("אלפא מור תגמולים"), "קופת גמל")
check("'פנסיה'", canonical_product_type("פנסיה"), "קרן פנסיה")
# Specific-before-generic: 'גמל להשקעה' must not be eaten by the 'גמל' token.
check("'גמל להשקעה' beats the 'גמל' token",
      canonical_product_type("גמל להשקעה"), "גמל להשקעה")
# Same trap: 'ביטוח מנהלים' must not be stripped to 'מנהלים' and mis-keyed.
check("'ביטוח מנהלים' stays itself",
      canonical_product_type("ביטוח מנהלים"), "ביטוח מנהלים")

print("\n[4] unknown wording is PRESERVED, never bucketed into 'אחר'")
# Hachshara's fund family and Migdal's segment name are real products this app
# has no opinion about. Hiding them defeats the breakdown the agent asked for.
check("'בסט' survives", canonical_product_type("בסט"), "בסט")
check("'פיננסים וזמן פרישה' survives",
      canonical_product_type("פיננסים וזמן פרישה"), "פיננסים וזמן פרישה")
check("'סיכונים' survives", canonical_product_type("סיכונים"), "סיכונים")

print("\n[5] empty input never crashes and never invents a product")
for raw in [None, "", "   "]:
    check(f"{raw!r} → ''", canonical_product_type(raw), "")

print("\n[6] normalisation is idempotent (a canonical key re-keys to itself)")
for raw in ["חיים", "בריאות", "קרן השתלמות", "גמל להשקעה", "מגוון", "בסט"]:
    check(f"{raw!r} stable", canonical_product_type(canonical_product_type(raw)),
          canonical_product_type(raw))

print("\n[7] classify_product splits ביטוח / פיננסים")
check("a health policy with premium is insurance",
      classify_product({"product_type": "ביטוח בריאות", "total_premium": 500.0,
                        "accumulation": 0.0}), ("insurance", "בריאות"))
check("a gemel row is financial",
      classify_product({"product_type": "מור השתלמות", "total_premium": 0.0,
                        "accumulation": 1_000_000.0}), ("financial", "קרן השתלמות"))
check("falls back to fund_type when product_type is empty",
      classify_product({"product_type": None, "fund_type": "גמל להשקעה",
                        "total_premium": 0.0, "accumulation": 50_000.0}),
      ("financial", "גמל להשקעה"))

print("\n[8] an accumulation-bearing life policy is פיננסים (decided 2026-09-09)")
# 324 live rows / ₪54,536,228 — Phoenix MU + Harel מגוון. Deliberate: they hold
# savings. Moving them to ביטוח would put a balance on a premium-measured panel.
check("life policy WITH accumulation and no premium → financial",
      classify_product({"product_type": "חיים", "total_premium": 0.0,
                        "accumulation": 162_000.0}), ("financial", "חיים"))
check("the same policy WITH premium stays insurance",
      classify_product({"product_type": "חיים", "total_premium": 500.0,
                        "accumulation": 0.0}), ("insurance", "חיים"))

print()
if failures:
    print(f"FAILED ({len(failures)}): {failures}")
    sys.exit(1)
print("all checks passed")
