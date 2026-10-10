"""Customer product history — snapshot every production upload's rows by reporting month
(models/customer_snapshot). Written after each production ingest and by a daily safety-net job that
also backfills uploads it hasn't seen; read by the Nifra tools (customer_changes, production_changes).

Idempotent: a month is upserted from whichever production file reports it; a later file for the same
month overwrites the figures. Never deletes — the point is to outlive replaced files."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer_snapshot import CustomerProductSnapshot as S, CustomerSnapshotUpload as Done
from app.models.record import ClientRecord
from app.models.upload import FileUpload

logger = logging.getLogger(__name__)


def _s(v, n: int) -> str:
    return (str(v).strip()[:n]) if v not in (None, "") else ""


async def snapshot_upload(db: AsyncSession, upload_id: uuid.UUID, *, commit: bool = True) -> int:
    """Upsert one production upload's rows into the month it reports (upload.period_month)."""
    up = await db.get(FileUpload, upload_id)
    if not up or up.file_category != "production" or not up.period_month:
        return 0
    month = up.period_month.replace(day=1)
    recs = (await db.execute(select(ClientRecord).where(ClientRecord.upload_id == up.id,
                                                        ClientRecord.id_number.isnot(None)))).scalars().all()
    rows: dict[tuple, dict] = {}
    now = datetime.utcnow()
    for r in recs:
        idn = str(r.id_number).strip().lstrip("0")
        if not idn:
            continue
        row = {"id": uuid.uuid4(), "user_id": up.user_id, "period_month": month, "customer_id_number": idn[:20],
               "customer_name": _s(" ".join(x for x in (r.first_name, r.last_name) if x), 200) or None,
               "company": _s(r.receiving_company, 160), "product_type": _s(r.product_type, 160),
               "product": _s(r.product, 200) or None, "policy_number": _s(r.fund_policy_number, 60),
               "track": _s(r.track, 200), "status": _s(r.product_status, 80) or None,
               "accumulation": r.accumulation, "premium": r.total_premium, "source_upload_id": up.id, "captured_at": now}
        k = (idn, row["company"], row["policy_number"], row["product_type"], row["track"])
        prev = rows.get(k)
        if prev:   # the same product twice in one file (coverages) — sum, don't lose either
            for f in ("accumulation", "premium"):
                if row[f] is not None:
                    prev[f] = (prev[f] or 0) + row[f]
        else:
            rows[k] = row
    vals = list(rows.values())
    for i in range(0, len(vals), 500):
        stmt = insert(S).values(vals[i: i + 500])
        upd = {c: getattr(stmt.excluded, c) for c in ("customer_name", "product", "status", "accumulation", "premium",
                                                       "source_upload_id", "captured_at")}
        await db.execute(stmt.on_conflict_do_update(constraint="uq_customer_product_month", set_=upd))
    mark = insert(Done).values(upload_id=up.id, rows=len(vals), captured_at=now)
    await db.execute(mark.on_conflict_do_update(index_elements=["upload_id"], set_={"rows": len(vals), "captured_at": now}))
    if commit:
        await db.commit()
    return len(vals)


async def sweep(db: AsyncSession) -> dict:
    """Snapshot every production upload (any user, active or not) not yet captured."""
    done = set((await db.execute(select(Done.upload_id))).scalars())
    ups = (await db.execute(select(FileUpload.id).where(FileUpload.file_category == "production",
                                                        FileUpload.period_month.isnot(None))
                            .order_by(FileUpload.period_month, FileUpload.uploaded_at))).scalars().all()
    stats = {"uploads": 0, "rows": 0}
    for uid in ups:
        if uid in done:
            continue
        try:
            n = await snapshot_upload(db, uid)
            stats["uploads"] += 1
            stats["rows"] += n
        except Exception as e:  # noqa: BLE001 — one bad file never stops the others
            await db.rollback()
            logger.warning("customer history: upload %s failed: %s", uid, e)
    logger.info("customer history sweep: %s", stats)
    return stats


async def months(db: AsyncSession, user_id) -> list:
    return list((await db.execute(select(S.period_month).where(S.user_id == user_id).distinct()
                                  .order_by(S.period_month))).scalars())


