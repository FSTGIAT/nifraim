"""Semantic search over calls: every finished call is cut into short passages (who said
what, when) plus one summary passage; each gets an embedding stored in Postgres
(pgvector, table call_chunks). A question like "מה הלקוח אמר על הלוואה לדירה" then finds
the משכנתא line even though no word matches.

The model runs IN the API process on CPU (ONNX, no torch, nothing leaves our servers).
It is one setting — CALLS_EMBED_MODEL — chosen from EMBED_MODELS below; changing it means
a new migration for the vector size + `scripts/reindex_calls.py`, never new code.
Embedding never fails a call: no model / no pgvector → keyword search_calls still works.
"""
from __future__ import annotations

import asyncio
import logging
import os
import threading
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmbedModel:
    repo: str                 # HF repo holding the ONNX export + tokenizer.json
    onnx_file: str
    dim: int
    pooling: str              # "mean" | "cls" | "last" | "sentence" (model outputs sentence_embedding)
    query_prefix: str = ""
    doc_prefix: str = ""
    max_tokens: int = 512


EMBED_MODELS: dict[str, EmbedModel] = {
    # 2023, ~120MB q8, 7/9 on our Hebrew call test (2026-10-05)
    "multilingual-e5-small": EmbedModel("Xenova/multilingual-e5-small", "onnx/model_quantized.onnx", 384, "mean",
                                        "query: ", "passage: "),
    "multilingual-e5-base": EmbedModel("Xenova/multilingual-e5-base", "onnx/model_quantized.onnx", 768, "mean",
                                       "query: ", "passage: "),
    # 2024, BAAI (MIT), 568M — strong multilingual retrieval, no prefixes, CLS pooling
    "bge-m3": EmbedModel("Xenova/bge-m3", "onnx/model_quantized.onnx", 1024, "cls", max_tokens=1024),
    # 2025 — Qwen3 0.6B (Apache-2.0), last-token pooling with an instruction on the query side
    "qwen3-embedding-0.6b": EmbedModel("onnx-community/Qwen3-Embedding-0.6B-ONNX", "onnx/model_quantized.onnx", 1024, "last",
                                       "Instruct: Given a search query, find the sentence from an insurance agent phone call that answers it\nQuery: ",
                                       "", 1024),
    # 2025 — Google EmbeddingGemma 300m (Gemma licence), 6/9 on the same test
    "embeddinggemma-300m": EmbedModel("onnx-community/embeddinggemma-300m-ONNX", "onnx/model_quantized.onnx", 768, "sentence",
                                      "task: search result | query: ", "title: none | text: "),
}
DEFAULT_MODEL = "multilingual-e5-small"


def model_name() -> str:
    return os.environ.get("CALLS_EMBED_MODEL", DEFAULT_MODEL)


def spec() -> EmbedModel:
    return EMBED_MODELS[model_name()]


class _Embedder:
    """Lazy ONNX session + tokenizer, loaded once per process (thread-safe)."""

    def __init__(self, m: EmbedModel):
        import numpy as np
        import onnxruntime as ort
        from huggingface_hub import snapshot_download
        from tokenizers import Tokenizer

        cache = os.environ.get("CALLS_EMBED_CACHE", os.path.join(os.path.expanduser("~"), ".cache", "nifraim-embed"))
        d = snapshot_download(m.repo, allow_patterns=[m.onnx_file + "*", "tokenizer.json"],
                              local_dir=os.path.join(cache, m.repo.replace("/", "__")))
        self.np = np
        self.m = m
        self.tok = Tokenizer.from_file(os.path.join(d, "tokenizer.json"))
        self.tok.enable_truncation(m.max_tokens)
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = int(os.environ.get("CALLS_EMBED_THREADS", "2"))   # the API is shared — stay polite
        self.sess = ort.InferenceSession(os.path.join(d, m.onnx_file), opts, providers=["CPUExecutionProvider"])
        self.inputs = {i.name for i in self.sess.get_inputs()}
        self.outputs = [o.name for o in self.sess.get_outputs()]

    def embed(self, texts: list[str]):
        np = self.np
        out = []
        for i in range(0, len(texts), 16):
            enc = self.tok.encode_batch(texts[i:i + 16])
            L = max(len(e.ids) for e in enc)
            pad = self.tok.token_to_id("<pad>") or 0
            # left-pad for last-token pooling so the last position is always real
            left = self.m.pooling == "last"
            ids = np.array([([pad] * (L - len(e.ids)) + e.ids) if left else (e.ids + [pad] * (L - len(e.ids))) for e in enc], dtype=np.int64)
            am = np.array([([0] * (L - len(e.ids)) + [1] * len(e.ids)) if left else ([1] * len(e.ids) + [0] * (L - len(e.ids))) for e in enc], dtype=np.int64)
            feed = {"input_ids": ids, "attention_mask": am}
            if "token_type_ids" in self.inputs:
                feed["token_type_ids"] = np.zeros_like(ids)
            if "position_ids" in self.inputs:
                feed["position_ids"] = np.maximum(np.cumsum(am, axis=1) - 1, 0)
            if self.m.pooling == "sentence" and "sentence_embedding" in self.outputs:
                v = self.sess.run(["sentence_embedding"], feed)[0]
            else:
                h = self.sess.run([self.outputs[0]], feed)[0]
                if self.m.pooling == "last":
                    v = h[:, -1, :]
                elif self.m.pooling == "cls":
                    v = h[:, 0, :]
                else:
                    mask = am[..., None].astype(h.dtype)
                    v = (h * mask).sum(1) / np.clip(mask.sum(1), 1e-9, None)
            v = v / np.clip(np.linalg.norm(v, axis=1, keepdims=True), 1e-9, None)
            out.extend(v.astype("float32").tolist())
        return out


