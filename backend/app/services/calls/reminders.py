"""Reminders from the agent's own promises in calls — the 15-minute heads-up and the morning brief.

Built on tools_calls.promises() (the same open-task list Nifra Agent and the office-agent
cards read), so the brief can never count differently from them. Channel-agnostic: the
browser speaks it today, the Android app reads the same payload next version. Spoken
sentences are written HERE so every channel says the same words.

A task fires only from a time the agent said exactly ("בסביבות 13:30") or confirmed with one
tap (sched_date/sched_time). Loose words ("אחרי 11") come back as a proposal, never a reminder.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.models.call_recording import CallRecording
from app.services.agent.tools_calls import promises
from app.services.calls.due_time import parse_time, propose

IL = ZoneInfo("Asia/Jerusalem")
LEAD = timedelta(minutes=15)
MAX_PROPOSALS = 3
WEEK_DAYS = 7          # the week brief: today + the next 7 days
DAY_HE = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]   # date.weekday(): Mon=0


def _first(name: str | None) -> str:
    return (name or "").strip().split(" ")[0]


def task_when(a: dict) -> tuple[str, str]:
    """(date, time) the reminder runs on: the agent's confirmation, else what was said exactly."""
    if a.get("sched_date"):
        return a["sched_date"], a.get("sched_time") or ""
    t = a.get("due_time") or ""
    if not t:
        t, exact = parse_time(a.get("due"))
        t = t if exact else ""
    return a.get("due_date") or "", t


def fire_at(day: str, hhmm: str) -> datetime:
    """UTC instant 15 min before HH:MM Israel time on that day (DST-safe: zoneinfo, never +03:00)."""
    h, m = (int(x) for x in hhmm.split(":"))
    return datetime.combine(date.fromisoformat(day), time(h, m), IL).astimezone(timezone.utc) - LEAD


def _greeting(now_il: datetime, name: str) -> str:
    g = "בוקר טוב" if now_il.hour < 12 else "צהריים טובים" if now_il.hour < 17 else "ערב טוב"
    return f"{g}{' ' + name if name else ''}."


def _say(p: dict) -> str:
    who = f" — {p['customer']}" if p.get("customer") else ""   # a dash = a short pause when spoken
    return f"{p['text']}{who}"


def build(rows: list[CallRecording], now: datetime | None = None, claimed: set[str] | None = None,
          agent_name: str | None = None) -> dict:
    """rows = the agent's visible, done calls. Pure — tests feed SimpleNamespace rows."""
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    now_il = now.astimezone(IL)
    today = now_il.date()
    claimed = claimed or set()
    by_id = {str(c.id): c for c in rows}
    open_tasks = promises(rows, "agent", today)

    timed, due_today, overdue, undated, proposals, upcoming = [], [], [], [], [], []
    week_end = (today + timedelta(days=WEEK_DAYS)).isoformat()
    for p in open_tasks:
        c = by_id[p["call_id"]]
        a = ((c.insights or {}).get("action_items") or [])[p["task_index"]]
        day, hhmm = task_when(a)
        item = {"call_id": p["call_id"], "task_index": p["task_index"], "text": p["text"],
                "customer": p["customer"], "due": p["due"], "due_date": day or None, "due_time": hhmm or None,
                "overdue_days": p["overdue_days"]}
        if not day:
            undated.append(item)
            continue
        if p["overdue_days"] > 0:
            overdue.append(item)
        elif day == today.isoformat():
            due_today.append(item)
        elif day <= week_end:
            upcoming.append(item)
        if hhmm and day >= today.isoformat() and day <= (today + timedelta(days=1)).isoformat():
            fa = fire_at(day, hhmm)
            key = f"task:{p['call_id']}:{p['task_index']}:{day}T{hhmm}"
            late = fa + LEAD < now
            timed.append({**item, "key": key, "fire_at": fa.isoformat().replace("+00:00", "Z"),
                          "late_today": late and day == today.isoformat(), "claimed": key in claimed,
                          "speak_he": (f"הגיע הזמן: {_say(item)}." if late else f"תזכורת, בעוד רבע שעה: {_say(item)}.")})

    for n, item in enumerate(undated[:MAX_PROPOSALS]):
        c = by_id[item["call_id"]]
        a = ((c.insights or {}).get("action_items") or [])[item["task_index"]]
        at = c.started_at or c.created_at
        call_day = at.replace(tzinfo=timezone.utc).astimezone(IL).date() if at else None
        pr = propose(a, call_day, today, (c.insights or {}).get("urgency"))
        if not parse_time(a.get("due"))[0]:   # default slots spread by half an hour, not three at 10:00
            pr["time"] = (datetime.combine(today, time(10, 0)) + timedelta(minutes=30 * n)).strftime("%H:%M")
        proposals.append({**item, **pr})

    due_today.sort(key=lambda x: x["due_time"] or "99")
    week = week_ahead(today, due_today, upcoming)
    brief_key = f"brief:{today.isoformat()}"
    return {
        "now": now.isoformat().replace("+00:00", "Z"), "tz": "Asia/Jerusalem", "today": today.isoformat(),
        "open": len(open_tasks),
        "timed": sorted(timed, key=lambda x: x["fire_at"]),
        "brief": {"key": brief_key, "claimed": brief_key in claimed,
                  "due_today": due_today, "overdue": overdue, "undated": undated,
                  "headline": headline(len(due_today), len(overdue), len(undated)),
                  "sentences_he": brief_sentences(now_il, _first(agent_name), due_today, overdue, undated, week)},
        "week": week,
        "proposals": proposals,
    }


