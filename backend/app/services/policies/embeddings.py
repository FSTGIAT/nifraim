"""Semantic search over policy documents (doc_chunks, pgvector) — the calls embedder reused.

A document's Markdown is cut into passages that each stand alone: one per heading section,
long tables one row per passage with the section heading (customer + company + policy number)
prefixed, so "מי מבוטח בסיעוד בהראל" lands on the right row. Same contract as the calls search:
indexing is best-effort and never fails an ingest; no model / no pgvector → search returns None
and the caller falls back to words (search_words).
"""
from __future__ import annotations

import logging
import re

from sqlalchemy import select, text

from app.services.calls.embeddings import _vec, embed_docs, embed_query, model_name

logger = logging.getLogger(__name__)

MAX_WORDS = 120
MAX_TRIES = 3


def chunk(markdown: str, title: str = "") -> list[dict]:
    """→ [{heading, text}]. Heading path = the H1 + nearest H2/H3, prefixed to every passage."""
    out: list[dict] = []
    h1, h2, h3 = title, "", ""
    buf: list[str] = []
    table_head: list[str] = []

    def head() -> str:
        return " › ".join(h for h in (h1, h2, h3) if h)

    def flush():
        nonlocal buf
        body = "\n".join(buf).strip()
        if body:
            words = body.split()
            if len(words) <= MAX_WORDS:
                out.append({"heading": head(), "text": body})
            else:
                for i in range(0, len(words), MAX_WORDS):
                    out.append({"heading": head(), "text": " ".join(words[i:i + MAX_WORDS])})
        buf = []

    for line in (markdown or "").splitlines():
        s = line.rstrip()
        m = re.match(r"^(#{1,3})\s+(.*)", s)
        if m:
            flush()
            lvl, t = len(m.group(1)), m.group(2).strip()
            if lvl == 1:
                h1, h2, h3 = t, "", ""
            elif lvl == 2:
                h2, h3 = t, ""
            else:
                h3 = t
            table_head = []
            continue
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue
            if not table_head:
                table_head = cells
                continue
            # one row = one passage, as "header: value" so the row reads on its own
            flush()
            pairs = [f"{h}: {v}" for h, v in zip(table_head, cells) if v]
            if pairs:
                out.append({"heading": head(), "text": " · ".join(pairs)})
            continue
        table_head = [] if not s else table_head
        buf.append(s)
    flush()
    return [c for c in out if len(c["text"]) >= 4]


async def has_table(db) -> bool:
    return bool((await db.execute(text("SELECT to_regclass('public.doc_chunks') IS NOT NULL"))).scalar())


async def index_document(db, doc) -> int:
    """(Re)build the document's passages. Returns how many were stored (0 = skipped). Commits."""
    if not doc.markdown or not await has_table(db):
        return 0
    ps = chunk(doc.markdown, doc.title)
    if not ps:
        return 0
    vecs = await embed_docs([f"{p['heading']}\n{p['text']}" for p in ps])
    if not vecs:
        return 0
    await db.execute(text("DELETE FROM doc_chunks WHERE document_id = :d"), {"d": doc.id})
    for i, (p, v) in enumerate(zip(ps, vecs)):
        await db.execute(text(
            "INSERT INTO doc_chunks (document_id, user_id, idx, heading, text, model, embedding) "
            "VALUES (:d, :u, :i, :h, :t, :m, CAST(:v AS vector))"),
            {"d": doc.id, "u": doc.user_id, "i": i, "h": p["heading"][:300], "t": p["text"][:2000],
             "m": model_name(), "v": _vec(v)})
    await db.commit()
    return len(ps)


async def index_safely(db, doc) -> int:
    try:
        return await index_document(db, doc)
    except Exception:  # noqa: BLE001 — the sweep retries
        logger.exception("policies: indexing %s failed", getattr(doc, "id", "?"))
        await db.rollback()
        return 0


async def search(db, user_id, query: str, k: int = 12, customer_id: str | None = None) -> list[dict] | None:
    """Nearest passages, this user only. None = semantic search unavailable (caller uses words)."""
    q = await embed_query(query)
    if q is None:
        return None
    where = ["ch.user_id = :u", "ch.model = :m", "d.is_current"]   # superseded fetches = history, not answers
    args = {"u": user_id, "m": model_name(), "q": _vec(q), "k": k}
    if customer_id:
        where.append("d.customer_id_number = :c")
        args["c"] = customer_id
    try:
        rows = (await db.execute(text(
            "SELECT ch.document_id, ch.heading, ch.text, d.title, d.company, d.policy_number, d.customer_id_number, "
            "d.source, 1 - (ch.embedding <=> CAST(:q AS vector)) AS score "
            "FROM doc_chunks ch JOIN policy_documents d ON d.id = ch.document_id "
            f"WHERE {' AND '.join(where)} ORDER BY ch.embedding <=> CAST(:q AS vector) LIMIT :k"), args)).mappings().all()
    except Exception:  # noqa: BLE001 — no pgvector / no table yet
        logger.exception("policies: semantic search failed")
        await db.rollback()
        return None
    return [dict(r) for r in rows]


async def search_words(db, user_id, query: str, k: int = 12, customer_id: str | None = None) -> list[dict]:
    """Exact-word fallback over the same passages, computed from the stored Markdown."""
    from app.models.policy_document import PolicyDocument
    words = [w for w in re.split(r"\s+", query) if len(w) > 1]
    if not words:
        return []
    stmt = select(PolicyDocument).where(PolicyDocument.user_id == user_id, PolicyDocument.status == "ready",
                                        PolicyDocument.is_current.is_(True))
    if customer_id:
        stmt = stmt.where(PolicyDocument.customer_id_number == customer_id)
    hits = []
    for d in (await db.execute(stmt.order_by(PolicyDocument.created_at.desc()).limit(300))).scalars().all():
        for p in chunk(d.markdown or "", d.title):
            hay = p["heading"] + " " + p["text"]
            n = sum(1 for w in words if w in hay)
            if n:
                hits.append({"document_id": d.id, "heading": p["heading"], "text": p["text"], "title": d.title,
                             "company": d.company, "policy_number": d.policy_number,
                             "customer_id_number": d.customer_id_number, "source": d.source, "score": n / len(words)})
    hits.sort(key=lambda h: -h["score"])
    return hits[:k]


async def sweep(limit: int = 20) -> int:
    """Index ready documents that have no passages under the current model. Never raises."""
    from app.database import async_session
    from app.models.policy_document import PolicyDocument
    done = 0
    try:
        async with async_session() as db:
            if not await has_table(db):
                return 0
            ids = (await db.execute(text(
                "SELECT d.id FROM policy_documents d WHERE d.status = 'ready' AND d.is_current AND d.markdown IS NOT NULL "
                "AND d.index_tries < :t AND NOT EXISTS (SELECT 1 FROM doc_chunks c WHERE c.document_id = d.id "
                "AND c.model = :m) ORDER BY d.created_at DESC LIMIT :l"),
                {"t": MAX_TRIES, "m": model_name(), "l": limit})).scalars().all()
            for did in ids:
                doc = await db.get(PolicyDocument, did)
                doc.index_tries = (doc.index_tries or 0) + 1
                await db.commit()
                if await index_safely(db, doc):
                    done += 1
    except Exception:  # noqa: BLE001
        logger.exception("policies: sweep failed")
    return done
