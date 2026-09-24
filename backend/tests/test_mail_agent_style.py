"""Mail Agent writing-style tests — prompt order, signing, rules per kind, sent-folder discovery.

    source backend/venv/bin/activate && python backend/tests/test_mail_agent_style.py

No network, no API key. The assertions that carry real weight:
  * the hard grounding rules come BEFORE the agent's style, and the style block
    says it loses any conflict — style can never override grounding;
  * the draft ends with the exact profile signature (appended in code), and
    with no signature at all it ends in a [להשלים] gap the send button refuses;
  * customer rules reach only customer drafts, insurer rules only insurer drafts;
  * text from old example replies is NOT trusted by the amount validator;
  * the Sent folder is found by its \\Sent flag, not by a hardcoded English name.
"""
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.mail_agent import draft  # noqa: E402
from app.services.mail_intake import search  # noqa: E402

PROFILE = {
    "signature": "רועי גיא\nסוכנות גיא ביטוחים\n050-1234567",
    "tone": "warm", "address_form": "female", "writer_form": "female",
    "greeting": "היי {שם},", "closing": "תמיד כאן בשבילך,",
    "customer_rules": "שעות פעילות: א-ה 9:00-17:00",
    "insurer_rules": "לציין את מספר הסוכן 12345",
    "never_say": "לא להבטיח אישור תביעה",
    "style_notes": "• משפטים קצרים",
    "examples": ["היי יוסי, העברתי ₪4,200 לחשבונך. תמיד כאן בשבילך,"],
}


def test_hard_rules_precede_style():
    s = draft.build_system(PROFILE, "customer")
    assert s.startswith(draft.HARD_RULES)
    assert s.index("כללים מחייבים") < s.index("לא להבטיח אישור תביעה") < s.index(draft.STYLE_HEADER)
    assert s.index(draft.STYLE_HEADER) < s.index(draft.STYLE_PRECEDENCE) < s.index("טון:")
    assert "לטון ולניסוח בלבד" in s
    assert "אני יכולה" in s and s.index(draft.STYLE_HEADER) < s.index("אני יכולה")


def test_no_profile_is_just_the_rules():
    assert draft.build_system(None, "customer") == draft.HARD_RULES
    assert draft.build_system({}, "insurer") == draft.HARD_RULES


def test_rules_by_kind():
    c, i, o = (draft.build_system(PROFILE, k) for k in ("customer", "insurer", "other"))
    assert "שעות פעילות" in c and "מספר הסוכן 12345" not in c
    assert "מספר הסוכן 12345" in i and "שעות פעילות" not in i
    assert "שעות פעילות" not in o and "מספר הסוכן 12345" not in o


def test_signature_appended_exactly_once():
    sig = PROFILE["signature"]
    out = draft.sign("שלום דנה,\nהפוליסה בתוקף.\nתמיד כאן בשבילך,", sig)
    assert out.endswith(sig) and out.count(sig) == 1
    assert draft.sign(out, sig).count(sig) == 1
    assert draft.sign("גוף", "").endswith("[להשלים: שם הסוכן]")
    assert draft.signature_of({}, "רועי") == "רועי"


def _fake_call(body):
    async def call_tool(**kw):
        call_tool.system = kw["system"]
        return {"subject": "Re: x", "body": body}, "fake", SimpleNamespace(input_tokens=1, output_tokens=1)
    return call_tool


def test_draft_reply_signs_and_validates():
    orig = draft.call_tool
    try:
        draft.call_tool = _fake_call("היי דנה,\nהביטוח בתוקף.\nתמיד כאן בשבילך,")
        res, _, _ = asyncio.run(draft.draft_reply(
            agent_name="", sender_label="דנה", subject="x", own_text="האם הביטוח בתוקף?",
            summary="", facts={}, profile=PROFILE, kind="customer"))
        assert res["body"].endswith(PROFILE["signature"])
        assert draft.call_tool.system.startswith(draft.HARD_RULES)
        # An amount lifted from an old example reply must still be flagged.
        draft.call_tool = _fake_call("היי דנה, העברתי ₪4,200 לחשבונך.")
        res, _, _ = asyncio.run(draft.draft_reply(
            agent_name="", sender_label="דנה", subject="x", own_text="מתי הכסף?",
            summary="", facts={}, profile=PROFILE, kind="customer"))
        assert res["warnings"], "amount copied from an example was not flagged"
    finally:
        draft.call_tool = orig


class _FakeImap:
    def __init__(self, lines):
        self.lines = lines

    def list(self):
        return "OK", self.lines


def test_sent_folder_by_flag():
    heb = [b'(\\HasNoChildren) "/" "INBOX"',
           b'(\\All \\HasNoChildren) "/" "[Gmail]/&BdsF3A- &BdQF0wXVBdAF6A-"',
           b'(\\HasNoChildren \\Sent) "/" "[Gmail]/&BdMF1QXQBegF3A- &BdkF1QXmBdA-"']
    assert search._imap_sent_folder(_FakeImap(heb)) == '"[Gmail]/&BdMF1QXQBegF3A- &BdkF1QXmBdA-"'
    assert search._imap_sent_folder(_FakeImap([b'(\\HasNoChildren) "." "Sent Items"'])) == '"Sent Items"'
    assert search._imap_quote("[Gmail]/Sent Mail") == '"[Gmail]/Sent Mail"'
    assert search._imap_from_criteria(["a@x.com", "@y.co.il"], "TO") == ["OR", "TO", '"a@x.com"', "TO", '"@y.co.il"']


def test_to_addresses_parsed():
    raw = (b"From: Agent <agent@gmail.com>\r\nTo: Dana <DANA@example.com>\r\nCc: b@y.co.il\r\n"
           b"Date: Thu, 24 Sep 2026 10:00:00 +0300\r\nSubject: hi\r\nMessage-ID: <1@x>\r\n\r\nbody\r\n")
    m = search._parse_rfc822(raw)
    assert m.to_addrs == ["dana@example.com", "b@y.co.il"]


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("ok ", name)
    print(f"{n} passed")
