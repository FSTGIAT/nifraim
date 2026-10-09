"""Month-over-month delta of the מסלקה production snapshots.

Every 2000/2100 answer is stored as holdings stamped with the file's
`status_date` (תאריך נכונות), one row per product per date. A month's delta is
that snapshot against the one before it; the first snapshot is compared with the
agent's production file instead, so there is a delta from day one.

Computed on read from the stored snapshots, so nothing extra is saved and the
answer always agrees with the data.

Rules (2026-10-09):
  * Only production answers (2000/2100) count as a monthly snapshot. A 9100 is
    one customer's check and would make the next month look ~all "new".
  * A company is compared only when it has data on BOTH sides. Otherwise a body
    whose next file hasn't arrived yet would show every product as "removed".
    Against production, a company is "on both sides" when at least one of its
    production rows matches a מסלקה product. Production calls Phoenix
    `הפניקס אקסלנס…` and the מסלקה calls it `הפניקס פנסיה…`, so names can't be
    compared.
  * A product = customer (no leading zeros) + policy (no leading zeros), plus the
    company between two מסלקה snapshots.
  * "Changed" needs a value on both sides: Phoenix gemel rows carry no צבירה
    while production has 0.00, and that is not a change.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pension_holding import PensionHolding
from app.models.pension_inquiry import PensionInquiry
from app.models.record import ClientRecord
from app.models.upload import FileUpload

PRODUCTION_CODES = ("events_v007:2000", "events_v007:2100")
MIN_ABS_CHANGE = 100.0       # ₪ — below this a balance is "unchanged"
MIN_REL_CHANGE = 0.01        # 1%


def _cid(v) -> str:
    return (str(v or "").strip()).lstrip("0")


def _pol(v) -> str:
    v = str(v or "").strip()
    return v.lstrip("0") or v


def _num(v) -> float | None:
    return None if v is None else float(v)


def _changed(old: float | None, new: float | None) -> bool:
    if old is None or new is None:
        return False
    d = abs(new - old)
    return d >= MIN_ABS_CHANGE and d >= MIN_REL_CHANGE * max(abs(old), abs(new))


async def snapshot_dates(db: AsyncSession, user_id: uuid.UUID) -> list[date]:
    """The valuation dates of the agent's production snapshots, newest first."""
    rows = (await db.execute(
        select(PensionHolding.status_date)
        .join(PensionInquiry, PensionInquiry.id == PensionHolding.inquiry_id)
        .where(PensionHolding.user_id == user_id,
               PensionHolding.status_date.is_not(None),
               PensionInquiry.interface_code.in_(PRODUCTION_CODES))
        .distinct()
    )).scalars().all()
    return sorted(rows, reverse=True)


async def _snapshot(db: AsyncSession, user_id: uuid.UUID, d: date) -> list[PensionHolding]:
    return (await db.execute(
        select(PensionHolding)
        .join(PensionInquiry, PensionInquiry.id == PensionHolding.inquiry_id)
        .where(PensionHolding.user_id == user_id,
               PensionHolding.status_date == d,
               PensionInquiry.interface_code.in_(PRODUCTION_CODES))
    )).scalars().all()


async def _names(db: AsyncSession, user_id: uuid.UUID, ids: set[str]) -> dict[str, str]:
    """Holdings carry no names; the agent's own records do."""
    if not ids:
        return {}
    out: dict[str, str] = {}
    for idn, first, last in (await db.execute(
        select(func.ltrim(ClientRecord.id_number, "0"), ClientRecord.first_name, ClientRecord.last_name)
        .where(ClientRecord.user_id == user_id, func.ltrim(ClientRecord.id_number, "0").in_(ids))
    )).all():
        name = " ".join(x for x in (first, last) if x)
        if name and idn not in out:
            out[idn] = name
    return out


async def _baseline_production(db: AsyncSession, user_id: uuid.UUID):
    """The agent's current production file: the newest production upload by
    reporting month (then upload time). None when there is none."""
    return (await db.execute(
        select(FileUpload)
        .where(FileUpload.user_id == user_id, FileUpload.is_production == True)  # noqa: E712
        .order_by(FileUpload.period_month.desc().nulls_last(), FileUpload.uploaded_at.desc())
        .limit(1)
    )).scalars().first()


def _item(key, *, company, product, policy, old=None, new=None, old_premium=None, new_premium=None):
    return {
        "id_number": key[0], "company": company, "product": product, "policy": policy,
        "old_accumulation": old, "new_accumulation": new,
        "accumulation_diff": (round(new - old, 2) if old is not None and new is not None else None),
        "old_premium": old_premium, "new_premium": new_premium,
    }