_lock = threading.Lock()
_inst: _Embedder | None = None
_failed = False


def _get() -> _Embedder | None:
    global _inst, _failed
    if _inst or _failed:
        return _inst
    with _lock:
        if _inst is None and not _failed:
            try:
                _inst = _Embedder(spec())
                logger.info("calls: embedder %s loaded", model_name())
            except Exception:  # noqa: BLE001 — semantic search is optional
                logger.exception("calls: embedder unavailable — keyword search only")
                _failed = True
    return _inst


async def embed_docs(texts: list[str]) -> list[list[float]] | None:
    e = await asyncio.to_thread(_get)
    if not e or not texts:
        return None
    return await asyncio.to_thread(e.embed, [spec().doc_prefix + t for t in texts])


async def embed_query(text: str) -> list[float] | None:
    e = await asyncio.to_thread(_get)
    if not e:
        return None
    return (await asyncio.to_thread(e.embed, [spec().query_prefix + text]))[0]


# ── passages ─────────────────────────────────────────────────────────────

ROLE_HE = {"agent": "סוכן", "customer": "לקוח"}


def passages(call) -> list[dict]:
    """A call as searchable passages — ONE speaker turn each (8–30 words), so a passage is
    about one thing. Long merged windows let the greeting ("שלום, מדבר קיקו…") dominate the
    vector and buried the topic (measured: "הלוואה לרכישת דירה" missed the משכנתא turn).
    Plus one passage of the summary."""
    ins = call.insights or {}
    roles = ins.get("speaker_roles") or {}
    out, buf, words = [], [], 0

    def flush():
        nonlocal buf, words
        if buf:
            out.append({"kind": "said", "start": float(buf[0].get("start") or 0), "end": float(buf[-1].get("end") or 0),
                        "role": roles.get(buf[0].get("speaker")),
                        "text": " ".join(s.get("text", "").strip() for s in buf).strip()})
        buf, words = [], 0

    for s in call.segments or []:
        t = (s.get("text") or "").strip()
        if not t:
            continue
        n = len(t.split())
        same_turn = buf and s.get("speaker") == buf[-1].get("speaker")
        if buf and (not same_turn or words + n > 30) and words >= 8:
            flush()
        elif buf and not same_turn and words < 8 and roles:
            flush()        # never glue two speakers together when we know who is who
        buf.append(s)
        words += n
    flush()
    summary = " ".join(x for x in (call.title, ins.get("tldr"), call.summary,
                                   " ".join(ins.get("topics") or []), " ".join(ins.get("customer_needs") or [])) if x)
    if summary.strip():
        out.append({"kind": "summary", "start": 0.0, "end": 0.0, "role": None, "text": summary.strip()})
    return [p for p in out if len(p["text"]) >= 4]


def _vec(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


async def index_call(db, call) -> int:
    """(Re)build the call's passages + embeddings. Returns the number stored (0 = skipped)."""
    from sqlalchemy import text
    ps = passages(call)
    if not ps:
        return 0
    vecs = await embed_docs([p["text"] for p in ps])
    if not vecs:
        return 0
    await db.execute(text("DELETE FROM call_chunks WHERE call_id = :c"), {"c": call.id})
    for i, (p, v) in enumerate(zip(ps, vecs)):
        await db.execute(text(
            "INSERT INTO call_chunks (call_id, user_id, idx, kind, start_s, end_s, role, text, model, embedding) "
            "VALUES (:c, :u, :i, :k, :s, :e, :r, :t, :m, CAST(:v AS vector))"),
            {"c": call.id, "u": call.user_id, "i": i, "k": p["kind"], "s": p["start"], "e": p["end"],
             "r": p["role"], "t": p["text"][:2000], "m": model_name(), "v": _vec(v)})
    await db.commit()
    return len(ps)


async def search(db, user_id, query: str, k: int = 12, since=None, until=None, call_ids=None) -> list[dict] | None:
    """Nearest passages to the question, this user only. None = semantic search unavailable."""
    from sqlalchemy import text
    q = await embed_query(query)
    if q is None:
        return None
    where = ["ch.user_id = :u", "ch.model = :m"]
    args = {"u": user_id, "m": model_name(), "q": _vec(q), "k": k}
    if since is not None:
        where.append("COALESCE(cr.started_at, cr.created_at) >= :since")
        args["since"] = since
    if until is not None:
        where.append("COALESCE(cr.started_at, cr.created_at) <= :until")
        args["until"] = until
    if call_ids:
        where.append("ch.call_id = ANY(:ids)")
        args["ids"] = list(call_ids)
    try:
        rows = (await db.execute(text(
            "SELECT ch.call_id, ch.kind, ch.start_s, ch.role, ch.text, 1 - (ch.embedding <=> CAST(:q AS vector)) AS score "
            "FROM call_chunks ch JOIN call_recordings cr ON cr.id = ch.call_id "
            f"WHERE {' AND '.join(where)} ORDER BY ch.embedding <=> CAST(:q AS vector) LIMIT :k"), args)).mappings().all()
    except Exception:  # noqa: BLE001 — no pgvector / no table yet
        logger.exception("calls: semantic search failed")
        await db.rollback()
        return None
    return [dict(r) for r in rows]
