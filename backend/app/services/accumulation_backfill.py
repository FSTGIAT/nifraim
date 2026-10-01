"""Fill a production policy's ₪0 צבירה from the same company's נפרעים.

Why this exists (QA 2026-09-30, kikohib): the clearinghouse "מוצרים בניהול"
production report carried ₪0 accumulation for 29 legacy אינטרגמל policies that
Mor now runs as "אלפא מור תגמולים" — while Mor's own נפרעים for the SAME month
reported ₪6.62M on the SAME policy numbers. The distribution chart showed מור at
₪90.6M; the agent's book is ~₪97M.

The rule is deliberately narrow, so nothing is guessed:
  · the production row reports 0 / no accumulation, and is not pure-risk
    insurance (whose נפרעים "צבירה" is not a balance the agent manages);
  · a נפרעים row of the SAME company (brand stem), for the SAME period, on the
    SAME policy (core number) for the SAME client ID reports a balance > 0;
  · the policy has exactly one production row (a pension split into מקיפה /
    כללית can't be told apart from one number).

Filled rows carry ``accumulation_source = 'nifraim'``. Every run first reverts
earlier fills to 0 and then re-derives them, so a נפרעים file that is replaced or
deleted never leaves a stale balance behind. Generic — no company or user is
special-cased.
"""
from __future__ import annotations

import logging
import uuid
from collections import defaultdict

from sqlalchemy import select, update

from app.models.record import ClientRecord
from app.models.upload import FileUpload
from app.services.comparison_service import _extract_policy_core
from app.services.rate_select import pure_risk_insurance
from app.utils.company_norm import company_stem

logger = logging.getLogger(__name__)

SOURCE_NIFRAIM = "nifraim"


def _policy_key(policy) -> str | None:
    s = str(policy or "").strip()
    if s.endswith(".0"):
        s = s[:-2]
    s = (_extract_policy_core(s) or "").lstrip("0")
    return s or None


def _id_key(id_number) -> str:
    return str(id_number or "").strip().lstrip("0")


async def backfill_zero_accumulation(db, user_id: uuid.UUID) -> dict:
    """Re-derive every נפרעים-sourced accumulation for this user's ACTIVE
    production. Returns {"filled": n, "amount": ₪}. Commits."""
    prod_uploads = (await db.execute(select(FileUpload).where(
        FileUpload.user_id == user_id,
        FileUpload.is_production.is_(True),
    ))).scalars().all()
    if not prod_uploads:
        return {"filled": 0, "amount": 0.0}
    prod_ids = [u.id for u in prod_uploads]

    # 1. Undo earlier fills — the answer is recomputed from scratch below.
    await db.execute(
        update(ClientRecord)
        .where(ClientRecord.upload_id.in_(prod_ids),
               ClientRecord.accumulation_source == SOURCE_NIFRAIM)
        .values(accumulation=0, accumulation_source=None)
    )

    periods = {u.period_month for u in prod_uploads if u.period_month}
    comm_uploads = []
    if periods:
        comm_uploads = (await db.execute(select(FileUpload).where(
            FileUpload.user_id == user_id,
            FileUpload.is_production.is_(False),
            FileUpload.file_category == "commission",
            FileUpload.period_month.in_(periods),
        ))).scalars().all()
    if not comm_uploads:
        await db.commit()
        return {"filled": 0, "amount": 0.0}
    comm_period = {u.id: u.period_month for u in comm_uploads}

    # 2. נפרעים balances by (period, company, policy, client). Several rows for
    #    one key (a merged file plus a single-company file of the same month)
    #    are the same balance twice, so the LARGEST is kept — never a sum.
    balances: dict[tuple, float] = {}
    for r in (await db.execute(select(
        ClientRecord.upload_id, ClientRecord.receiving_company,
        ClientRecord.fund_policy_number, ClientRecord.id_number,
        ClientRecord.accumulation,
    ).where(ClientRecord.upload_id.in_(list(comm_period))))).all():
        acc = float(r.accumulation or 0)
        pol = _policy_key(r.fund_policy_number)
        stem = company_stem(r.receiving_company)
        if acc <= 0 or not pol or not stem:
            continue
        key = (comm_period[r.upload_id], stem, pol, _id_key(r.id_number))
        balances[key] = max(balances.get(key, 0.0), acc)
    if not balances:
        await db.commit()
        return {"filled": 0, "amount": 0.0}

    # 3. Production rows that report nothing, one row per policy only.
    prod_period = {u.id: u.period_month for u in prod_uploads}
    rows = (await db.execute(select(
        ClientRecord.id, ClientRecord.upload_id, ClientRecord.receiving_company,
        ClientRecord.fund_policy_number, ClientRecord.id_number,
        ClientRecord.accumulation, ClientRecord.product_type, ClientRecord.fund_type,
    ).where(ClientRecord.upload_id.in_(prod_ids)))).all()
    per_policy = defaultdict(list)
    for r in rows:
        pol = _policy_key(r.fund_policy_number)
        if pol:
            per_policy[(r.upload_id, company_stem(r.receiving_company), pol)].append(r)

    filled = 0
    amount = 0.0
    for (upload_id, stem, pol), recs in per_policy.items():
        if len(recs) != 1:
            continue
        r = recs[0]
        if float(r.accumulation or 0) > 0 or pure_risk_insurance(r.fund_type or r.product_type):
            continue
        bal = balances.get((prod_period[upload_id], stem, pol, _id_key(r.id_number)))
        if not bal:
            continue
        await db.execute(
            update(ClientRecord).where(ClientRecord.id == r.id)
            .values(accumulation=round(bal, 2), accumulation_source=SOURCE_NIFRAIM)
        )
        filled += 1
        amount += bal

    await db.commit()
    if filled:
        logger.info("accumulation backfill user=%s: %d policies, ₪%.0f from נפרעים",
                    user_id, filled, amount)
    return {"filled": filled, "amount": round(amount, 2)}