def _group(rows, key) -> dict:
    out: dict = defaultdict(list)
    for r in rows:
        out[key(r)].append(r)
    return out


def _pair(cur: list, base: list, *, cur_status, base_status, base_acc):
    """Pair the accounts of one product (customer + policy) across two sides.
    One saver can hold several accounts under one number (Altshuler 305392110:
    an inactive ₪10,670 and an active ₪763,295). Same status first, then the
    closest balance; what is left over is new (cur) or removed (base)."""
    cur, base, pairs = list(cur), list(base), []
    for c in list(cur):
        st = cur_status(c)
        if not st:
            continue
        b = next((b for b in base if base_status(b) == st), None)
        if b is not None:
            pairs.append((c, b)); cur.remove(c); base.remove(b)
    while cur and base:
        c, b = min(((c, b) for c in cur for b in base),
                   key=lambda cb: abs(float(cb[0].accumulation or 0) - float(base_acc(cb[1]) or 0)))
        pairs.append((c, b)); cur.remove(c); base.remove(b)
    return pairs, cur, base


async def monthly_delta(db: AsyncSession, user_id: uuid.UUID, as_of: date | None = None) -> dict:
    """The delta of one snapshot (default: the newest) against the one before it,
    or against the production file when it is the first."""
    dates = await snapshot_dates(db, user_id)
    if not dates:
        return {"as_of": None, "snapshots": [], "base": None,
                "summary": None, "new": [], "removed": [], "changed": []}
    as_of = as_of if as_of in dates else dates[0]
    prev = next((d for d in dates if d < as_of), None)

    cur_rows = await _snapshot(db, user_id, as_of)
    new_items, removed_items, changed_items, unchanged = [], [], [], 0
    companies: dict[str, dict] = defaultdict(lambda: {"new": 0, "removed": 0, "changed": 0, "unchanged": 0})

    def add(bucket, item, co):
        {"new": new_items, "removed": removed_items, "changed": changed_items}[bucket].append(item)
        companies[co][bucket] += 1

    if prev is not None:
        # מסלקה vs מסלקה: same source, so the company name is part of the key.
        base_rows = await _snapshot(db, user_id, prev)
        both = {h.receiving_company or "" for h in cur_rows} & {h.receiving_company or "" for h in base_rows}
        base_info = {"kind": "maslaka", "as_of": prev.isoformat()}
        key = lambda h: (_cid(h.customer_id_number), _pol(h.fund_policy_number), h.receiving_company or "")
        cur_g, base_g = _group([h for h in cur_rows if (h.receiving_company or "") in both], key), \
            _group([h for h in base_rows if (h.receiving_company or "") in both], key)
        for k in set(cur_g) | set(base_g):
            pairs, cur_left, base_left = _pair(cur_g.get(k, []), base_g.get(k, []),
                                               cur_status=lambda h: h.account_status,
                                               base_status=lambda b: b.account_status,
                                               base_acc=lambda b: b.accumulation)
            for h, b in pairs:
                item = _item(k, company=h.receiving_company, product=h.product or h.product_type,
                             policy=h.fund_policy_number, old=_num(b.accumulation), new=_num(h.accumulation),
                             old_premium=_num(b.total_premium), new_premium=_num(h.total_premium))
                if _changed(item["old_accumulation"], item["new_accumulation"]) or \
                        _changed(item["old_premium"], item["new_premium"]):
                    add("changed", item, k[2])
                else:
                    unchanged += 1; companies[k[2]]["unchanged"] += 1
            for h in cur_left:
                add("new", _item(k, company=h.receiving_company, product=h.product or h.product_type,
                                 policy=h.fund_policy_number, new=_num(h.accumulation),
                                 new_premium=_num(h.total_premium)), k[2])
            for b in base_left:
                add("removed", _item(k, company=b.receiving_company, product=b.product or b.product_type,
                                     policy=b.fund_policy_number, old=_num(b.accumulation)), k[2])
    else:
        # First snapshot: against the agent's production file.
        up = await _baseline_production(db, user_id)
        base_info = {"kind": "production", "as_of": up.period_month.isoformat() if up and up.period_month else None,
                     "filename": up.filename if up else None}
        prod_rows = [] if up is None else (await db.execute(
            select(ClientRecord).where(ClientRecord.user_id == user_id, ClientRecord.upload_id == up.id)
        )).scalars().all()
        pkey = lambda x, cid, pol: (_cid(cid), _pol(pol))
        prod_g = _group([r for r in prod_rows if _cid(r.id_number) and _pol(r.fund_policy_number)],
                        lambda r: pkey(r, r.id_number, r.fund_policy_number))
        cur_g = _group(cur_rows, lambda h: pkey(h, h.customer_id_number, h.fund_policy_number))
        # What the מסלקה answered for, in production's terms = (production company,
        # product type). Each מסלקה company maps to the production company most of
        # its products match (Phoenix → Phoenix Excellence); a stray cross-company
        # match (one Mor policy number on a Menora row) doesn't make Menora
        # "answered". The product type matters because production lists all of
        # Altshuler under one company while the מסלקה answered its pension only.
        pair_n: dict[tuple, int] = defaultdict(int)
        for k, hs in cur_g.items():
            for r in prod_g.get(k, [])[:1]:
                pair_n[(hs[0].receiving_company or "", r.receiving_company)] += 1
        maps_to: dict[str, str] = {}
        for (hco, pco), n in sorted(pair_n.items(), key=lambda kv: -kv[1]):
            maps_to.setdefault(hco, pco)
        answered = {(r.receiving_company, r.product_type) for k, hs in cur_g.items() for r in prod_g.get(k, [])
                    if maps_to.get(hs[0].receiving_company or "") == r.receiving_company}
        shown_as = {pco: hco for hco, pco in maps_to.items()}   # one name per company in the summary
        for k in set(cur_g) | set(prod_g):
            base_list = [r for r in prod_g.get(k, []) if (r.receiving_company, r.product_type) in answered] \
                if k not in cur_g else prod_g.get(k, [])
            # production's status words don't match the מסלקה's codes: pair by balance only
            pairs, cur_left, base_left = _pair(cur_g.get(k, []), base_list,
                                               cur_status=lambda h: None, base_status=lambda r: None,
                                               base_acc=lambda r: r.accumulation)
            for h, r in pairs:
                co = h.receiving_company or ""
                item = _item(k, company=co, product=h.product or h.product_type, policy=h.fund_policy_number,
                             old=_num(r.accumulation), new=_num(h.accumulation), new_premium=_num(h.total_premium))
                if _changed(item["old_accumulation"], item["new_accumulation"]):
                    add("changed", item, co)
                else:
                    unchanged += 1; companies[co]["unchanged"] += 1
            for h in cur_left:
                co = h.receiving_company or ""
                add("new", _item(k, company=co, product=h.product or h.product_type, policy=h.fund_policy_number,
                                 new=_num(h.accumulation), new_premium=_num(h.total_premium)), co)
            for r in base_left:
                co = shown_as.get(r.receiving_company, r.receiving_company)
                add("removed", _item(k, company=co, product=r.product or r.product_type,
                                     policy=r.fund_policy_number, old=_num(r.accumulation)), co)

    names = await _names(db, user_id, {i["id_number"] for i in new_items + removed_items + changed_items})
    for i in new_items + removed_items + changed_items:
        i["name"] = names.get(i["id_number"])
    changed_items.sort(key=lambda i: abs(i["accumulation_diff"] or 0), reverse=True)
    new_items.sort(key=lambda i: -(i["new_accumulation"] or 0))
    removed_items.sort(key=lambda i: -(i["old_accumulation"] or 0))

    def total(items, field):
        return round(sum(i[field] or 0 for i in items), 2)

    return {
        "as_of": as_of.isoformat(),
        "snapshots": [d.isoformat() for d in dates],
        "base": base_info,
        "summary": {
            "new_count": len(new_items), "removed_count": len(removed_items),
            "changed_count": len(changed_items), "unchanged_count": unchanged,
            "new_accumulation": total(new_items, "new_accumulation"),
            "removed_accumulation": total(removed_items, "old_accumulation"),
            "changed_accumulation_diff": total(changed_items, "accumulation_diff"),
        },
        "by_company": [{"company": c, **v} for c, v in sorted(companies.items(), key=lambda kv: -sum(kv[1].values()))],
        "new": new_items, "removed": removed_items, "changed": changed_items,
    }


def latest_per_company(holdings: list[PensionHolding]) -> list[PensionHolding]:
    """One customer's holdings, keeping only each company's newest valuation date.
    Monthly snapshots are kept side by side; summing all of them would count a
    product once per month."""
    newest: dict[str, date | None] = {}
    for h in holdings:
        co = h.receiving_company or ""
        d = h.status_date
        if co not in newest or (d is not None and (newest[co] is None or d > newest[co])):
            newest[co] = d
    return [h for h in holdings if h.status_date == newest.get(h.receiving_company or "")]
