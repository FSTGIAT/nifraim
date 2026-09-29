"""Delete a TEST user and everything that hangs off them.

Only ever called for `users.is_test_user` (the admin route enforces it). The
users table is referenced by ~45 tables, most with NO ACTION foreign keys and
some with grandchildren (holdings → inquiries, records → uploads), so a plain
DELETE fails and a hand-written list goes stale with the next table. Instead
this reads the database's OWN foreign-key graph and deletes children before
parents, recursively, inside the caller's transaction — all or nothing.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_FK_SQL = text("""
SELECT cl.relname  AS child_table,
       att.attname AS child_col,
       pcl.relname AS parent_table,
       patt.attname AS parent_col
FROM pg_constraint con
JOIN pg_class cl   ON cl.oid = con.conrelid
JOIN pg_class pcl  ON pcl.oid = con.confrelid
JOIN pg_namespace ns ON ns.oid = cl.relnamespace
JOIN pg_attribute att  ON att.attrelid = con.conrelid  AND att.attnum = con.conkey[1]
JOIN pg_attribute patt ON patt.attrelid = con.confrelid AND patt.attnum = con.confkey[1]
WHERE con.contype = 'f' AND array_length(con.conkey, 1) = 1 AND ns.nspname = 'public'
""")

def _q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


async def purge_user(db: AsyncSession, user_id: uuid.UUID) -> dict[str, int]:
    """Delete the user and all dependent rows. Returns rows deleted per table.
    Does not commit — the caller commits (or rolls back on error).

    Two phases, because the FK graph has loops (e.g. holdings ↔ records), so a
    nested "children first" recursion never bottoms out:
      1. COLLECT — starting from the user row, follow every FK backwards and
         gather the physical rows (ctid) that depend on it, as sets, until no
         new rows appear.
      2. DELETE — repeatedly delete each table's collected rows inside a
         savepoint; a table still referenced by a not-yet-deleted row fails and
         is retried on the next pass. Stops when everything is gone, or raises
         when a pass makes no progress (a rollback then undoes it all).
    """
    fks: dict[str, list[tuple[str, str, str]]] = {}
    for child, ccol, parent, pcol in (await db.execute(_FK_SQL)).all():
        fks.setdefault(parent, []).append((child, ccol, pcol))

    rows: dict[str, set[str]] = {"users": set()}
    first = (await db.execute(
        text("SELECT ctid::text FROM users WHERE id = :uid"), {"uid": user_id})).scalars().all()
    if not first:
        return {}
    rows["users"].update(first)

    # 1. collect
    frontier: dict[str, set[str]] = {"users": set(first)}
    while frontier:
        nxt: dict[str, set[str]] = {}
        for table, ctids in frontier.items():
            for child, ccol, pcol in fks.get(table, []):
                found = (await db.execute(text(
                    f"SELECT c.ctid::text FROM {_q(child)} c "
                    f"WHERE c.{_q(ccol)} IN (SELECT p.{_q(pcol)} FROM {_q(table)} p "
                    f"WHERE p.ctid = ANY(CAST(:ids AS text[])::tid[]))"
                ), {"ids": list(ctids)})).scalars().all()
                new = set(found) - rows.setdefault(child, set())
                if new:
                    rows[child] |= new
                    nxt.setdefault(child, set()).update(new)
        frontier = nxt

    # 2. delete, retrying tables still referenced by rows not yet deleted
    counts: dict[str, int] = {}
    pending = {t: ids for t, ids in rows.items() if ids}
    while pending:
        progressed = False
        for table in list(pending):
            try:
                async with db.begin_nested():
                    res = await db.execute(
                        text(f"DELETE FROM {_q(table)} WHERE ctid = ANY(CAST(:ids AS text[])::tid[])"),
                        {"ids": list(pending[table])},
                    )
            except Exception:                                    # noqa: BLE001
                continue            # still referenced — try again next pass
            if res.rowcount:
                counts[table] = counts.get(table, 0) + res.rowcount
            del pending[table]
            progressed = True
        if not progressed:
            raise RuntimeError(f"could not delete rows in: {', '.join(sorted(pending))}")

    logger.info("test_user_purge: user %s removed: %s", user_id, counts)
    return counts
