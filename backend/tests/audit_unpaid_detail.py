"""Independent audit of every customer's "לא שולם" verdict against the raw files.

Usage (read-only; the DB session is READ ONLY):
    venv/bin/python tests/audit_unpaid_detail.py <user_id> [comparison_id]

Reads the saved comparison (newest, or the id given) and, WITHOUT using the
comparison's own matching code, re-checks it against the raw production rows of
the book it judged and the raw נפרעים rows of the same month:

  1. every product the UI lists as unpaid exists in that production book, with
     the same premium and balance (to the agora);
  2. no נפרעים row pays it: same customer, same company, commission > 0, and the
     same policy (or, for pension, any pension line of that customer there);
  3. every product listed as paid ("paid_production_products") has such a row;
  4. "לא שולם" (nothing paid) customers have no payment at any company, and
     "שולם חלקית" customers have at least one;
  5. every production customer at a company that sent נפרעים is in the
     comparison (none silently dropped).

Each disagreement is printed with the customer, the product and the evidence,
so it can be read as a finding, not a number.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import uuid
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402

from app.models.commission_comparison import CommissionComparison  # noqa: E402
from app.models.record import ClientRecord  # noqa: E402
from app.models.upload import FileUpload  # noqa: E402
from app.utils.company_norm import company_stem  # noqa: E402
# The product classifier only (what IS a pension product), not the matching.
from app.services.comparison_service import is_pension_record, received_money  # noqa: E402


def cid(v) -> str:
    return str(v or "").strip().split(".")[0].lstrip("0")


def pol_keys(v) -> set[str]:
    """Every digit run of 5+ in a policy, no leading zeros — a generous,
    independent notion of "the same account" (compound 'X-TRACK-ACCT-N' too)."""
    s = str(v or "").strip()
    if s.endswith(".0"):
        s = s[:-2]
    runs = {r.lstrip("0") for r in re.findall(r"\d{5,}", s)}
    return {r for r in runs if r}


def paid_amount(r: ClientRecord) -> float:
    # The user's rule (2026-10-10): net exactly 0 beside a positive gross = the gross.
    if r.commission_paid is not None and float(r.commission_paid) == 0 and (r.commission_before_fee or 0) > 0:
        return float(r.commission_before_fee)
    for f in (r.commission_paid, r.commission_before_fee, r.actual_amount):
        if f is not None:
            return float(f)
    return 0.0


def is_pension(product, product_type) -> bool:
    return bool(is_pension_record(product, product_type))


async def main(user_id: str, comparison_id: str | None) -> int:
    dsn = os.environ.get("AUDIT_DSN") or os.environ["DATABASE_URL"]
    eng = create_async_engine(dsn)
    problems: list[str] = []
    async with AsyncSession(eng) as db:
        await db.execute(text("SET TRANSACTION READ ONLY"))
        q = select(CommissionComparison).where(CommissionComparison.user_id == uuid.UUID(user_id))
        q = q.where(CommissionComparison.id == uuid.UUID(comparison_id)) if comparison_id else \
            q.order_by(CommissionComparison.computed_at.desc()).limit(1)
        row = (await db.execute(q)).scalars().first()
        rj = row.result_json if isinstance(row.result_json, dict) else json.loads(row.result_json)
        if os.environ.get("AUDIT_JSON"):
            # A recomputed (unsaved) result, e.g. from a rolled-back dry run.
            rj = json.loads(Path(os.environ["AUDIT_JSON"]).read_text(encoding="utf-8"))
        customers = rj["customers"]

        prod_rows = (await db.execute(select(ClientRecord).where(
            ClientRecord.upload_id == row.production_upload_id))).scalars().all()
        prod_up = await db.get(FileUpload, row.production_upload_id)
        # The נפרעים of the judged month: the newest merged file plus newer
        # per-company files, exactly the uploads the comparison names as sources.
        sources = set(rj.get("commission_company_sources") or [])
        comm_ups = (await db.execute(select(FileUpload).where(
            FileUpload.user_id == uuid.UUID(user_id), FileUpload.file_category == "commission",
        ).order_by(FileUpload.uploaded_at.desc()))).scalars().all()
        merged = next((u for u in comm_ups if (u.company_source or "") == "מאוחד"), None)
        comm_rows = (await db.execute(select(ClientRecord).where(
            ClientRecord.upload_id == merged.id))).scalars().all() if merged else []
        comm_rows = [r for r in comm_rows if not sources or r.receiving_company in sources]

    await eng.dispose()

    covered = {company_stem(r.receiving_company) for r in comm_rows} - {""}
    pay = defaultdict(list)          # (customer, company stem) → paying rows
    pension_line_stems = set()       # companies whose נפרעים name pension at all
    for r in comm_rows:
        if is_pension(r.product, r.fund_type):
            pension_line_stems.add(company_stem(r.receiving_company))
        if paid_amount(r) > 0:
            pay[(cid(r.id_number), company_stem(r.receiving_company))].append(r)
    paid_any = {k[0] for k in pay}

    prod_by = defaultdict(list)       # (customer, stem) → production rows
    for r in prod_rows:
        prod_by[(cid(r.id_number), company_stem(r.receiving_company))].append(r)

    def payment_for(c: str, p: dict, owners: list[str]) -> ClientRecord | None:
        """The documented rule (memory unpaid_per_product): a product with a real
        policy is paid by money on THAT policy; a product without one (pension
        carries the member's ID) is judged by family — paid by money on a pension
        line when the company's נפרעים name pension, else by any money there."""
        stem = company_stem(p.get("company_full") or p.get("company") or "")
        keys = pol_keys(p.get("policy_number"))
        real_policy = bool(keys) and keys != {c}
        pension = is_pension(p.get("product"), p.get("product_type"))
        for who in [c, *owners]:
            for r in pay.get((who, stem), []):
                if real_policy:
                    if keys & pol_keys(r.fund_policy_number):
                        return r
                elif pension and stem in pension_line_stems:
                    if is_pension(r.product, r.fund_type):
                        return r
                else:
                    return r
        return None

    def in_book(c: str, p: dict) -> ClientRecord | None:
        stem = company_stem(p.get("company_full") or p.get("company") or "")
        keys = pol_keys(p.get("policy_number"))
        for r in prod_by.get((c, stem), []):
            if (not keys and not pol_keys(r.fund_policy_number)) or keys & pol_keys(r.fund_policy_number):
                return r
        return None

    counts = defaultdict(int)
    seen_customers = set()
    for cu in customers:
        c = cid(cu.get("id_number"))
        seen_customers.add(c)
        owners = [cid(o) for v in cu.get("paid_via") or []
                  for o in (v.get("paid_via_ids") or [v.get("paid_via_id")]) if o]
        st = cu.get("match_status")
        if st != "only_production":
            continue
        partial = received_money(cu)     # what the UI shows since 2026-10-10
        counts["partial" if partial else "full"] += 1
        name = f'{cu.get("first_name") or ""} {cu.get("last_name") or ""}'.strip()
        for p in cu.get("production_products") or []:
            counts["unpaid_products"] += 1
            src = in_book(c, p)
            if src is None:
                problems.append(f"NOT IN BOOK  {c} {name}: {p.get('company')} {p.get('product')} policy {p.get('policy_number')}")
            else:
                for k_ui, k_db in (("premium", "total_premium"), ("accumulation", "accumulation")):
                    ui = float(p.get(k_ui) or 0)
                    same = [float(getattr(r, k_db) or 0) for r in prod_by[(c, company_stem(src.receiving_company))]
                            if pol_keys(r.fund_policy_number) & pol_keys(p.get("policy_number"))
                            or not pol_keys(p.get("policy_number"))]
                    if same and all(abs(ui - v) > 0.01 for v in same) and abs(ui - sum(same)) > 0.01:
                        problems.append(f"AMOUNT       {c} {name}: {p.get('company')} {p.get('product')} {k_ui} shown {ui:,.2f}, book {same}")
            r = payment_for(c, p, owners)
            if r is not None:
                problems.append(
                    f"PAID?        {c} {name}: {p.get('company')} {p.get('product')} policy {p.get('policy_number')} "
                    f"shown unpaid, but נפרעים has {paid_amount(r):,.2f} on {r.product or r.product_type} policy {r.fund_policy_number}")
        for p in cu.get("paid_production_products") or []:
            if payment_for(c, p, owners) is None:
                problems.append(f"NO PAYMENT   {c} {name}: {p.get('company')} {p.get('product')} policy {p.get('policy_number')} shown paid")
        got_money = c in paid_any or any(o in paid_any for o in owners)
        if not partial and got_money:
            stems = sorted(s for (who, s) in pay if who == c)
            problems.append(f"FULL BUT PAID {c} {name}: listed 'לא שולם' but נפרעים pays at {stems}")
        if partial and not got_money:
            problems.append(f"PARTIAL NO MONEY {c} {name}: 'שולם חלקית' but no money arrived")

    nv = {cid(c.get("id_number")) for c in rj.get("no_value_customers") or []}
    for (c, stem), rows in prod_by.items():
        if stem in covered and c not in seen_customers and c not in nv:
            problems.append(f"DROPPED      {c}: {len(rows)} production rows at {stem} missing from the comparison")

    print(f"comparison {row.id} computed {row.computed_at}  production: {prod_up.filename} ({prod_up.period_month})"
          f"  נפרעים: {merged.filename if merged else None} ({merged.period_month if merged else None})")
    print(f"customers {len(customers)} · לא שולם {counts['full']} · שולם חלקית {counts['partial']}"
          f" · unpaid products checked {counts['unpaid_products']}")
    kinds = defaultdict(int)
    for p in problems:
        kinds[p.split()[0]] += 1
    print("findings:", dict(kinds) or "none")
    for p in problems:
        print("  " + p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)))
