"""Who said each word: pyannote speaker turns → per-word speaker → segments split at speaker changes.

Pure functions (no model) so they are unit-tested in the API's test suite.

A whisper segment often spans a speaker change on a phone call ("כן", "בסדר" interjections),
so speakers are assigned per WORD (max overlap with a turn, else the nearest turn) and a
segment is cut wherever the speaker changes. Speakers are renamed S1, S2… in the order
they are first heard.
"""
from __future__ import annotations


def _speaker_at(start: float, end: float, turns: list[tuple[float, float, str]]) -> str | None:
    best, best_ov = None, 0.0
    for ts, te, spk in turns:
        ov = min(end, te) - max(start, ts)
        if ov > best_ov:
            best, best_ov = spk, ov
    if best is not None:
        return best
    mid = (start + end) / 2
    near = min(turns, key=lambda t: min(abs(mid - t[0]), abs(mid - t[1])), default=None)
    return near[2] if near else None


def label_segments(segments: list[dict], turns: list[tuple[float, float, str]]) -> list[dict]:
    """segments: [{start, end, text, words: [{start, end, word}]}] (whisper, word_timestamps=True).
    turns: [(start, end, raw_speaker)] from the diarization pipeline.
    Returns [{start, end, text, speaker}] — or the segments without `speaker` when there are no turns."""
    if not turns:
        return [{k: s[k] for k in ("start", "end", "text")} for s in segments]
    names: dict[str, str] = {}
    out: list[dict] = []
    for seg in segments:
        words = seg.get("words") or [{"start": seg["start"], "end": seg["end"], "word": seg["text"]}]
        run: dict | None = None
        for w in words:
            raw = _speaker_at(w["start"], w["end"], turns)
            spk = names.setdefault(raw, f"S{len(names) + 1}") if raw is not None else (run or {}).get("speaker")
            if run is None or spk != run["speaker"]:
                if run:
                    out.append(run)
                run = {"start": w["start"], "end": w["end"], "text": w["word"], "speaker": spk}
            else:
                run["end"] = w["end"]
                run["text"] += w["word"]
        if run:
            out.append(run)
    for s in out:
        s["text"] = " ".join(s["text"].split())
        s["start"], s["end"] = round(s["start"], 2), round(s["end"], 2)
    return [s for s in out if s["text"]]
