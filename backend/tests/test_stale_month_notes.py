"""Batch note for a company that served an OLDER נפרעים month (QA 2026-10-03).

    cd backend && venv/bin/python tests/test_stale_month_notes.py
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.portal_automation.batch_runner import stale_month_notes  # noqa: E402

JUL, JUN, AUG = date(2026, 7, 1), date(2026, 6, 1), date(2026, 8, 1)
fails = 0


def check(name, got, want):
    global fails
    ok = got == want
    fails += not ok
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if ok else f"\n   got  {got!r}\n   want {want!r}"))


# kikohib's case: everyone July, Mor June → Mor is named.
notes = stale_month_notes([("הראל", JUL), ("מור", JUN), ("מנורה", JUL)], None)
check("mor june named", len(notes) == 1 and "מור 06/2026" in notes[0] and "07/2026" in notes[0], True)
check("on-time companies not named", "הראל" in notes[0] or "מנורה" in notes[0], False)
# All on the same month → no note.
check("all current → no note", stale_month_notes([("הראל", JUL), ("מור", JUL)], None), [])
# A cycle knows its period: everyone delivered June for a July cycle → all named.
n = stale_month_notes([("הראל", JUN), ("מור", JUN)], JUL)
check("cycle target wins", len(n) == 1 and "הראל 06/2026" in n[0] and "מור 06/2026" in n[0], True)
# A company AHEAD of the target is not stale.
check("ahead is fine", stale_month_notes([("הראל", AUG)], JUL), [])
check("empty input", stale_month_notes([], None), [])
# One company, two files of the same month → named once.
n = stale_month_notes([("מור", JUN), ("מור", JUN), ("הראל", JUL)], None)
check("deduped", n[0].count("מור"), 1)

print("ALL PASS" if not fails else f"{fails} FAILED")
sys.exit(1 if fails else 0)
