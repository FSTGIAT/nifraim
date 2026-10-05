"""The calls-plane wire contract — the ONE place stream names and message fields live.

Pure stdlib on purpose: services/calls-gateway and services/ivrit-transcriber COPY this
exact file into their images (as calls_contract.py), so the API, the gateway and the
transcriber can never drift apart. Change a field here → redeploy all three.

Flow: API → gateway POST /ingest → inbox/ → listener XADD JOBS → transcriber XREADGROUP
→ XADD EVENTS (transcribing | transcribed | failed) → groups "api" (DB + Claude summary)
and "gateway" (move file to done/ | failed/).
"""
from __future__ import annotations

JOBS_STREAM = "calls:jobs"        # one message per audio file to transcribe
EVENTS_STREAM = "calls:events"    # status transitions from the transcriber
DEAD_STREAM = "calls:dead"        # poison jobs (delivered too many times)

TRANSCRIBER_GROUP = "transcribers"
API_GROUP = "api"
GATEWAY_GROUP = "gateway"

ENQUEUED_KEY = "calls:enq:{call_id}"      # SET NX — the listener enqueues a file exactly once
TRANSCRIPT_KEY = "calls:tx:{call_id}"     # transcript JSON; deleted by the API once stored

SECRET_HEADER = "X-Calls-Secret"

# Job fields (JOBS_STREAM): call_id, filename, attempt
# Event fields (EVENTS_STREAM): call_id, status, error?, duration_s?, model?
EV_TRANSCRIBING = "transcribing"
EV_TRANSCRIBED = "transcribed"
EV_FAILED = "failed"

MAX_DELIVERIES = 3                 # a job delivered more often than this → DEAD_STREAM + failed
VISIBILITY_TIMEOUT_MS = 5 * 60 * 1000    # XAUTOCLAIM jobs idle longer than this (crashed worker).
HEARTBEAT_S = 60                          # a busy transcriber re-XCLAIMs its job this often, so a long
                                          # (90-min audio) transcription is never mistaken for a dead one

AUDIO_EXTS = (".webm", ".ogg", ".m4a", ".mp4", ".wav", ".mp3", ".amr", ".3gp")  # amr/3gp: phone dialers


def is_valid_call_id(call_id: str) -> bool:
    """call ids are UUID hex strings — the only thing ever used as a filename stem."""
    import re
    return bool(re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", call_id or ""))
