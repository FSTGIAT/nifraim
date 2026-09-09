"""The merged-file company key must INVERT itself across a fold.

    source backend/venv/bin/activate && python backend/tests/test_merged_company_key.py

The standalone fold rebuilds the merged workbook by dropping the just-run
company's stale slice and appending its fresh rows. That comparison is between
a FRESH parser record (short brand: 'מנורה', 'מיטב דש') and a MERGED-FILE
record (full legal entity: 'מנורה מבטחים פנסיה וגמל בע"מ'). If the key doesn't
map both to the same value, the stale slice survives and the company is written
TWICE — silently, with plausible-looking totals.

Two ways to get this wrong, and this file guards both:

  * too loose (`normalize_company`, the old fold key) — misses for מנורה,
    מגדל-savings, אלטשולר, מיטב, ילין, אנליסט, כלל-בריאות → duplication.
  * too coarse (`company_stem`) — collapses 'הראל חברה לביטוח בע"מ' with
    'הראל פנסיה וגמל בע"מ', so folding a Harel GEMEL run would DELETE Harel's
    insurance rows. Coarse is right for display grouping, wrong as a fold key.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.portal_automation.aggregate import merged_company_key  # noqa: E402

failures = []


def check(name, got, want):
    if got == want:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}\n         got  {got!r}\n         want {want!r}")
        failures.append(name)


def fresh(company, product_type="", accum=0.0, premium=0.0, fund_type=""):
    """A record as a per-company parser emits it — short brand name."""
    return {"receiving_company": company, "product_type": product_type,
            "accumulation": accum, "total_premium": premium, "fund_type": fund_type}


# ---------------------------------------------------------------------------
print("\n[1] a fresh run and its own merged rows resolve to ONE key (idempotence)")
# Every company the old normalize_company-based fold silently duplicated.
cases = [
    ("מנורה", "ביטוח חיים", 0.0, 500.0),
    ("מנורה", "גמל", 1_000.0, 0.0),
    ("מגדל", "השתלמות", 1_000.0, 0.0),
    ("אלטשולר", "גמל", 1_000.0, 0.0),
    ("מיטב דש", "גמל", 1_000.0, 0.0),
    ("ילין לפידות", "גמל", 1_000.0, 0.0),
    ("אנליסט", "גמל", 1_000.0, 0.0),
    ("כלל בריאות", "ביטוח בריאות", 0.0, 500.0),
    ("הראל", "ביטוח חיים", 0.0, 500.0),
    ("הראל", "גמל", 1_000.0, 0.0),
    ("הפניקס", "ביטוח חיים", 0.0, 500.0),
    ("מור", "גמל", 1_000.0, 0.0),
    ("הכשרה", "גמל", 1_000.0, 0.0),
]
for company, ptype, accum, prem in cases:
    r = fresh(company, ptype, accum, prem)
    key = merged_company_key(r, commission=False)
    # The merged file stores that key as receiving_company; re-keying it must
    # return the SAME value or the fold can't recognise its own output.
    merged_row = dict(r, receiving_company=key)
    check(f"{company:12} / {ptype:14} → {key}",
          merged_company_key(merged_row, commission=False), key)

# ---------------------------------------------------------------------------
print("\n[2] the same holds on the נפרעים side")
for company, fund in [("מנורה", "גמל"), ("מיטב דש", "השתלמות"), ("אנליסט", "גמל"),
                      ("ילין לפידות", "גמל"), ("אלטשולר", "גמל"), ("מור", "גמל"),
                      ("הראל", ""), ("הפניקס", "")]:
    r = fresh(company, fund_type=fund, accum=1000.0)
    key = merged_company_key(r, commission=True)
    merged_row = dict(r, receiving_company=key)
    check(f"{company:12} / {fund or '(ביטוח)':10} → {key}",
          merged_company_key(merged_row, commission=True), key)

# ---------------------------------------------------------------------------
print("\n[3] distinct legal entities must NOT collapse (the over-merge trap)")
# Folding a fresh Harel gemel run must not delete Harel's insurance rows.
harel_life = merged_company_key(fresh("הראל", "ביטוח חיים", 0.0, 500.0), commission=False)
harel_gemel = merged_company_key(fresh("הראל", "גמל", 1_000.0, 0.0), commission=False)
check("Harel insurance ≠ Harel gemel", harel_life != harel_gemel, True)
mnr_ins = merged_company_key(fresh("מנורה", "ביטוח חיים", 0.0, 500.0), commission=False)
mnr_gml = merged_company_key(fresh("מנורה", "גמל", 1_000.0, 0.0), commission=False)
check("Menora insurance ≠ Menora gemel", mnr_ins != mnr_gml, True)

# ---------------------------------------------------------------------------
print("\n[4] the fold actually replaces one slice and keeps the rest")
merged_file = [
    dict(fresh(harel_life, "ביטוח חיים", 0.0, 500.0)),
    dict(fresh(harel_gemel, "גמל", 1_000.0, 0.0)),
    dict(fresh(mnr_ins, "ביטוח חיים", 0.0, 700.0)),
]
new_run = [fresh("הראל", "גמל", 2_000.0, 0.0)]          # a fresh Harel GEMEL run
fresh_keys = {merged_company_key(r, commission=False) for r in new_run}
rebuilt = [r for r in merged_file
           if merged_company_key(r, commission=False) not in fresh_keys] + new_run
keys = [merged_company_key(r, commission=False) for r in rebuilt]
check("no company written twice", len(keys), len(set(keys)))
check("Harel gemel replaced, not appended", keys.count(harel_gemel), 1)
check("Harel INSURANCE survived the gemel fold", harel_life in keys, True)
check("Menora untouched", mnr_ins in keys, True)
check("fresh row's amount is the one kept",
      [r["accumulation"] for r in rebuilt
       if merged_company_key(r, commission=False) == harel_gemel], [2_000.0])

# ---------------------------------------------------------------------------
print("\n[5] an unmapped insurer degrades, never vanishes")
k = merged_company_key(fresh("חברה חדשה כלשהי", "גמל", 1_000.0, 0.0), commission=False)
check("unmapped name is preserved", k, "חברה חדשה כלשהי")
check("blank company yields a blank key, not a crash",
      merged_company_key({"receiving_company": None}, commission=False), "")

print()
if failures:
    print(f"FAILED ({len(failures)}): {failures}")
    sys.exit(1)
print("all checks passed")
