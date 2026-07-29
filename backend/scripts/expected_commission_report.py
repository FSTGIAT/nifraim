"""Before/after harness for the EXPECTED-commission math.

Why per-record and not per-total
--------------------------------
Changing rate selection legitimately moves totals (a company that used to fall
through to a median now gets a product match). A total-level "must not move"
assertion therefore can't distinguish the fix working from the fix breaking
something. This script emits ONE ROW PER RECORD so the two runs can be diffed
record by record:

  * records that matched the same way with the same rate  -> must be identical
  * records whose rate or match route changed             -> must each be
    attributable to stem-fallback or product-match, reviewed as a list

Usage
-----
    python scripts/expected_commission_report.py --out /tmp/before.jsonl
    ...apply the change...
    python scripts/expected_commission_report.py --out /tmp/after.jsonl
    python scripts/expected_commission_report.py --diff /tmp/before.jsonl /tmp/after.jsonl

Reads DATABASE_URL from the environment (falls back to app settings). Strictly
read-only — it opens a connection, SELECTs, and never writes.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncpg  # noqa: E402

from app.services.rate_select import (  # noqa: E402
    accumulation_based,
    expected_rate,
    make_pick_rate,
)


class _Rate:
    """Duck-type of a CommissionRate row — rate_select only reads attributes."""

    __slots__ = ("company_name", "product", "rate", "rate_kind")

    def __init__(self, company_name, product, rate, rate_kind):
        self.company_name = company_name
        self.product = product
        self.rate = rate
        self.rate_kind = rate_kind


def _db_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        try:
            from app.core.config import settings  # noqa: PLC0415

            url = getattr(settings, "DATABASE_URL", None) or getattr(settings, "database_url", None)
        except Exception:
            url = None
    if not url:
        raise SystemExit(
            "No DATABASE_URL. Export it, e.g.\n"
            "  export DATABASE_URL='postgresql://user:pw@host:port/db'"
        )
    # asyncpg wants a plain postgresql:// DSN, not SQLAlchemy's +asyncpg form.
    return url.replace("postgresql+asyncpg://", "postgresql://")


try:  # post-change build exposes the selector's own decision
    from app.services.rate_select import select_rate as _select_rate
except ImportError:  # pre-change build
    _select_rate = None


def _match_route(rates, company: str, product: str | None,
                 product_type: str | None = None, is_accum: bool = False) -> str:
    """HOW this rate was chosen.

    After the change this is the selector's own `route` ('exact:product',
    'stem:median', …) — the whole point of the harness is to attribute every
    moved number to a branch, and a company-tier-only label can't do that.
    Before the change the selector didn't exist, so fall back to the tier.
    """
    if _select_rate is not None:
        return _select_rate(rates, company, product, product_type, is_accum)[1]

    from app.utils.company_norm import normalize_company

    canon = normalize_company(company)
    if canon and any(
        r.company_name and normalize_company(r.company_name) == canon for r in rates
    ):
        return "exact"
    return "none"


async def collect(out_path: str | None) -> None:
    conn = await asyncpg.connect(_db_url())
    try:
        uploads = await conn.fetch(
            "select id, user_id, filename from file_uploads where is_production = true"
        )
        rows_out: list[dict] = []
        summary: list[dict] = []

        for up in uploads:
            rate_rows = await conn.fetch(
                "select company_name, product, rate, rate_kind "
                "from commission_rates where user_id = $1",
                up["user_id"],
            )
            rates = [
                _Rate(r["company_name"], r["product"], r["rate"], r["rate_kind"])
                for r in rate_rows
            ]
            recs = await conn.fetch(
                "select id, id_number, receiving_company, product, product_type, "
                "accumulation, total_premium from client_records where upload_id = $1",
                up["id"],
            )
            pick = make_pick_rate(rates)

            stats = defaultdict(int)
            total = 0.0
            for r in recs:
                company = r["receiving_company"]
                if not company:
                    stats["no_company"] += 1
                    continue
                accum = float(r["accumulation"] or 0)
                premium = float(r["total_premium"] or 0)
                is_accum = accumulation_based(r["product_type"], accum)
                rate = expected_rate(
                    rates, pick, company, r["product"], r["product_type"], is_accum
                )

                if rate <= 0:
                    exp, reason = 0.0, "no_rate"
                elif is_accum:
                    exp, reason = accum * rate / 12.0, "accum"
                elif premium > 0:
                    exp, reason = premium * rate, "premium"
                else:
                    exp, reason = 0.0, "no_base"

                stats[reason] += 1
                total += exp
                rows_out.append(
                    {
                        "upload": up["filename"],
                        "record_id": str(r["id"]),
                        "id_number": r["id_number"],
                        "company": company,
                        "product": r["product"],
                        "product_type": r["product_type"],
                        "basis": "accum" if is_accum else "premium",
                        "accum": round(accum, 2),
                        "premium": round(premium, 2),
                        "rate": round(float(rate), 6),
                        "route": _match_route(
                            rates, company, r["product"], r["product_type"], is_accum
                        ),
                        "reason": reason,
                        "expected": round(exp, 2),
                    }
                )

            summary.append(
                {
                    "upload": up["filename"],
                    "rate_rows": len(rates),
                    "records": len(recs),
                    "contributing": stats["accum"] + stats["premium"],
                    "no_rate": stats["no_rate"],
                    "no_base": stats["no_base"],
                    "expected_total": round(total, 2),
                }
            )

        hdr = f'{"upload":36} {"rates":>6} {"recs":>6} {"contrib":>8} {"no-rate":>8} {"no-base":>8} {"expected":>13}'
        print(hdr)
        print("-" * len(hdr))
        for s in summary:
            print(
                f'{s["upload"][:34]:36} {s["rate_rows"]:>6} {s["records"]:>6} '
                f'{s["contributing"]:>8} {s["no_rate"]:>8} {s["no_base"]:>8} '
                f'₪{s["expected_total"]:>12,.0f}'
            )

        if out_path:
            with open(out_path, "w", encoding="utf-8") as fh:
                for row in rows_out:
                    fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(f"\nwrote {len(rows_out)} per-record rows -> {out_path}")
    finally:
        await conn.close()


def diff(before_path: str, after_path: str) -> int:
    def load(p):
        with open(p, encoding="utf-8") as fh:
            return {json.loads(line)["record_id"]: json.loads(line) for line in fh if line.strip()}

    before, after = load(before_path), load(after_path)
    only_before = set(before) - set(after)
    only_after = set(after) - set(before)

    identical = changed = 0
    by_transition: dict[str, list[dict]] = defaultdict(list)
    for rid in set(before) & set(after):
        b, a = before[rid], after[rid]
        if b["rate"] == a["rate"] and b["reason"] == a["reason"]:
            identical += 1
            continue
        changed += 1
        by_transition[f'{b["route"]}/{b["reason"]} -> {a["route"]}/{a["reason"]}'].append(
            {"company": a["company"], "product": a["product"],
             "rate": f'{b["rate"]} -> {a["rate"]}',
             "expected": f'{b["expected"]} -> {a["expected"]}'}
        )

    print(f"records in both runs : {len(set(before) & set(after))}")
    print(f"  identical          : {identical}")
    print(f"  changed            : {changed}")
    if only_before or only_after:
        print(f"  only in before     : {len(only_before)}")
        print(f"  only in after      : {len(only_after)}")

    exp_b = sum(r["expected"] for r in before.values())
    exp_a = sum(r["expected"] for r in after.values())
    print(f"\nexpected total: ₪{exp_b:,.0f} -> ₪{exp_a:,.0f}  ({exp_a - exp_b:+,.0f})")

    if by_transition:
        print("\nchanges grouped by transition (route/reason):")
        for key, items in sorted(by_transition.items(), key=lambda kv: -len(kv[1])):
            print(f"\n  {key}   [{len(items)} records]")
            seen = set()
            for it in items:
                sig = (it["company"], it["product"], it["rate"])
                if sig in seen:
                    continue
                seen.add(sig)
                if len(seen) > 8:
                    print(f'      … and {len(items) - 8} more')
                    break
                print(f'      {str(it["company"])[:38]:40} {str(it["product"])[:26]:28} {it["rate"]}')

    # A regression is a record that CONTRIBUTED before and stopped contributing,
    # without its company/product changing — the fix must never take money away.
    regressions = [
        (before[rid], after[rid])
        for rid in set(before) & set(after)
        if before[rid]["expected"] > 0 and after[rid]["expected"] == 0
    ]
    if regressions:
        print(f"\n!! {len(regressions)} records STOPPED contributing — investigate:")
        for b, a in regressions[:10]:
            print(f'   {b["company"][:36]:38} {str(b["product"])[:24]:26} '
                  f'₪{b["expected"]:,.2f} -> 0  ({b["reason"]} -> {a["reason"]})')
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", help="write per-record JSONL snapshot here")
    ap.add_argument("--diff", nargs=2, metavar=("BEFORE", "AFTER"), help="diff two snapshots")
    args = ap.parse_args()

    if args.diff:
        return diff(*args.diff)
    asyncio.run(collect(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