async def customer_timeline(db: AsyncSession, user_id, idn: str) -> list[dict]:
    """Every product of one customer → its balance per month."""
    rows = (await db.execute(select(S).where(S.user_id == user_id, S.customer_id_number == idn.lstrip("0"))
                             .order_by(S.period_month))).scalars().all()
    by: dict[tuple, dict] = {}
    for r in rows:
        k = (r.company, r.policy_number, r.product_type, r.track)
        d = by.setdefault(k, {"company": r.company, "product": r.product or r.product_type, "policy": r.policy_number or None,
                              "track": r.track or None, "months": []})
        d["months"].append({"month": r.period_month.strftime("%m/%Y"), "accumulation": float(r.accumulation) if r.accumulation is not None else None,
                            "status": r.status})
    return list(by.values())


FAMILIES = (("סיעוד", "nursing"), ("בריאות", "health"), ("מנהלים", "managers"), ("פוליסת חיסכון", "savings_policy"),
            ("חיסכון טהור", "savings_policy"), ("חיים", "life"), ("ריסק", "life"), ("משכנתא", "life"),
            ("גמל", "savings"), ("השתלמות", "savings"), ("פנסי", "savings"), ("מגוון", "savings"))
MIN_COVERAGE = 0.6
MIN_OVERLAP = 0.5


def family(product_type: str | None) -> str:
    t = product_type or ""
    return next((f for k, f in FAMILIES if k in t), "other")


async def book_changes(db: AsyncSession, user_id) -> dict:
    """Latest month vs the month before, like for like: per (company, product family) present in BOTH
    months with similar coverage (customer counts within MIN_COVERAGE of each other). July's full
    "products under management" file vs September's merged automation file listed Phoenix Excellence
    savings 221 → 1 customers — "220 left" was a partial file, not leavers (2026-10-10)."""
    ms = await months(db, user_id)
    if len(ms) < 2:
        return {"months": [m.strftime("%m/%Y") for m in ms], "companies": []}
    cur, prev = ms[-1], ms[-2]

    async def side(m):
        q = select(S.company, S.product_type, S.customer_id_number, S.customer_name, S.accumulation).where(
            S.user_id == user_id, S.period_month == m)
        out: dict[tuple, dict] = {}
        for co, pt, idn, nm, acc in (await db.execute(q)).all():
            d = out.setdefault((co or "—", family(pt)), {})
            prev_nm, prev_acc = d.get(idn, (None, 0.0))
            d[idn] = (nm or prev_nm, prev_acc + float(acc or 0))
        return out
    a, b = await side(cur), await side(prev)
    comps, not_comparable = [], []
    for key in sorted(set(a) | set(b)):
        ca, cb = a.get(key, {}), b.get(key, {})
        co, fam = key
        overlap = len(set(ca) & set(cb)) / (min(len(ca), len(cb)) or 1)
        # similar size AND mostly the same people — two files of different scope (Menora life: 50 "new", 48
        # "left" out of ~100) are not churn
        if not ca or not cb or min(len(ca), len(cb)) < MIN_COVERAGE * max(len(ca), len(cb)) or overlap < MIN_OVERLAP:
            not_comparable.append({"company": co, "family": fam, "customers_now": len(ca), "customers_before": len(cb)})
            continue
        new, gone = set(ca) - set(cb), set(cb) - set(ca)
        comps.append({"company": co, "family": fam, "new": len(new), "left": len(gone),
                      "accumulation_now": round(sum(v[1] for v in ca.values())), "accumulation_before": round(sum(v[1] for v in cb.values())),
                      "new_names": [ca[i][0] or i for i in list(new)[:8]], "left_names": [cb[i][0] or i for i in list(gone)[:8]]})
    return {"current": cur.strftime("%m/%Y"), "previous": prev.strftime("%m/%Y"), "companies": comps,
            "not_comparable": not_comparable,
            "rule": "משווים רק חברה + סוג מוצר שמופיעים בשני החודשים בכיסוי דומה. אחרת — הקובץ חלקי או מסוג אחר, לא עזיבה."}
