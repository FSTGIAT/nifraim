"""Agreement-rate composition — QA 2026-10-02 items 4 / 4b.

    cd backend && venv/bin/python -m pytest -q tests/test_rate_bands_harel.py

• הפניקס prints עמלת ספר and שיעור תגמול per policy-year band; the final rate is
  their sum WITHIN a band, and a dated policy takes its own band.
• הראל prints only the תוספת; the agency's known ספר is added (11% life/risk,
  14% health) — never to savings, never over a היקף row, never twice.
"""
import sys
import uuid
from datetime import date
from pathlib import Path
from types import SimpleNamespace as R

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.rate_select import (  # noqa: E402
    _effective_rate, harel_hidden_book, policy_year, rate_for_product,
)

DOC = uuid.uuid4()


def _rows(company, product, spec):
    return [R(company_name=company, product=product, rate=r, rate_kind=k,
              rate_scope=sc, source_document_id=DOC) for r, k, sc in spec]


PHX_RISK = _rows("הפניקס חברה לביטוח בע\"מ", "מוצרי ריסק", [
    (0.15, "book", "שנה 1-5"), (0.15, "book", "שנה 6-15"), (0.15, "book", "שנה 16+"),
    (0.08, "reward", "משנה 1 ועד שנה 5 (כולל)"), (0.08, "reward", "שנה 6-15"),
    (0.04, "reward", "16 ומעלה"),
])
# commission_rate_summing.md's worked example: no תגמול in years 1-5.
PHX_TRANSPLANT = _rows("הפניקס", "השתלות", [
    (0.15, "book", "שנה 1-5"), (0.15, "book", "שנה 6-15"), (0.05, "book", "שנה 16+"),
    (0.072, "reward", "שנה 6-15"), (0.072, "reward", "שנה 16+"),
])


def approx(a, b):
    return abs(a - b) < 1e-9


def test_band_pairing_sums_within_band():
    assert approx(_effective_rate(PHX_RISK, 1), 0.23)
    assert approx(_effective_rate(PHX_RISK, 9), 0.23)
    assert approx(_effective_rate(PHX_RISK, 20), 0.19)


def test_band_never_invents_a_reward():
    assert approx(_effective_rate(PHX_TRANSPLANT, 3), 0.15)
    assert approx(_effective_rate(PHX_TRANSPLANT, 10), 0.222)
    assert approx(_effective_rate(PHX_TRANSPLANT, 17), 0.122)


def test_policy_year():
    today = date(2026, 10, 2)
    assert policy_year("2026-01-01", today) == 1
    assert policy_year(date(2017, 10, 1), today) == 10
    assert policy_year(None, today) is None


def test_dated_policy_takes_its_band():
    old = date(date.today().year - 20, 1, 1)
    rate, _exp, _route = rate_for_product(PHX_RISK, "הפניקס חברה לביטוח בע\"מ",
                                          "מוצרי ריסק", "ריסק", 0, 100, old)
    assert approx(rate, 0.19)


HAREL = (
    _rows("הראל חברה לביטוח בע\"מ", "ניתוחים בחו\"ל (בריאות)", [(0.044, "reward", None)])
    + _rows("הראל חברה לביטוח", "משכנתא בטוחה - ריסק משכנתא", [(0.60, "single", None)])
    + _rows("הראל חברה לביטוח בע\"מ", "משכנתא בטוחה - ריסק משכנתא", [(0.05, "reward", None)])
    + _rows("הראל חברה לביטוח", "מור לשכירים (חיסכון)", [(0.0028, "single", None)])
)


def test_harel_health_adds_14():
    rate, *_ = rate_for_product(HAREL, "הראל חברה לביטוח בע\"מ", "ניתוחים בחו\"ל",
                                "בריאות", 0, 100)
    assert approx(rate, 0.044 + 0.14)


def test_harel_life_adds_11_despite_hekef_row():
    rate, *_ = rate_for_product(HAREL, "הראל חברה לביטוח בע\"מ", "משכנתא בטוחה - ריסק משכנתא",
                                "ביטוח חיים משכנתא", 0, 100)
    assert approx(rate, 0.05 + 0.11)


def test_harel_never_on_savings_or_full_rate():
    assert harel_hidden_book("הראל", "מור לשכירים (חיסכון)", None, HAREL[-1:]) == 0
    full = _rows("הראל", "בריאות", [(0.18, "single", None)])
    assert harel_hidden_book("הראל", "בריאות", "בריאות", full) == 0
    assert harel_hidden_book("הפניקס", "בריאות", "בריאות", HAREL[:1]) == 0


def test_harel_generic_policy_priced_from_same_kind_lines():
    # Real Harel production lines are generic ('הראל - בריאות') and name no
    # agreement line — priced from Harel's health lines + 14%, as an estimate.
    rate, _exp, route = rate_for_product(HAREL, "הראל חברה לביטוח בע\"מ", "הראל - בריאות",
                                         "ביטוח בריאות", 0, 100)
    assert approx(rate, 0.044 + 0.14) and route.endswith(":category")
    rate, _exp, route = rate_for_product(HAREL, "הראל חברה לביטוח בע\"מ", "הראל - חיים",
                                         "ביטוח חיים", 0, 100)
    assert approx(rate, 0.05 + 0.11) and route.endswith(":category")


