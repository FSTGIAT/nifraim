"""Speaker labels on calls: word→speaker assignment, segment splitting, prompt formatting, talk ratio.
Pure functions only — no pyannote / whisper model needed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "ivrit-transcriber"))

from speakers import label_segments  # noqa: E402
from app.services.calls.events_consumer import _clean_roles, talk_ratio  # noqa: E402
from app.services.calls.summarize import _fmt, has_speakers  # noqa: E402


def w(s, e, t):
    return {"start": s, "end": e, "word": t}


def test_segment_split_at_speaker_change():
    segs = [{"start": 0, "end": 6, "text": "שלום מה שלומך טוב תודה", "words": [
        w(0, 1, " שלום"), w(1, 2, " מה"), w(2, 3, " שלומך"), w(3.5, 4.5, " טוב"), w(4.5, 6, " תודה")]}]
    turns = [(0.0, 3.2, "SPEAKER_07"), (3.3, 6.0, "SPEAKER_02")]
    out = label_segments(segs, turns)
    assert [(s["speaker"], s["text"]) for s in out] == [("S1", "שלום מה שלומך"), ("S2", "טוב תודה")]
    assert out[0]["end"] == 3 and out[1]["start"] == 3.5


def test_names_follow_first_heard_and_gaps_use_nearest():
    segs = [{"start": 0, "end": 2, "text": "כן", "words": [w(0, 1, " כן")]},
            {"start": 10, "end": 12, "text": "בסדר", "words": [w(10, 11, " בסדר")]}]
    turns = [(0.0, 1.0, "B"), (9.0, 9.5, "A")]   # second word overlaps no turn → nearest (A)
    out = label_segments(segs, turns)
    assert [s["speaker"] for s in out] == ["S1", "S2"]


def test_no_turns_keeps_unlabelled():
    segs = [{"start": 0, "end": 1, "text": "שלום", "words": []}]
    assert label_segments(segs, []) == [{"start": 0, "end": 1, "text": "שלום"}]


def test_prompt_formatting():
    labelled = [{"start": 65, "end": 70, "text": "שלום", "speaker": "S2"}]
    assert _fmt(labelled) == "[01:05] S2: שלום" and has_speakers(labelled)
    plain = [{"start": 5, "end": 7, "text": "שלום"}]
    assert _fmt(plain) == "[00:05] שלום" and not has_speakers(plain)


def test_talk_ratio_and_roles():
    segs = [{"start": 0, "end": 30, "speaker": "S1"}, {"start": 30, "end": 40, "speaker": "S2"}]
    roles = _clean_roles({"S1": "agent", "S2": "customer", "S3": "agent", "S9": "boss"}, segs)
    assert roles == {"S1": "agent", "S2": "customer"}
    assert talk_ratio(segs, roles) == {"agent_s": 30.0, "customer_s": 10.0, "agent_pct": 75}
    assert _clean_roles({"S1": "agent"}, [{"start": 0, "end": 1}]) == {}