def headline(n_today: int, n_over: int, n_undated: int) -> str:
    parts = []
    if n_today:
        parts.append(f"{n_today} משימות להיום" if n_today > 1 else "משימה אחת להיום")
    if n_over:
        parts.append(f"{n_over} באיחור")
    if n_undated:
        parts.append(f"{n_undated} בלי תאריך")
    return " · ".join(parts) or "אין משימות פתוחות מהשיחות"


def _n(n: int, one: str, many: str) -> str:
    return one if n == 1 else f"{n} {many}"


def day_label(d: date, today: date) -> str:
    if d == today:
        return "היום"
    if d == today + timedelta(days=1):
        return "מחר"
    return f"יום {DAY_HE[d.weekday()]}"


def week_ahead(today: date, due_today: list, upcoming: list) -> dict:
    """The coming week, day by day — what the agent promised, with a date, from today to +7."""
    days: dict[str, list] = {}
    for t in sorted(due_today + upcoming, key=lambda x: (x["due_date"], x["due_time"] or "99")):
        days.setdefault(t["due_date"], []).append(t)
    out = [{"date": d, "label": day_label(date.fromisoformat(d), today), "tasks": ts} for d, ts in days.items()]
    total = sum(len(d["tasks"]) for d in out)
    if not out:
        sentences = ["בשבוע הקרוב אין משימות עם תאריך."]
    else:
        sentences = ["בשבוע הקרוב יש לך משימה אחת:" if total == 1 else f"בשבוע הקרוב יש לך {total} משימות:"]
        for d in out:
            items = [f"{'בשעה ' + t['due_time'] + ', ' if t['due_time'] else ''}{_say(t)}" for t in d["tasks"][:3]]
            more = f", ועוד {len(d['tasks']) - 3}" if len(d["tasks"]) > 3 else ""
            sentences.append(f"{d['label']}: {'. '.join(items)}{more}.")
    return {"days": out, "total": total, "sentences_he": sentences}


def brief_sentences(now_il: datetime, name: str, due_today: list, overdue: list, undated: list,
                    week: dict | None = None) -> list[str]:
    """Short, natural Hebrew — the agent hears it once, cold, between two calls."""
    out = [_greeting(now_il, name)]
    if not (due_today or overdue or undated):
        return out + ["אין משימות פתוחות מהשיחות. יום טוב!"]
    if due_today:
        out.append("היום יש לך משימה אחת מהשיחות:" if len(due_today) == 1 else f"היום יש לך {len(due_today)} משימות מהשיחות:")
        for t in due_today[:3]:
            out.append(f"{'בשעה ' + t['due_time'] + ', ' if t['due_time'] else ''}{_say(t)}.")
    else:
        out.append("אין לך משימות להיום.")
    if overdue:
        old = max(overdue, key=lambda t: t["overdue_days"])
        late = "יש משימה אחת שהתאריך שלה כבר עבר" if len(overdue) == 1 else f"יש {len(overdue)} משימות שהתאריך שלהן כבר עבר"
        out.append(f"{late}. הכי דחופה: {_say(old)}.")
    if undated:
        out.append("יש לך משימה אחת שעוד לא קבעת לה תאריך. אפשר לקבוע אותה ב-Nifra Insights." if len(undated) == 1
                   else f"יש לך {len(undated)} משימות שעוד לא קבעת להן תאריך. אפשר לקבוע אותן ב-Nifra Insights.")
    # Sunday opens the Israeli work week — one line about the week ahead
    later = (week or {}).get("total", 0) - len(due_today)
    if now_il.weekday() == 6 and later > 0:
        out.append("בהמשך השבוע מחכה לך עוד משימה אחת." if later == 1 else f"בהמשך השבוע מחכות לך עוד {later} משימות.")
    return out
