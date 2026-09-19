"""Unified-export regression: `סיכום` must agree with the sheets it ships with.

    source backend/venv/bin/activate && python backend/tests/test_unified_export_summary.py

No DB, no network — the selection and grouping helpers are pure functions over
FileUpload-shaped objects and a dataframe.

Guards the four defects QA 2026-09-09 found in `נפרעים מאוחד` / `פרודוקציה
מאוחדת`, each of which failed SILENTLY and produced a plausible-looking file:

  1. `סיכום` was built per-FileUpload while `מאוחד` held the merged records, so
     the same workbook reported 11 companies on one sheet and 4 on another.
  2. `סה״כ` added the merged total to each company again — live 4299 = 2678+1621.
  3. Stale per-company leftovers from an earlier run were reported as the
     current month (four May/June files inside a July merge).
  4. A 24-hour "harvest window" dropped one of two Harel account files whenever
     the two logins ran more than a day apart (70 kept, 139 lost).
"""

import sys
from datetime import datetime, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from app.api.production import (  # noqa: E402
    _select_unified_uploads,
    _summary_from_rows,
    _excel_sheet_name,
)
from app.utils.company_norm import company_stem  # noqa: E402


class U:
    """Minimal FileUpload stand-in — the selector only reads these four."""

    def __init__(self, filename, company_source, uploaded_at, period_month=None):
        self.filename = filename
        self.company_source = company_source
        self.uploaded_at = uploaded_at
        self.period_month = period_month

    def __repr__(self):
        return f"U({self.filename!r})"


def _dt(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M")


failures = []


def check(name, got, want):
    if got == want:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}\n         got  {got!r}\n         want {want!r}")
        failures.append(name)


# ---------------------------------------------------------------------------
print("\n[1] stale per-company leftovers are excluded (QA #5)")
# Reproduces kikohib exactly: a July merge uploaded 08-30, with four May/June
# per-company files still sitting beside it from earlier runs.
merge = U("נפרעים מאוחד יולי 26.xlsx", "מאוחד", _dt("2026-08-30 14:38"), date(2026, 7, 1))
stale = [
    U("נפרעים מאוחד יוני 26.xlsx", "מאוחד", _dt("2026-07-30 15:24"), date(2026, 6, 1)),
    U("מור נפרעים 05-2026.xlsx", "מור", _dt("2026-07-20 16:18"), date(2026, 5, 1)),
    U("מנורה.zip", "מנורה", _dt("2026-07-09 08:43"), date(2026, 6, 1)),
    U("הראל 113049345.xls", "הראל", _dt("2026-07-09 08:42"), date(2026, 5, 1)),
    U("מגדל נפרעים מאי 2026.xlsx", "מגדל", _dt("2026-07-08 04:39"), date(2026, 5, 1)),
]
check("only the newest merge survives", _select_unified_uploads([merge] + stale), [merge])

# ---------------------------------------------------------------------------
print("\n[2] a standalone run AFTER the merge is kept (not a leftover)")
fresh = U("מור נפרעים 08-2026.xlsx", "מור", _dt("2026-08-31 09:00"), date(2026, 8, 1))
picked = _select_unified_uploads([merge, fresh] + stale)
check("merge + post-merge run", sorted(u.filename for u in picked),
      sorted([merge.filename, fresh.filename]))

# ---------------------------------------------------------------------------
print("\n[3] BOTH Harel account files survive (QA #4 — the 24h window bug)")
# The two Harel agency logins ran 28h apart, which the old harvest window read
# as "different harvests" and silently dropped the older one's 139 rows.
h1 = U("הראל - 113049345.xls", "הראל", _dt("2026-09-01 08:42"), date(2026, 8, 1))
h2 = U("הראל - 113061826.xls", "הראל", _dt("2026-09-02 12:50"), date(2026, 8, 1))
picked = _select_unified_uploads([merge, h1, h2])
check("both accounts kept", sorted(u.filename for u in picked),
      sorted([merge.filename, h1.filename, h2.filename]))

