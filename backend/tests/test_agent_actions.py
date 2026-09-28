"""Nifra Agent actions: proposals validate, and a meeting is a real iCalendar
REQUEST invite (customer + a copy to the agent). Nothing is sent here."""
import pytest

from app.services import agent_actions as aa


def test_meeting_invite_message():
    p = aa.normalize("meeting", {"to_email": "dana@gmail.com", "to_name": "דנה כהן", "title": "פגישת היכרות",
                                 "start": "2026-09-30T14:00", "duration_min": 45, "location": "טלפון"})
    msg = aa.build_message(p, "agent@gmail.com", "קיקו")
    assert msg["Cc"] == "agent@gmail.com" and "dana@gmail.com" in msg["To"]
    assert "30.9.2026" in msg["Subject"] and "14:00–14:45" in msg["Subject"]
    cal = next(part for part in msg.walk() if part.get_content_type() == "text/calendar")
    assert cal.get_param("method") == "REQUEST"
    ics = cal.get_content()
    # 14:00 Israel (IDT, UTC+3) → 11:00Z
    assert "DTSTART:20260930T110000Z" in ics and "DTEND:20260930T114500Z" in ics
    assert "ORGANIZER;CN=קיקו:mailto:agent@gmail.com" in ics
    assert "RSVP=TRUE:mailto:dana@gmail.com" in ics and "LOCATION:טלפון" in ics
    assert any(part.get_filename() == "invite.ics" for part in msg.walk())


def test_email_message():
    p = aa.normalize("email", {"to_email": "yossi@walla.co.il", "subject": "חידוש", "body": "הפוליסה חודשה"})
    msg = aa.build_message(p, "agent@gmail.com", "קיקו")
    assert msg["Subject"] == "חידוש" and "Cc" not in msg
    assert "הפוליסה חודשה" in msg.get_content()


@pytest.mark.parametrize("kind,data,err", [
    ("email", {"to_email": "not-an-email", "subject": "a", "body": "b"}, "bad_email"),
    ("email", {"to_email": "a@b.co", "subject": "", "body": "b"}, "missing_text"),
    ("meeting", {"to_email": "a@b.co", "title": "x", "start": "tomorrow"}, "bad_start"),
])
def test_rejects_bad_proposals(kind, data, err):
    with pytest.raises(aa.ActionError, match=err):
        aa.normalize(kind, data)
