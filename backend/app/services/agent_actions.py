"""Nifra Agent's hands — things it can DO, not only answer.

The model never sends anything. Its tools (`propose_email`, `propose_meeting`)
only PREPARE an action; the panel shows it as an editable sheet and the agent's
"אישור ושליחה" click posts it to /api/office-agent/act, which sends from the
agent's own mailbox (mail_intake/send.send_as_agent — Gmail app password today).

A meeting is a real calendar invitation: an iCalendar REQUEST (RFC 5545/5546)
mailed to the customer, with a copy to the agent — Gmail / Outlook render it as
an invite with accept / decline. There is no Google Calendar API consent in the
app (the mailbox is IMAP/SMTP), so the invite IS the scheduling channel.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from zoneinfo import ZoneInfo

IL = ZoneInfo("Asia/Jerusalem")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
HE_DAYS = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]

PROPOSE_EMAIL_TOOL = {
    "name": "propose_email",
    "description": "הכנת מייל שהסוכן ישלח מהתיבה שלו (ללקוח, לחברה או לכל כתובת). המייל לא נשלח — הסוכן רואה, עורך ומאשר.",
    "input_schema": {
        "type": "object",
        "properties": {
            "to_email": {"type": "string"},
            "to_name": {"type": "string"},
            "subject": {"type": "string"},
            "body": {"type": "string", "description": "גוף המייל בעברית, בגוף ראשון של הסוכן, בלי חתימה"},
        },
        "required": ["to_email", "subject", "body"],
    },
}
PROPOSE_MEETING_TOOL = {
    "name": "propose_meeting",
    "description": "קביעת פגישה: מכין זימון יומן (הזמנה עם אישור/דחייה) שיישלח למשתתף מהתיבה של הסוכן. לא נשלח עד שהסוכן מאשר.",
    "input_schema": {
        "type": "object",
        "properties": {
            "to_email": {"type": "string"},
            "to_name": {"type": "string"},
            "title": {"type": "string"},
            "start": {"type": "string", "description": "שעת התחלה בשעון ישראל, ISO: YYYY-MM-DDTHH:MM"},
            "duration_min": {"type": "integer"},
            "location": {"type": "string", "description": "כתובת, 'טלפון' או קישור לשיחת וידאו"},
            "note": {"type": "string", "description": "שורה-שתיים לגוף ההזמנה"},
        },
        "required": ["to_email", "title", "start"],
    },
}
TOOLS = [PROPOSE_EMAIL_TOOL, PROPOSE_MEETING_TOOL]


class ActionError(ValueError):
    pass


def _parse_start(s: str) -> datetime:
    try:
        d = datetime.fromisoformat(str(s).strip().replace("Z", ""))
    except ValueError as e:
        raise ActionError("bad_start") from e
    return d.replace(tzinfo=IL) if d.tzinfo is None else d.astimezone(IL)


def normalize(kind: str, data: dict) -> dict:
    """Validate a proposal (from the model or from the agent's edited sheet)."""
    to = str(data.get("to_email") or "").strip()
    if not EMAIL_RE.match(to):
        raise ActionError("bad_email")
    out = {"kind": kind, "to_email": to, "to_name": str(data.get("to_name") or "").strip()[:120]}
    if kind == "email":
        subject, body = str(data.get("subject") or "").strip(), str(data.get("body") or "").strip()
        if not subject or not body:
            raise ActionError("missing_text")
        return {**out, "subject": subject[:200], "body": body[:8000]}
    if kind == "meeting":
        start = _parse_start(data.get("start"))
        dur = int(data.get("duration_min") or 30)
        return {
            **out,
            "title": (str(data.get("title") or "").strip() or "פגישה")[:200],
            "start": start.strftime("%Y-%m-%dT%H:%M"),
            "duration_min": max(10, min(dur, 480)),
            "location": str(data.get("location") or "").strip()[:200],
            "note": str(data.get("note") or "").strip()[:2000],
        }
    raise ActionError("bad_kind")


def when_he(start: str, duration_min: int) -> str:
    d = _parse_start(start)
    end = d + timedelta(minutes=duration_min)
    return f"יום {HE_DAYS[d.weekday()]} {d.day}.{d.month}.{d.year} · {d:%H:%M}–{end:%H:%M}"


def _ics_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def build_ics(m: dict, organizer_email: str, organizer_name: str, uid: str | None = None) -> str:
    start = _parse_start(m["start"]).astimezone(timezone.utc)
    end = start + timedelta(minutes=m["duration_min"])
    fmt = "%Y%m%dT%H%M%SZ"
    lines = [
        "BEGIN:VCALENDAR", "PRODID:-//Nifraim//Nifra Agent//HE", "VERSION:2.0", "METHOD:REQUEST",
        "BEGIN:VEVENT",
        f"UID:{uid or uuid.uuid4()}@nifraim.com",
        f"DTSTAMP:{datetime.now(timezone.utc):{fmt}}",
        f"DTSTART:{start:{fmt}}", f"DTEND:{end:{fmt}}",
        f"SUMMARY:{_ics_escape(m['title'])}",
        f"ORGANIZER;CN={_ics_escape(organizer_name or organizer_email)}:mailto:{organizer_email}",
        f"ATTENDEE;CN={_ics_escape(m.get('to_name') or m['to_email'])};ROLE=REQ-PARTICIPANT;PARTSTAT=NEEDS-ACTION;RSVP=TRUE:mailto:{m['to_email']}",
        f"ATTENDEE;CN={_ics_escape(organizer_name or organizer_email)};ROLE=CHAIR;PARTSTAT=ACCEPTED:mailto:{organizer_email}",
    ]
    if m.get("location"):
        lines.append(f"LOCATION:{_ics_escape(m['location'])}")
    if m.get("note"):
        lines.append(f"DESCRIPTION:{_ics_escape(m['note'])}")
    lines += ["STATUS:CONFIRMED", "SEQUENCE:0", "END:VEVENT", "END:VCALENDAR"]
    return "\r\n".join(lines) + "\r\n"


def build_message(p: dict, sender_email: str, sender_name: str) -> EmailMessage:
    domain = sender_email.split("@")[-1] or "nifraim.com"
    msg = EmailMessage()
    msg["To"] = formataddr((p.get("to_name") or "", p["to_email"]))
    msg["Message-ID"] = make_msgid(domain=domain)
    if p["kind"] == "email":
        msg["Subject"] = p["subject"]
        msg.set_content(p["body"])
        return msg
    # meeting: the agent gets a copy so it lands on their side too
    msg["Subject"] = f"הזמנה: {p['title']} · {when_he(p['start'], p['duration_min'])}"
    if p["to_email"].lower() != sender_email.lower():  # a reminder to self needs no copy
        msg["Cc"] = sender_email
    text = "\n".join(x for x in [
        f"שלום{' ' + p['to_name'] if p.get('to_name') else ''},", "",
        f"קבעתי לנו פגישה: {p['title']}",
        when_he(p["start"], p["duration_min"]),
        f"מיקום: {p['location']}" if p.get("location") else "",
        p.get("note") or "", "",
        "אפשר לאשר או לדחות ישירות מההזמנה.",
    ] if x is not None)
    msg.set_content(text)
    ics = build_ics(p, sender_email, sender_name)
    msg.add_alternative(ics, subtype="calendar", params={"method": "REQUEST"})
    msg.add_attachment(ics.encode(), maintype="application", subtype="ics", filename="invite.ics")
    return msg


async def send(db, user, kind: str, data: dict) -> dict:
    """The agent approved — send it from their own mailbox."""
    from app.services.agreement_requests import mailbox_state
    from app.services.mail_intake.send import send_as_agent

    p = normalize(kind, data)
    state = await mailbox_state(db, user.id)
    if not state.get("can_send"):
        raise ActionError(state.get("reason") or "cannot_send")
    msg = build_message(p, state["mailbox_address"], user.full_name or "")
    await send_as_agent(user.id, msg, display_name=user.full_name)
    return {"ok": True, "kind": kind, "to_email": p["to_email"]}
