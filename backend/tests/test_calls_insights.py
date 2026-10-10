"""Nifra Insights: due-time parsing, reminders (15 min + brief), proposals, the products board,
the theme cache fingerprint and the analyst-number guard. Pure — no DB, no Claude."""
import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace

from app.api.calls import set_schedule
from app.services.agent.tools_calls import promises
from app.services.calls import insights_board as B
from app.services.calls import reminders as R
from app.services.calls.due_time import next_workday, parse_time, propose
from app.services.calls.events_consumer import clean_tasks


def _call(tasks=None, **kw):
    base = dict(id=uuid.uuid4(), title="שיחה", summary="", category="pension", source="phone_android", direction="out",
                duration_s=60, started_at=datetime(2026, 10, 8, 9), created_at=datetime(2026, 10, 8, 9),
                id_number="22944995", phone_number="0501234567", segments=[], status="done",
                insights={"customer": {"name": "חיים עזר", "matched": True}, "sentiment": "neutral",
                          "products_mentioned": ["פנסיה"], "topics": ["העברת פנסיה"], "companies_mentioned": ["הראל", "רשות המסים"],
                          "objections": [], "customer_needs": [],
                          "action_items": tasks if tasks is not None else [
                              {"text": "פגישה לסגירת הבחירה", "owner": "agent", "due": "יום שני, בסביבות 13:30", "due_date": "2026-10-12"},
                              {"text": "לבדוק נתוני הראל", "owner": "agent", "due": "יום ראשון", "due_date": "2026-10-11"},
                              {"text": "לעדכן את הלקוח", "owner": "agent", "due": "", "due_date": ""},
                              {"text": "לשלוח מייל", "owner": "customer", "due": "", "due_date": ""}]})
    base.update(kw)
    return SimpleNamespace(**base)


SUNDAY_0830 = datetime(2026, 10, 11, 5, 30, tzinfo=timezone.utc)     # 08:30 Israel (UTC+3)


def test_parse_time_exact_vs_suggestion():
    assert parse_time("יום שני, בסביבות 13:30") == ("13:30", True)
    assert parse_time("בשעה 3") == ("15:00", True)                # a work call's "3" is the afternoon
    assert parse_time("מחר אחרי 11") == ("11:00", False)           # loose → suggestion only
    assert parse_time("בבוקר") == ("09:00", False)
    assert parse_time("עד 15.10") == ("", False)                   # a date, not 15:10
    assert parse_time("שלושה ימים") == ("", False) and parse_time(None) == ("", False)


def test_workdays_skip_friday_saturday():
    assert next_workday(date(2026, 10, 8)) == date(2026, 10, 11)   # Thursday → Sunday
    p = propose({"due": ""}, date(2026, 10, 8), date(2026, 10, 9))
    assert p["date"] == "2026-10-11" and p["time"] == "10:00" and "לא נקבע" in p["reason"]


def test_fire_at_is_dst_safe():
    assert R.fire_at("2026-10-12", "13:30") == datetime(2026, 10, 12, 10, 15, tzinfo=timezone.utc)   # IDT +3
    assert R.fire_at("2026-10-26", "13:30") == datetime(2026, 10, 26, 11, 15, tzinfo=timezone.utc)   # IST +2 after 25/10


def test_brief_and_timed_from_real_shape():
    c = _call()
    out = R.build([c], now=SUNDAY_0830, agent_name="קיקו חביב")
    b = out["brief"]
    assert [t["text"] for t in b["due_today"]] == ["לבדוק נתוני הראל"]
    assert [t["text"] for t in b["undated"]] == ["לעדכן את הלקוח"]           # customer's own task never in the agent's brief
    assert b["sentences_he"][0] == "בוקר טוב קיקו." and b["key"] == "brief:2026-10-11"
    assert [t["key"] for t in out["timed"]] == [f"task:{c.id}:0:2026-10-12T13:30"]   # Sunday's task has no time → no timed alert
    assert out["timed"][0]["fire_at"] == "2026-10-12T10:15:00Z" and out["timed"][0]["speak_he"].startswith("בעוד רבע שעה")
    assert [p["text"] for p in out["proposals"]] == ["לעדכן את הלקוח"]


def test_brief_counts_equal_open_promises():
    rows = [_call(), _call(id_number="304675309")]
    out = R.build(rows, now=SUNDAY_0830)
    b = out["brief"]
    future = [t for t in promises(rows, "agent", date(2026, 10, 11)) if t["due_date"] and t["due_date"] > "2026-10-11"]
    assert out["open"] == len(promises(rows, "agent", date(2026, 10, 11)))
    assert len(b["due_today"]) + len(b["overdue"]) + len(b["undated"]) + len(future) == out["open"]


