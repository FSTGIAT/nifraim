"""When did the agent say they'd get back? Time-of-day out of a task's free-text `due`.

Only an exact clock time ("בסביבות 13:30", "ב-9:15", "בשעה 11") becomes a reminder by
itself. Loose words ("אחרי 11", "בבוקר", "אחה״צ") are only ever a SUGGESTION the agent
confirms with one tap — never a reminder we invented. Used by services/calls/reminders.py.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

_CLOCK = re.compile(r"(?<![\d.:/])([01]?\d|2[0-3]):([0-5]\d)(?![\d.:/])")   # ":" only — "15.10" is a date
_AT_HOUR = re.compile(r"בשעה\s*(\d{1,2})(?![\d:./])")
_NEAR_HOUR = re.compile(r"(?:אחרי|לפני|סביב|בסביבות|ב-?)\s*(\d{1,2})(?![\d:./])")
_WORDS = (  # most specific first
    (re.compile(r"אחה[\"״'׳]?צ|אחרי הצהריים|אחר הצהריים"), "15:00"),
    (re.compile(r"בצהריים|צהריים"), "12:00"),
    (re.compile(r"בבוקר|בוקר"), "09:00"),
    (re.compile(r"בערב|ערב"), "18:00"),
)
WORKDAYS = {6, 0, 1, 2, 3}   # Python weekday: Sun=6, Mon..Thu=0..3 (Israeli work week)
DEFAULT_TIME = "10:00"


def _work_hour(h: int) -> int:
    """'ב-3' said in a work call is 15:00, not 03:00."""
    return h + 12 if 1 <= h <= 7 else h


def parse_time(due: str | None) -> tuple[str, bool]:
    """→ ("HH:MM", exact) or ("", False)."""
    s = (due or "").strip()
    if not s:
        return "", False
    m = _CLOCK.search(s)
    if m:
        return f"{_work_hour(int(m.group(1))):02d}:{m.group(2)}", True
    m = _AT_HOUR.search(s)
    if m and int(m.group(1)) <= 23:
        return f"{_work_hour(int(m.group(1))):02d}:00", True
    m = _NEAR_HOUR.search(s)
    if m and 1 <= int(m.group(1)) <= 23:
        return f"{_work_hour(int(m.group(1))):02d}:00", False
    for rx, t in _WORDS:
        if rx.search(s):
            return t, False
    return "", False


def next_workday(after: date) -> date:
    d = after + timedelta(days=1)
    while d.weekday() not in WORKDAYS:
        d += timedelta(days=1)
    return d


def propose(task: dict, call_day: date | None, today: date, urgency: str | None = None) -> dict:
    """A date/time Nifra suggests for an undated task. Pure; nothing is stored until the
    agent taps אישור (POST /api/calls/{id}/tasks/{i}/schedule)."""
    t, _exact = parse_time(task.get("due"))
    base = max(today, call_day or today)
    d = next_workday(base - timedelta(days=1)) if urgency == "high" and base.weekday() in WORKDAYS else next_workday(base)
    if (task.get("due") or "").strip():
        reason = f"נאמר בשיחה: «{task['due'].strip()}»"
    else:
        reason = "לא נקבע מועד בשיחה"
    return {"date": d.isoformat(), "time": t or DEFAULT_TIME, "reason": reason}