# ---------------------------------------------------------------------------
print("\n[4] period detection is NOT trusted for selection (documented Harel case)")
# Live: two fresh Harel files had period_month detected as 2026-02/03 (portal
# נפרעים filenames carry no month, so detection landed on record-data months)
# while a stale merge held 2026-05. A latest-period filter served ONLY the
# stale merge. Selecting on upload time must keep the fresh files.
old_merge = U("נפרעים מאוחד מאי 26.xlsx", "מאוחד", _dt("2026-05-20 10:00"), date(2026, 5, 1))
f1 = U("הראל א.xls", "הראל", _dt("2026-06-01 09:00"), date(2026, 2, 1))
f2 = U("הראל ב.xls", "הראל", _dt("2026-06-01 09:05"), date(2026, 3, 1))
picked = _select_unified_uploads([old_merge, f1, f2])
check("fresh files win over a stale merge", sorted(u.filename for u in picked),
      sorted([old_merge.filename, f1.filename, f2.filename]))

# ---------------------------------------------------------------------------
print("\n[5] no merge yet → per-company files stand alone, deduped by filename")
a_old = U("מור נפרעים.xlsx", "מור", _dt("2026-06-01 09:00"), date(2026, 5, 1))
a_new = U("מור נפרעים.xlsx", "מור", _dt("2026-07-01 09:00"), date(2026, 6, 1))
b = U("מגדל נפרעים.xlsx", "מגדל", _dt("2026-07-01 09:00"), date(2026, 6, 1))
picked = _select_unified_uploads([a_new, b, a_old])
check("newest wins per filename", sorted(u.filename for u in picked),
      sorted([a_new.filename, b.filename]))
check("the newest 'מור' is the July one", [u for u in picked if u.company_source == "מור"],
      [a_new])

# ---------------------------------------------------------------------------
print("\n[6] סה״כ is the sum of the groups, never the merge counted twice (QA #4)")
df = pd.DataFrame([
    # Two Menora LEGAL entities must roll up to one brand row.
    {"פרמיה": 100.0, "עמלה ששולמה": 10.0, "_stem": company_stem('מנורה מבטחים ביטוח בע"מ'),
     "_period": "2026-07", "_source": "merge.xlsx"},
    {"פרמיה": 50.0, "עמלה ששולמה": 5.0, "_stem": company_stem('מנורה מבטחים פנסיה וגמל בע"מ'),
     "_period": "2026-07", "_source": "merge.xlsx"},
    {"פרמיה": 20.0, "עמלה ששולמה": 2.0, "_stem": company_stem('מגדל חברה לביטוח בע"מ'),
     "_period": "2026-07", "_source": "merge.xlsx"},
])
configured = {
    "מנורה": {"label": "מנורה", "production": True, "commission": True},
    "מגדל": {"label": "מגדל", "production": True, "commission": True},
    "אלטשולר": {"label": "אלטשולר", "production": False, "commission": True},
    "מור": {"label": "מור", "production": False, "commission": True},
}
summary, sheets = _summary_from_rows(
    df, {"סך פרמיה": "פרמיה", "סך עמלה ששולמה": "עמלה ששולמה"},
    configured, kind="commission",
)
by_company = {r["חברה"]: r for r in summary}
check("Menora's two legal entities roll into one row", by_company["מנורה"]["מספר רשומות"], 2)
check("Menora premium summed across entities", by_company["מנורה"]["סך פרמיה"], 150.0)
check("סה״כ rows == sum of groups", by_company["סה״כ"]["מספר רשומות"], 3)
check("סה״כ premium == sum of groups", by_company["סה״כ"]["סך פרמיה"], 170.0)
check("one sheet per company with data", sorted(n for n, _ in sheets), ["מגדל", "מנורה"])
check("helper columns stripped from sheets",
      [c for c, _ in sheets for c in dict(sheets)[c].columns if c.startswith("_")], [])

# ---------------------------------------------------------------------------
print("\n[7] every configured company appears, at zero, with an accurate reason")
check("all configured companies present",
      sorted(r["חברה"] for r in summary if r["חברה"] != "סה״כ"),
      sorted(configured))
check("a real failure says so", by_company["אלטשולר"]["קובץ מקור"],
      "לא התקבלו נתונים בהרצה האחרונה")