def test_confirmed_schedule_beats_heard_date_and_fires():
    c = _call()
    c.insights = set_schedule(c.insights, 2, "2026-10-11", "09:00")
    out = R.build([c], now=SUNDAY_0830)
    assert not out["brief"]["undated"] and not out["proposals"]
    t = next(t for t in out["timed"] if t["task_index"] == 2)
    assert t["key"] == f"task:{c.id}:2:2026-10-11T09:00" and t["fire_at"] == "2026-10-11T05:45:00Z"
    c.insights = set_schedule(c.insights, 2, "", "")                 # cleared → undated again
    assert [p["task_index"] for p in R.build([c], now=SUNDAY_0830)["proposals"]] == [2]


def test_clean_tasks_keeps_new_fields_and_drops_junk():
    t = clean_tasks([{"text": "x", "owner": "agent", "due_time": "9:05", "sched_date": "2026-10-12", "sched_time": "25:00",
                      "done": True, "done_at": "2026-10-10T08:00:00Z"},
                     {"text": "y", "sched_date": "not a date", "due_time": "בבוקר"}])
    assert t[0]["due_time"] == "09:05" and t[0]["sched_date"] == "2026-10-12" and t[0]["sched_time"] == ""
    assert t[0]["done_at"] and "sched_date" not in t[1] and t[1]["due_time"] == ""


def test_board_products_first_and_insurers_only():
    yoav = _call(id_number="304675309", category="study_fund",
                 insights={**_call().insights, "products_mentioned": ["קרן השתלמות"], "topics": ["תיקון 190"],
                           "customer": {"name": "יואב מרדכי"}})
    rows = [_call(), yoav]
    raw = B.build(rows, None, None, today=date(2026, 10, 11))           # no themes yet → raw product names
    assert [(p["theme"], p["calls"]) for p in raw["products"]] == [("פנסיה", 1), ("קרן השתלמות", 1)]
    pension = raw["products"][0]
    assert pension["insurers"] == ["הראל"] and pension["others"] == ["רשות המסים"]   # tax authority is not an insurer
    assert pension["customers"][0]["name"] == "חיים עזר" and pension["open"] == 3
    themed = B.build(rows, [{"name": "פנסיה", "members": ["פנסיה", "העברת פנסיה"]}], ["x"], today=date(2026, 10, 11))
    assert [(p["theme"], p["calls"]) for p in themed["products"]] == [("פנסיה", 1), ("קרן השתלמות", 1)]
    assert {p["theme"] for p in themed["products"]} == {"פנסיה", "קרן השתלמות"}   # unthemed call → its category label
    assert themed["stats"]["calls"] == 2 and themed["stats"]["customers"] == 2 and themed["narrative"] == ["x"]


def test_personal_calls_never_reach_the_board():
    # visible() filters in SQL; the pure builders must not resurrect hidden data from tasks either
    out = R.build([], now=SUNDAY_0830)
    assert out["open"] == 0 and out["brief"]["sentences_he"][-1].startswith("אין משימות")


def test_fingerprint_ignores_task_ticks():
    c = _call()
    fp = B.fingerprint([c])
    c.insights = {**c.insights, "action_items": [{**a, "done": True} for a in c.insights["action_items"]]}
    assert B.fingerprint([c]) == fp
    c.insights = {**c.insights, "products_mentioned": ["ביטוח מנהלים"]}
    assert B.fingerprint([c]) != fp


def test_analyst_may_not_do_math():
    facts = {"stats": {"calls": 16, "top_theme": {"pct": 25}}}
    lines = ["פנסיה מובילה עם 25% מהשיחות", "יש 31 משימות פתוחות", "כדאי לתאם פגישות השבוע"]
    assert B.guard_narrative(lines, facts) == ["פנסיה מובילה עם 25% מהשיחות", "כדאי לתאם פגישות השבוע"]


def test_counts_in_words_are_dropped_too():
    facts = {"stats": {"agent_open": 60}}
    assert B.guard_narrative(["שישים משימות פתוחות", "יש 60 משימות פתוחות"], facts) == ["יש 60 משימות פתוחות"]


def test_brief_is_light_when_only_undated():
    from zoneinfo import ZoneInfo
    s = R.brief_sentences(datetime(2026, 10, 10, 19, tzinfo=ZoneInfo("Asia/Jerusalem")), "קיקו", [], [],
                          [{"text": "x", "customer": None, "due_time": None, "overdue_days": 0}] * 20)
    assert s[0] == "ערב טוב קיקו." and s[1] == "להיום אין משהו קבוע." and s[2].startswith("20 דברים שהבטחת ללקוחות")


def test_themes_only_use_given_strings():
    out = B.clean_themes([{"name": "פנסיה", "members": ["פנסיה", "המצאה"]}, {"name": "שוב", "members": ["פנסיה"]},
                          {"name": 'ביטוח חיים ואכ"ע', "members": ["ביטוח חיים"]}], {"פנסיה", "ביטוח חיים"})
    assert out == [{"name": "פנסיה", "members": ["פנסיה"]}, {"name": 'ביטוח חיים ואכ"ע', "members": ["ביטוח חיים"]}]
