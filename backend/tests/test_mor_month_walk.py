"""Mor נפרעים month walk — against a simulated חישוב תגמול grid.

    cd backend && venv/bin/python tests/test_mor_month_walk.py

QA 2026-10-03: kikohib's merged נפרעים carried Mor's 06/2026 report while Mor
had July. The walk read the result count ONCE right after חפש (a grid that had
not refreshed yet still showed the previous month's "no records"), and an
exception silently stepped to an older month. Either is enough to serve June.
"""
import asyncio
import logging
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.portal_automation.companies.mor import pick_latest_month  # noqa: E402

LOG = logging.getLogger("test_mor")


class FakeGrid:
    """Mor's grid: `data` = {(m, y): rows}. After חפש the grid keeps showing the
    PREVIOUS result for `lag` reads before the new month appears."""

    def __init__(self, data, lag=0, fail_clicks=0):
        self.data, self.lag, self.fail_clicks = data, lag, fail_clicks
        self.typed = None
        self.shown = 0          # what the grid displays right now
        self.pending = None     # (rows, reads_left) while loading
        self.searched = []

    # page.*
    async def wait_for_timeout(self, _ms): pass
    async def wait_for_load_state(self, *_a, **_k): pass

    @property
    def keyboard(self):
        class _K:
            async def press(self, _key): pass
        return _K()

    async def result_count(self):
        if self.pending:
            rows, left = self.pending
            if left > 0:
                self.pending = (rows, left - 1)
                return self.shown            # stale: still the previous grid
            self.shown, self.pending = rows, None
        return self.shown


class FakeInput:
    def __init__(self, grid): self.grid = grid
    async def click(self, **_k):
        if self.grid.fail_clicks:
            self.grid.fail_clicks -= 1
            raise TimeoutError("kendo picker not ready")
    async def type(self, digits, **_k): self.grid.typed = (int(digits[:2]), int(digits[2:]))


class FakeSearch:
    def __init__(self, grid): self.grid = grid
    async def click(self, **_k):
        g = self.grid
        g.searched.append(g.typed)
        g.pending = (g.data.get(g.typed, 0), g.lag)


def walk(grid, today):
    return asyncio.run(pick_latest_month(grid, FakeInput(grid), FakeSearch(grid),
                                         grid.result_count, today, LOG))


def old_walk(grid, today):
    """The pre-fix algorithm: one read after חפש, exception → older month."""
    async def run():
        inp, btn = FakeInput(grid), FakeSearch(grid)
        for back in range(10):
            m, y = today.month - back, today.year
            while m <= 0:
                m += 12; y -= 1
            try:
                await inp.click(); await inp.type(f"{m:02d}{y}"); await btn.click()
                cnt = await grid.result_count()
            except Exception:
                continue
            if cnt > 0:
                return cnt, m, y
        return 0, today.month, today.year
    return asyncio.run(run())


SEP_15 = date(2026, 9, 15)
MOR = {(7, 2026): 467, (6, 2026): 455, (5, 2026): 490}


def test_reproduces_the_june_bug_and_fixes_it():
    # The grid needs one extra read to show July's rows.
    old = old_walk(FakeGrid(MOR, lag=1), SEP_15)
    assert old[1:] != (7, 2026), old                                  # the QA bug: July missed
    assert walk(FakeGrid(MOR, lag=1), SEP_15) == (467, 7, 2026)      # fixed


def test_slow_grid_within_deadline():
    assert walk(FakeGrid(MOR, lag=2), SEP_15) == (467, 7, 2026)


def test_click_error_retries_same_month():
    # 09 and 08 are empty; the July click fails once — must retry July, not
    # step back to June.
    g_fail = FakeGrid(MOR)
    seq = []

    class FlakyInput(FakeInput):
        async def click(self, **_k):
            seq.append(self.grid.typed)
            if len(seq) == 3:                # the third click is July's
                raise TimeoutError("kendo picker not ready")

    out = asyncio.run(pick_latest_month(g_fail, FlakyInput(g_fail), FakeSearch(g_fail),
                                        g_fail.result_count, SEP_15, LOG))
    assert out == (467, 7, 2026), out


def test_no_data_anywhere():
    assert walk(FakeGrid({}), SEP_15)[0] == 0


def test_year_wrap():
    assert walk(FakeGrid({(12, 2026): 300}), date(2027, 1, 20)) == (300, 12, 2026)


def test_newest_month_wins_when_present():
    assert walk(FakeGrid({**MOR, (8, 2026): 470}, lag=1), SEP_15) == (470, 8, 2026)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t(); print(f"[PASS] {t.__name__}")
        except AssertionError as e:
            failed += 1; print(f"[FAIL] {t.__name__} {e}")
    print("ALL PASS" if not failed else f"{failed} FAILED")
    sys.exit(1 if failed else 0)