def test_harel_pension_untouched():
    rate, *_ = rate_for_product(HAREL, "הראל חברה לביטוח בע\"מ", "הראל פנסיה",
                                "קרן פנסיה חדשה מקיפה", 0, 100)
    assert rate < 0.11


def test_harel_never_on_hekef_row():
    # The shelf showed 'תוספת 60% + ספר הראל 11% = 71%' on one-time היקף rows.
    hekef = _rows("הראל חברה לביטוח", "מגן 1 (ריסק)", [(0.60, "single", None)])
    assert harel_hidden_book("הראל חברה לביטוח", "מגן 1 (ריסק)", None, hekef) == 0


MIGDAL = _rows("מגדל חברה לביטוח בע\"מ", "אובדן כושר עבודה", [
    (0.08, "single", "משנה א'-טו'"), (0.04, "single", "משנה טז' ואילך"),
])


def test_hebrew_numeral_bands():
    # Migdal prints its bands in Hebrew numerals (א'-טו' = 1-15, טז' = 16+).
    assert approx(_effective_rate(MIGDAL, 3), 0.08)
    assert approx(_effective_rate(MIGDAL, 15), 0.08)
    assert approx(_effective_rate(MIGDAL, 16), 0.04)


def test_odd_sign_dates():
    from datetime import datetime
    today = date(2026, 10, 2)
    assert policy_year("2030-01-01", today) == 1          # future date → first year
    assert policy_year(datetime(2010, 10, 3, 12), today) == 16
    assert policy_year("not a date", today) is None       # → median across bands
    assert policy_year("2011-10-02T00:00:00", today) == 16


def test_savings_never_firm_from_risk_cover_line():
    from app.services.rate_select import _RISK_COVER_RE
    rows = _rows("מגדל", "מגדל אובדן כושר עבודה מנהלים ועצמאים", [
        (0.06, "single", "משנה א'-טו'"), (0.03, "single", "משנה טז' ואילך")])
    rows += _rows("מגדל", "מגדל קשת — עמלה מחיסכון מצטבר", [(0.0032, "single", None)])
    old = date(date.today().year - 30, 1, 1)
    _rate, _exp, route = rate_for_product(rows, "מגדל", "מגדל - מנהלים", "ביטוח מנהלים", 137000, 0, old)
    assert not route.endswith(":product")   # never a FIRM rate off a risk-cover line
    # 'השתל' (transplants) must not swallow 'השתלמות' (study fund).
    assert not _RISK_COVER_RE.search("מוצרי גמל והשתלמות")
    assert _RISK_COVER_RE.search("השתלות וטיפולים מיוחדים")


# ── Pension: only a pension line prices a pension fund (QA 2026-10-03) ──
from app.services.rate_select import is_pension_record, is_pension_rate_line  # noqa: E402

PHX = (_rows("הפניקס פנסיה וגמל בע\"מ", "מוצרי גמל והשתלמות", [(0.0027, "single", None)])
       + _rows("הפניקס חברה לביטוח בע\"מ", "מוצרי ריסק", [(0.15, "book", None), (0.08, "reward", None)]))
MENORA = (_rows("מנורה מבטחים", "פנסיה מקיפה, פנסית חובה ופנסיה משלימה", [(0.004, "single", None)])
          + _rows("מנורה מבטחים", "קרן השתלמות (פנסיוני שוטף)", [(0.0024, "single", None)]))


def test_pension_detection():
    assert is_pension_record("מבטחים החדשה", "קרן פנסיה חדשה מקיפה")
    assert is_pension_record("מבטחים יותר", None)            # נפרעים line, no type
    assert is_pension_record("מקפת אישית", None)
    assert not is_pension_record("מנורה מבטחים - ביטוח חיים משכנתא", "ביטוח חיים משכנתא")
    assert not is_pension_record("מנורה מבטחים השתלמות", "קרן השתלמות")
    assert not is_pension_record("מגדל מטריה לפנסיה", None)
    assert is_pension_rate_line(MENORA[0])
    assert not is_pension_rate_line(MENORA[1])                # "פנסיוני" = gemel arm
    assert not is_pension_rate_line(_rows("מגדל", "מגדל מטריה לפנסיה", [(0.06, "single", None)])[0])


def test_pension_without_pension_line_has_no_rate():
    rate, exp, route = rate_for_product(PHX, "הפניקס פנסיה וגמל בע\"מ", "הפניקס פנסיה מקיפה",
                                        "קרן פנסיה חדשה מקיפה", 0, 500)
    assert rate == 0 and exp is None and route.endswith(":no_pension_line")


def test_pension_with_pension_line_uses_it():
    rate, *_ = rate_for_product(MENORA, "מנורה מבטחים", "מבטחים החדשה", "קרן פנסיה חדשה מקיפה", 0, 0)
    assert approx(rate, 0.004)
    rate, *_ = rate_for_product(MENORA, "מנורה מבטחים", "מבטחים יותר", None, 0, 0)
    assert approx(rate, 0.004)                                 # not dropped by the insurance floor