# מור is a gemel house: its portal has no production report, so a zero on the
# PRODUCTION sheet is not a failure and must not read like one.
prod_summary, _ = _summary_from_rows(
    df, {"סך פרמיה": "פרמיה"}, configured, kind="production",
)
prod_by = {r["חברה"]: r for r in prod_summary}
check("no production report ≠ a failed run", prod_by["מור"]["קובץ מקור"],
      "הפורטל אינו מספק דוח פרודוקציה")
check("a company that DOES publish production still reports a failure",
      prod_by["מנורה"]["קובץ מקור"] if prod_by["מנורה"]["מספר רשומות"] == 0
      else "(has data)", "(has data)")

# The last run's REAL per-company error beats the generic "no data" — those
# reasons already existed, concatenated into batch.error_message[:2000] where
# nobody could read them per company.
reasons = {"אלטשולר": "הפורמט לא זוהה (unknown) — לא ייכלל בקבצים המאוחדים",
           "מור": "לא הצלחנו להוריד"}
summary_r, _ = _summary_from_rows(
    df, {"סך פרמיה": "פרמיה"}, configured, kind="commission", reasons=reasons)
by_r = {r["חברה"]: r for r in summary_r}
check("real failure reason surfaces", by_r["אלטשולר"]["קובץ מקור"],
      "הפורמט לא זוהה (unknown) — לא ייכלל בקבצים המאוחדים")
# ...but "the portal has no such report" still wins: it is not a failure, and
# a stale run error must not make it look like one.
prod_r, _ = _summary_from_rows(
    df, {"סך פרמיה": "פרמיה"}, configured, kind="production", reasons=reasons)
check("no-such-report beats a run error", {r["חברה"]: r["קובץ מקור"] for r in prod_r}["מור"],
      "הפורטל אינו מספק דוח פרודוקציה")
check("a company with data is never given a reason",
      by_r["מנורה"]["קובץ מקור"], "merge.xlsx")

# ---------------------------------------------------------------------------
print("\n[8] excel sheet names stay legal and unique")
taken = {"סיכום"}
check("illegal chars stripped", _excel_sheet_name("a/b:c*d", taken), "a b c d")
check("collision suffixed", _excel_sheet_name("הראל", taken), "הראל")
check("second collision suffixed", _excel_sheet_name("הראל", taken), "הראל (2)")
check("over-long truncated to 31", len(_excel_sheet_name("x" * 60, taken)), 31)

print()
# ---------------------------------------------------------------------------
print("\n[6] the PRODUCTION aggregation path de-stales too (QA 2026-09-18)")
# The live shape that broke התפלגות לפי חברה / לקוחות לפי פרמיה: three uploads
# flagged is_production at once. `/breakdown`, `/analytics` and `/clients` read
# "every is_production row" and so summed April + June + September together —
# 5,080 rows / 890 clients / 21 companies / ₪383.4M, against the correct
# 2,238 / 408 / 5 / ₪53.3M that the KPI tiles on the SAME screen showed.
# Premium came out 3.25x too high, which QA reported as "הפרמיה ברמה שנתית".
prod_apr = U("פרודוקציה אפריל.xlsx", 'הפניקס אקסלנס פנסיה וגמל בע"מ', _dt("2026-05-18 18:27"))
prod_jun = U("פרודוקציה מאוחד יוני 26.xlsx", "מאוחד", _dt("2026-07-02 06:35"))
prod_sep = U("פרודוקציה מאוחד ספטמבר 26.xlsx", "מאוחד", _dt("2026-09-15 18:51"))
check("only the newest production merge survives",
      _select_unified_uploads([prod_apr, prod_jun, prod_sep]), [prod_sep])

# And the record-aggregation helper must actually route through the selector —
# it is the single seam every per-record production endpoint shares.
import inspect as _inspect  # noqa: E402
from app.api.production import _get_production_upload_ids  # noqa: E402
_src = _inspect.getsource(_get_production_upload_ids)
check("_get_production_upload_ids applies the selector",
      "_select_unified_uploads(" in _src, True)


if failures:
    print(f"FAILED ({len(failures)}): {failures}")
    sys.exit(1)
print("all checks passed")
