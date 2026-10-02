"""ivrit-transcriber — Hebrew speech-to-text worker for the calls plane.

Consumes calls:jobs (consumer group "transcribers"), fetches the audio from
calls-gateway, transcribes it with an ivrit.ai Whisper model (faster-whisper /
CTranslate2, int8 on CPU), and publishes the result:

    transcript JSON → gateway done/<id>.json  AND  Redis calls:tx:<id>
    XADD calls:events {status: transcribed | failed}
    XACK the job

SQS semantics on Redis Streams:
  * a job is acked only after its result is durable;
  * while transcribing, the worker re-XCLAIMs its own job every HEARTBEAT_S, so a long
    recording is never mistaken for a crashed worker;
  * an idle job (crashed worker) is XAUTOCLAIMed after VISIBILITY_TIMEOUT_MS;
  * a job delivered more than MAX_DELIVERIES times goes to calls:dead and is failed.

TRANSCRIBER_FAKE=1 skips the model and returns a canned Hebrew transcript (UI dev).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import subprocess
import tempfile
import time
from pathlib import Path

import httpx
import redis.asyncio as aioredis

import calls_contract as C

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s ivrit %(message)s")
log = logging.getLogger("ivrit")

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
GATEWAY_URL = os.environ.get("CALLS_GATEWAY_URL", "http://localhost:8090").rstrip("/")
SECRET = os.environ.get("CALLS_SECRET", "")
MODEL_ID = os.environ.get("IVRIT_MODEL", "ivrit-ai/whisper-large-v3-turbo-ct2")
MODEL_DIR = os.environ.get("MODEL_DIR", "/models")
CPU_THREADS = int(os.environ.get("CPU_THREADS", str(os.cpu_count() or 4)))
COMPUTE_TYPE = os.environ.get("COMPUTE_TYPE", "int8")
BEAM_SIZE = int(os.environ.get("BEAM_SIZE", "1"))   # greedy: ~2.2x faster than 5, identical text on our Hebrew sample (2026-10-02)
FAKE = os.environ.get("TRANSCRIBER_FAKE", "0") == "1"
CONSUMER = f"{socket.gethostname()}-{os.getpid()}"
HEADERS = {C.SECRET_HEADER: SECRET}


class PermanentError(Exception):
    """Retrying won't help (undecodable audio, file gone) — fail the call now."""


# ── model ────────────────────────────────────────────────────────────────────

_model = None


def load_model():
    global _model
    if FAKE:
        log.info("FAKE mode — no model loaded")
        return
    from faster_whisper import WhisperModel
    t = time.time()
    _model = WhisperModel(MODEL_ID, device="cpu", compute_type=COMPUTE_TYPE,
                          cpu_threads=CPU_THREADS, download_root=MODEL_DIR)
    log.info("model %s loaded in %.1fs (threads=%d, %s)", MODEL_ID, time.time() - t, CPU_THREADS, COMPUTE_TYPE)


def probe_duration(path: Path) -> float | None:
    """MediaRecorder webm carries no reliable duration header — ask ffprobe after decoding."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=60,
        ).stdout.strip()
        return round(float(out), 1) if out and out != "N/A" else None
    except Exception:
        return None


def to_wav(src: Path, dst: Path) -> None:
    proc = subprocess.run(
        ["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", str(src), "-ac", "1", "-ar", "16000", str(dst)],
        capture_output=True, text=True, timeout=1800,
    )
    if proc.returncode != 0 or not dst.exists() or dst.stat().st_size < 1000:
        raise PermanentError(f"ffmpeg: {proc.stderr.strip()[-300:] or 'no audio'}")


def transcribe(wav: Path) -> dict:
    if FAKE:
        time.sleep(3)
        segs = [
            {"start": 0.0, "end": 4.2, "text": "שלום, מדבר הסוכן, רציתי לעבור איתך על תיק הפנסיה."},
            {"start": 4.2, "end": 9.8, "text": "בשמחה. ראיתי שדמי הניהול בקרן ההשתלמות עלו, אפשר לבדוק את זה?"},
            {"start": 9.8, "end": 15.0, "text": "בטח, אבדוק מול החברה ואחזור אלייך עד יום חמישי עם הצעה."},
        ]
        return {"segments": segs, "language": "he", "duration_s": 15.0}
    segments, info = _model.transcribe(str(wav), language="he", beam_size=BEAM_SIZE, vad_filter=True)
    segs = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segments]
    return {"segments": segs, "language": info.language, "duration_s": round(info.duration, 1)}


# ── job handling ─────────────────────────────────────────────────────────────

async def emit(r, call_id: str, status: str, **extra) -> None:
    fields = {"call_id": call_id, "status": status}
    fields.update({k: str(v) for k, v in extra.items() if v is not None})
    await r.xadd(C.EVENTS_STREAM, fields)


async def heartbeat(r, msg_id: str) -> None:
    """Reset our job's idle time so XAUTOCLAIM elsewhere never steals a live job."""
    while True:
        await asyncio.sleep(C.HEARTBEAT_S)
        try:
            await r.xclaim(C.JOBS_STREAM, C.TRANSCRIBER_GROUP, CONSUMER, 0, [msg_id], justid=True)
        except Exception:
            log.warning("heartbeat failed for %s", msg_id)


