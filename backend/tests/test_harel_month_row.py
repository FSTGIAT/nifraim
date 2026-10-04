"""Harel ריכוז-תשלומים: drill the REQUESTED month's row, never the top row.

Row texts mirror the live grid (QA doc 2026-09-29): a dated, still-open payment
run on top, then month rows, then the חודשים קודמים roll-up.
"""
from datetime import date

from app.services.portal_automation.companies._harel_report import pick_month_row

GRID = [
    {"nth": 0, "row": "10/09/2026 1,808 1,762 5,796 1,686"},
    {"nth": 1, "row": "08/2026 1,861 1,653 5,942 1,702"},
    {"nth": 2, "row": "07/2026 1,744 1,663 5,948 1,684"},
    {"nth": 3, "row": "חודשים קודמים 25,978 6,357 2,232 113,718 26,691"},
]


def test_after_cutoff_picks_previous_month():
    cell, month, fallback = pick_month_row(GRID, date(2026, 9, 29))
    assert (cell["nth"], month, fallback) == (1, "08/2026", False)


def test_before_cutoff_picks_two_back():
    cell, month, fallback = pick_month_row(GRID, date(2026, 9, 14))
    assert (cell["nth"], month, fallback) == (2, "07/2026", False)


def test_target_missing_falls_back_to_newest_month_flagged():
    cell, month, fallback = pick_month_row(GRID, date(2026, 12, 25))
    assert (cell["nth"], month, fallback) == (1, "08/2026", True)


def test_dated_and_rollup_rows_never_picked():
    only_noise = [GRID[0], GRID[3]]
    assert pick_month_row(only_noise, date(2026, 9, 29)) == (None, None, False)
