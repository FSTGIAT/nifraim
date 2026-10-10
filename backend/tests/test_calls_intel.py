"""Calls intelligence: categories, promises, due-date calendar, output cleaning, data-map pages."""
import uuid
from datetime import date, datetime
from types import SimpleNamespace

from app.services.agent.tools_calls import promises
from app.services.calls.categories import CATEGORIES, key_for, label
from app.services.calls.events_consumer import as_list, clean_tasks
from app.services.calls.summarize import _untag, when_line


def _call(**kw):
    base = dict(id=uuid.uuid4(), title="שיחה", summary="", category="claim", source="phone_android", direction="in",
                duration_s=60, started_at=datetime(2026, 9, 29, 10), created_at=datetime(2026, 9, 29, 10),
                id_number="36148096", phone_number="0543903020", segments=[], status="done",
                insights={"customer": {"name": "שרית סימון", "matched": True}, "tldr": "תביעה",
                          "action_items": [
                              {"text": "לשלוח טופס", "owner": "agent", "due": "עד רביעי", "due_date": "2026-09-30", "done": False},
                              {"text": "לשלוח קבלות", "owner": "customer", "due_date": "2026-10-02", "done": False},
                              {"text": "להגיש", "owner": "agent", "due_date": "", "done": False},
                              {"text": "בוצע", "owner": "agent", "due_date": "2026-09-30", "done": True}]})
    base.update(kw)
    return SimpleNamespace(**base)


def test_category_lookup_hebrew_and_key():
    assert key_for("fees") == "fees" and key_for("דמי ניהול") == "fees" and key_for("ניוד") == "transfer"
    assert key_for("משהו אחר לגמרי") is None and label(None) == CATEGORIES["other"]


def test_promises_overdue_first_and_owner_filter():
    p = promises([_call()], "agent", today=date(2026, 10, 5))
    assert [x["text"] for x in p] == ["לשלוח טופס", "להגיש"]          # done + customer tasks excluded
    assert p[0]["overdue_days"] == 5 and p[1]["overdue_days"] == 0
    assert [x["text"] for x in promises([_call()], "customer", today=date(2026, 10, 5))] == ["לשלוח קבלות"]


def test_calendar_is_a_lookup_not_arithmetic():
    line = when_line(date(2026, 9, 29))                                 # a Tuesday
    assert "יום שלישי 2026-09-29" in line and "יום רביעי (מחר)=2026-09-30" in line
    assert "יום חמישי=2026-10-01" in line


def test_clean_tasks_drops_bad_dates():
    t = clean_tasks([{"text": "x", "owner": "agent", "due_date": "יום חמישי"}, {"text": " "}])
    assert t == [{"text": "x", "owner": "agent", "due": "", "due_date": "", "due_time": "", "done": False}]


def test_untag_and_escaped_newlines():
    out = _untag({"followup_body": "שלום שרית,\\n\\nתודה.</followup_body>", "topics": ["<title>תביעה"]})
    assert out == {"followup_body": "שלום שרית,\n\nתודה.", "topics": ["תביעה"]}


def test_calls_pages_render():
    from app.services import data_map
    ctx = SimpleNamespace(calls=[_call()], user=None)
    page = data_map.page_calls(ctx)
    assert "[תביעה](calls/claim.md)" in page and "שרית סימון: לשלוח טופס" in page and "עבר המועד ב-" in page
    assert "שרית סימון" in data_map.page_calls_category(ctx, "claim")
    sec = "\n".join(data_map.calls_section(ctx, "36148096"))
    assert "## שיחות (1)" in sec and "פתוח (סוכן): לשלוח טופס" in sec


def test_passages_one_speaker_turn_each():
    from app.services.calls.embeddings import passages
    seg = [{"start": 0, "end": 2, "speaker": "S1", "text": "שלום שולמית, מדבר קיקו מהסוכנות, יש לך דקה לדבר?"},
           {"start": 2, "end": 4, "speaker": "S2", "text": "כן, היי קיקו, מה קורה איתך היום?"},
           {"start": 4, "end": 9, "speaker": "S1", "text": "ראיתי שדמי הניהול בקרן הפנסיה שלך עלו החודש לשתיים נקודה אחת אחוז"}]
    c = _call(segments=seg, insights={"speaker_roles": {"S1": "agent", "S2": "customer"}, "tldr": "דמי ניהול"})
    ps = passages(c)
    said = [p for p in ps if p["kind"] == "said"]
    assert [p["role"] for p in said] == ["agent", "customer", "agent"]      # never two speakers in one passage
    assert said[2]["start"] == 4 and ps[-1]["kind"] == "summary"


def test_list_fields_written_as_one_string_become_lists():
    assert as_list("<item>קצבה לא נכנסה</item>\n<item>להפעיל מחדש</item>") == ["קצבה לא נכנסה", "להפעיל מחדש"]
    assert as_list("שורה א\n- שורה ב") == ["שורה א", "שורה ב"]
    assert as_list(["א", " ", None, "ב"]) == ["א", "ב"] and as_list(None) == [] and as_list({"x": 1}) == []