async def handle(r, http: httpx.AsyncClient, msg_id: str, fields: dict) -> None:
    call_id = fields.get("call_id", "")
    if not C.is_valid_call_id(call_id):
        log.error("dropping malformed job %s: %s", msg_id, fields)
        await r.xack(C.JOBS_STREAM, C.TRANSCRIBER_GROUP, msg_id)
        return
    await emit(r, call_id, C.EV_TRANSCRIBING)
    hb = asyncio.create_task(heartbeat(r, msg_id))
    started = time.time()
    try:
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / (fields.get("filename") or f"{call_id}.webm")
            resp = await http.get(f"{GATEWAY_URL}/files/{call_id}", headers=HEADERS)
            if resp.status_code == 404:
                raise PermanentError("audio not found on gateway")
            resp.raise_for_status()
            src.write_bytes(resp.content)
            wav = Path(td) / "audio.wav"
            await asyncio.to_thread(to_wav, src, wav)
            duration = await asyncio.to_thread(probe_duration, wav)
            result = await asyncio.to_thread(transcribe, wav)
        elapsed = time.time() - started
        duration = duration or result.get("duration_s")
        result.update({
            "call_id": call_id,
            "text": "\n".join(s["text"] for s in result["segments"] if s["text"]),
            "duration_s": duration,
            "model": "fake" if FAKE else MODEL_ID,
            "rtf": round(elapsed / duration, 3) if duration else None,
        })
        payload = json.dumps(result, ensure_ascii=False)
        # durable in two places BEFORE the event and the ack
        await r.set(C.TRANSCRIPT_KEY.format(call_id=call_id), payload)
        (await http.put(f"{GATEWAY_URL}/transcripts/{call_id}", content=payload.encode("utf-8"),
                        headers={**HEADERS, "Content-Type": "application/json"})).raise_for_status()
        await emit(r, call_id, C.EV_TRANSCRIBED, duration_s=duration, model=result["model"])
        await r.xack(C.JOBS_STREAM, C.TRANSCRIBER_GROUP, msg_id)
        log.info("%s transcribed: %ss audio in %.1fs (rtf %s, %d segments)",
                 call_id, duration, elapsed, result["rtf"], len(result["segments"]))
    except PermanentError as e:
        log.error("%s failed permanently: %s", call_id, e)
        await emit(r, call_id, C.EV_FAILED, error="לא הצלחנו לפענח את ההקלטה")
        await r.xack(C.JOBS_STREAM, C.TRANSCRIBER_GROUP, msg_id)
    except Exception:
        # transient — leave it pending; XAUTOCLAIM retries it after the visibility timeout
        log.exception("%s transient failure — will retry", call_id)
    finally:
        hb.cancel()


async def deliveries(r, msg_id: str) -> int:
    info = await r.xpending_range(C.JOBS_STREAM, C.TRANSCRIBER_GROUP, min=msg_id, max=msg_id, count=1)
    return int(info[0]["times_delivered"]) if info else 0


async def reclaim(r, http) -> None:
    """Pick up jobs whose worker died (idle past the visibility timeout)."""
    start = "0-0"
    while True:
        start, msgs, *_ = await r.xautoclaim(C.JOBS_STREAM, C.TRANSCRIBER_GROUP, CONSUMER,
                                             min_idle_time=C.VISIBILITY_TIMEOUT_MS, start_id=start, count=1)
        for msg_id, fields in msgs:
            if fields is None:
                continue  # deleted from the stream
            n = await deliveries(r, msg_id)
            if n > C.MAX_DELIVERIES:
                log.error("poison job %s (%d deliveries) → %s", msg_id, n, C.DEAD_STREAM)
                await r.xadd(C.DEAD_STREAM, {**fields, "job_id": msg_id, "deliveries": str(n)})
                await emit(r, fields.get("call_id", ""), C.EV_FAILED, error="התמלול נכשל שוב ושוב")
                await r.xack(C.JOBS_STREAM, C.TRANSCRIBER_GROUP, msg_id)
            else:
                log.info("reclaimed %s (delivery %d)", msg_id, n)
                await handle(r, http, msg_id, fields)
        if start in ("0-0", b"0-0"):
            return


async def main() -> None:
    if not SECRET:
        log.warning("CALLS_SECRET is empty — the gateway will refuse every request")
    await asyncio.to_thread(load_model)
    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    try:
        await r.xgroup_create(C.JOBS_STREAM, C.TRANSCRIBER_GROUP, id="0", mkstream=True)
    except aioredis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise
    log.info("listening on %s as %s (gateway %s)", C.JOBS_STREAM, CONSUMER, GATEWAY_URL)
    last_sweep = 0.0
    async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=10)) as http:
        while True:
            try:
                if time.time() - last_sweep > 60:
                    await reclaim(r, http)
                    last_sweep = time.time()
                # one job at a time per replica — scale by adding replicas
                resp = await r.xreadgroup(C.TRANSCRIBER_GROUP, CONSUMER, {C.JOBS_STREAM: ">"}, count=1, block=5000)
                for _stream, msgs in resp or []:
                    for msg_id, fields in msgs:
                        await handle(r, http, msg_id, fields)
            except Exception:
                log.exception("loop error — retrying in 5s")
                await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
