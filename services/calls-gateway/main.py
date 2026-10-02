"""calls-gateway — the calls plane's file owner.

The ONLY place call audio lives. Folder layout under CALLS_DATA_DIR (a Railway volume):

    inbox/     the API just delivered it (written .tmp → atomic rename)
    queued/    the listener put a job on calls:jobs for it
    done/      transcribed (+ <id>.json, the transcript, until the API has stored it)
    failed/    the transcriber gave up on it

The listener watches inbox/ with inotify (watchdog) AND rescans every RESCAN_S, so a
missed filesystem event never strands a recording. Enqueue is idempotent (a Lua
SET-NX+XADD), so a crash anywhere between "enqueued" and "moved" re-runs safely.

Private service: every route except /health requires the shared X-Calls-Secret.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import time
from contextlib import asynccontextmanager
from pathlib import Path

import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import calls_contract as C

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s calls-gateway %(message)s")
log = logging.getLogger("calls-gateway")

DATA_DIR = Path(os.environ.get("CALLS_DATA_DIR", "/data/calls"))
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
SECRET = os.environ.get("CALLS_SECRET", "")
RETENTION_DAYS = float(os.environ.get("CALLS_AUDIO_RETENTION_DAYS", "7"))
MAX_BYTES = int(os.environ.get("CALLS_MAX_BYTES", str(80 * 1024 * 1024)))
RESCAN_S = 60
CONSUMER = f"{socket.gethostname()}-{os.getpid()}"

INBOX, QUEUED, DONE, FAILED = (DATA_DIR / d for d in ("inbox", "queued", "done", "failed"))

# SET NX the marker, and XADD only if this call set it — one atomic step, so the same
# file is enqueued exactly once no matter how often it is seen.
_ENQUEUE_LUA = """
if redis.call('SET', KEYS[1], '1', 'NX', 'EX', 2592000) then
  return redis.call('XADD', KEYS[2], '*', 'call_id', ARGV[1], 'filename', ARGV[2])
end
return false
"""

r: aioredis.Redis | None = None


def _check(request: Request) -> None:
    if not SECRET or request.headers.get(C.SECRET_HEADER) != SECRET:
        raise HTTPException(401, "bad secret")


def _call_id(call_id: str) -> str:
    if not C.is_valid_call_id(call_id):
        raise HTTPException(400, "bad call id")
    return call_id


def _find_audio(call_id: str) -> Path | None:
    for folder in (QUEUED, INBOX, DONE, FAILED):
        for ext in C.AUDIO_EXTS:
            p = folder / f"{call_id}{ext}"
            if p.exists():
                return p
    return None


def _audio_files(folder: Path):
    for p in folder.iterdir():
        if p.is_file() and p.suffix in C.AUDIO_EXTS and C.is_valid_call_id(p.stem):
            yield p


# ── listener ──────────────────────────────────────────────────────────────────

async def enqueue(path: Path) -> None:
    """inbox/<id>.<ext> → job on calls:jobs → queued/. Safe to call twice."""
    if not path.exists() or path.parent != INBOX or path.suffix not in C.AUDIO_EXTS:
        return
    call_id = path.stem
    if not C.is_valid_call_id(call_id):
        return
    msg_id = await r.eval(_ENQUEUE_LUA, 2, C.ENQUEUED_KEY.format(call_id=call_id), C.JOBS_STREAM,
                          call_id, path.name)
    try:
        path.rename(QUEUED / path.name)
    except FileNotFoundError:
        return  # another pass moved it first
    log.info("enqueued %s (%s)", call_id, msg_id or "already queued")


class _InboxHandler(FileSystemEventHandler):
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    def _go(self, p: str) -> None:
        asyncio.run_coroutine_threadsafe(enqueue(Path(p)), self.loop)

    def on_moved(self, event):        # the .tmp → final rename lands here
        if not event.is_directory:
            self._go(event.dest_path)

    def on_closed(self, event):       # a file copied straight into inbox/
        if not event.is_directory:
            self._go(event.src_path)


async def rescan_loop() -> None:
    while True:
        try:
            for p in list(_audio_files(INBOX)):
                await enqueue(p)
        except Exception:
            log.exception("rescan failed")
        await asyncio.sleep(RESCAN_S)


# ── events (group "gateway") → move the file to done/ | failed/ ───────────────

async def _settle(call_id: str, status: str) -> None:
    src = _find_audio(call_id)
    if not src or src.parent in (DONE, FAILED):
        return
    dest = DONE if status == C.EV_TRANSCRIBED else FAILED
    src.rename(dest / src.name)
    log.info("%s → %s/", call_id, dest.name)


async def events_loop() -> None:
    try:
        await r.xgroup_create(C.EVENTS_STREAM, C.GATEWAY_GROUP, id="0", mkstream=True)
    except aioredis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise
    while True:
        try:
            resp = await r.xreadgroup(C.GATEWAY_GROUP, CONSUMER, {C.EVENTS_STREAM: ">"}, count=20, block=5000)
            for _stream, msgs in resp or []:
                for msg_id, f in msgs:
                    if f.get("status") in (C.EV_TRANSCRIBED, C.EV_FAILED) and C.is_valid_call_id(f.get("call_id", "")):
                        await _settle(f["call_id"], f["status"])
                    await r.xack(C.EVENTS_STREAM, C.GATEWAY_GROUP, msg_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("events loop error — retrying in 5s")
            await asyncio.sleep(5)


# ── retention: audio is deleted RETENTION_DAYS after it settled ──────────────

async def retention_loop() -> None:
    while True:
        cutoff = time.time() - RETENTION_DAYS * 86400
        for folder in (DONE, FAILED):
            for p in folder.iterdir():
                try:
                    if p.is_file() and p.stat().st_mtime < cutoff:
                        p.unlink()
                        log.info("retention: deleted %s", p.name)
                except FileNotFoundError:
                    pass
        await asyncio.sleep(3600)


# ── app ──────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global r
    if not SECRET:
        log.warning("CALLS_SECRET is empty — every protected route will refuse")
    for d in (INBOX, QUEUED, DONE, FAILED):
        d.mkdir(parents=True, exist_ok=True)
    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    loop = asyncio.get_running_loop()
    observer = Observer()
    observer.schedule(_InboxHandler(loop), str(INBOX), recursive=False)
    observer.start()
    tasks = [asyncio.create_task(t()) for t in (rescan_loop, events_loop, retention_loop)]
    log.info("up: data=%s consumer=%s", DATA_DIR, CONSUMER)
    yield
    for t in tasks:
        t.cancel()
    observer.stop()
    await r.aclose()


app = FastAPI(title="calls-gateway", lifespan=lifespan)


@app.get("/health")
async def health():
    try:
        await r.ping()
        redis_ok = True
    except Exception:
        redis_ok = False
    counts = {d.name: sum(1 for _ in _audio_files(d)) for d in (INBOX, QUEUED, DONE, FAILED)}
    return {"ok": redis_ok, "redis": redis_ok, "files": counts}


@app.post("/ingest/{call_id}")
async def ingest(call_id: str, request: Request, ext: str = ".webm"):
    _check(request)
    call_id = _call_id(call_id)
    if ext not in C.AUDIO_EXTS:
        raise HTTPException(400, "bad extension")
    final = INBOX / f"{call_id}{ext}"
    tmp = INBOX / f".{call_id}{ext}.tmp"   # dotfile + .tmp: the listener ignores it
    size = 0
    with tmp.open("wb") as fh:
        async for chunk in request.stream():
            size += len(chunk)
            if size > MAX_BYTES:
                fh.close()
                tmp.unlink(missing_ok=True)
                raise HTTPException(413, "too large")
            fh.write(chunk)
    if size == 0:
        tmp.unlink(missing_ok=True)
        raise HTTPException(400, "empty body")
    tmp.rename(final)
    await enqueue(final)   # don't wait for inotify; the watcher/rescan are the safety net
    return {"ok": True, "bytes": size}


@app.get("/files/{call_id}")
async def get_file(call_id: str, request: Request):
    _check(request)
    p = _find_audio(_call_id(call_id))
    if not p:
        raise HTTPException(404, "no audio")
    return FileResponse(p, filename=p.name)


@app.put("/transcripts/{call_id}")
async def put_transcript(call_id: str, request: Request):
    _check(request)
    call_id = _call_id(call_id)
    body = await request.json()
    tmp = DONE / f".{call_id}.json.tmp"
    tmp.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    tmp.rename(DONE / f"{call_id}.json")
    return {"ok": True}


@app.get("/transcripts/{call_id}")
async def get_transcript(call_id: str, request: Request):
    _check(request)
    p = DONE / f"{_call_id(call_id)}.json"
    if not p.exists():
        raise HTTPException(404, "no transcript")
    return json.loads(p.read_text(encoding="utf-8"))


@app.delete("/files/{call_id}")
async def delete_call(call_id: str, request: Request):
    """The agent deleted the call — remove its audio and transcript everywhere."""
    _check(request)
    call_id = _call_id(call_id)
    removed = 0
    for folder in (INBOX, QUEUED, DONE, FAILED):
        for p in folder.glob(f"{call_id}*"):
            p.unlink(missing_ok=True)
            removed += 1
    await r.delete(C.TRANSCRIPT_KEY.format(call_id=call_id))
    return {"ok": True, "removed": removed}
