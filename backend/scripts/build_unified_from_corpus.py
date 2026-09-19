#!/usr/bin/env python3
"""Build the TWO unified workbooks (production + נפרעים) from the local corpus.

This is the offline twin of what `batch_runner` does at the end of a
"הורדה אוטומטית מכל החברות" run: every per-company file the agent has on disk is
parsed, the freshest one per (insurer entity, category) is kept, and the two
merged workbooks are written with the very same builders the batch uses
(`aggregate.build_unified_workbook_bytes` / `build_unified_nifraim_bytes`) — so
the output is byte-for-byte the shape the app ingests, not a lookalike.

    backend/venv/bin/python backend/scripts/build_unified_from_corpus.py --dry-run
    backend/venv/bin/python backend/scripts/build_unified_from_corpus.py

Selection rule — NEWEST PER (insurer entity, category). The corpus holds many
repeat runs of the same report (five copies of `מגדל - ייצור (יוני 2026).xlsx`,
six of the Menora נפרעים zip); merging them all would multiply every number.
The entity key is `aggregate.merged_company_key`, the same function the
standalone fold uses, so 'מנורה' and 'מנורה מבטחים פנסיה וגמל בע"מ' collapse the
way the merged file itself spells them.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

OUT_DIR = ROOT.parent / "downloaded_unified"

# Files that parse as production/commission but are NOT insurer deliverables:
# hand-made test sheets and manual re-exports. They must never land in a file
# the agent reads as real money.
EXCLUDE_NAMES = {
    "בדיקה פרודוקציה מרץ 26.xlsx",   # literally "test"
    "production.xlsx",                # manual KIKO scratch export
    "migdal_production.xlsx",          # manual re-export of migdal_production.zip
}

# A run folder often holds BOTH the raw download and the artifact the plugin
# derived from it. Re-parsing the RAW one is the point of this exercise: the
# derived file froze whatever parser was deployed the day of that run, so it
# carries that day's bugs forever. Live proof: `מגדל - ייצור (יוני 2026).xlsx`
# on disk has 121 rows and accumulation 0, while re-merging its own
# `migdal_*.zip` through today's code gives 109 rows carrying ₪1,705,423 — the
# artifact predates `fix(mimshak): accumulation dropped every balance component`.
#
# (key = glob for the derived artifact, value = glob for the raw source that
# must be present in the same folder for the artifact to be dropped)
DERIVED_ARTIFACTS = [
    ("מגדל - ייצור*.xlsx", "*.zip"),
    ("הפניקס פרודוקציה*.xlsx", "MU_NK_*"),
]

# How far back a source may sit behind the newest one and still belong in the
# same merged month. The corpus keeps a year of desktop archives
# (`הפניקס אקסלנס- דוח 09.2025.xls`, 1,152 rows) that no newer file supersedes
# by name — without a floor they dominate the נפרעים union.
STALENESS_MONTHS = 6

# How much of an older report's policy set a newer one from the same insurer
# must cover before the older is treated as superseded rather than complementary.
CONTAINMENT = 0.80

_PERIOD_SUFFIX = re.compile(
    r"[\s_\-]*[\(\[]?\s*(?:"
    r"ינואר|פברואר|מרץ|אפריל|מאי|יוני|יולי|אוגוסט|ספטמבר|אוקטובר|נובמבר|דצמבר"
    r"|\d{1,2}[-_./]\d{2,4}|\d{4}"
    r")[\s\d]*[\)\]]?\s*$"
)


def _report_key(name: str) -> str:
    """The report's identity, independent of which month/run produced it.

    The corpus proxy for `portal_kind` is the filename: repeat runs of one
    report share it exactly (5× `מגדל - ייצור (יוני 2026).xlsx`, 6× the Menora
    zip), while a company's genuinely DIFFERENT books do not — הפניקס alone
    ships four (גמל, חיים ובריאות, the MU terminal book, the SFE holdings DAT).
    Keying on the insurer instead of the report collapses those four into
    whichever happens to be newest and silently loses three.
    """
    stem = Path(name).stem
    for _ in range(2):                       # "(יוני 2026)" then a trailing year
        stem = _PERIOD_SUFFIX.sub("", stem).strip(" -_")
    return stem or name


def _drop_derived(units: list[dict]) -> list[dict]:
    """Drop a plugin's derived artifact when its raw source sits beside it."""
    keep = []
    for u in units:
        p = u["items"][0]["path"]
        derived = False
        for artifact_glob, raw_glob in DERIVED_ARTIFACTS:
            if p.match(artifact_glob) and any(
                q.match(raw_glob) and q != p for q in p.parent.iterdir()
            ):
                derived = True
                break
        if not derived:
            keep.append(u)
    return keep


# A file cannot describe a month more than a year before it was downloaded.
# When it appears to, the period came from a policy INCEPTION date, not a
# reporting month — `הכשרה נפרעים.xlsx` downloaded 2026-06 reports 2024-12 from
# a sign_date that sits exactly at `_MAX_DATA_PERIOD_AGE_MONTHS`, and the
# staleness floor then threw away 350 live commission rows. The download date is
# the more trustworthy signal in that case.
_PERIOD_TRUST_MONTHS = 12


def _effective_period(pm: date | None, downloaded: datetime) -> date:
    dl = date(downloaded.year, downloaded.month, 1)
    if pm and _months_between(pm, dl) <= _PERIOD_TRUST_MONTHS:
        return pm
    return dl


def _months_between(a: date, b: date) -> int:
    return abs((b.year - a.year) * 12 + (b.month - a.month))


def _modal_period(rows: list[dict]) -> date:
    """The month the merged file is FOR — the modal period of its sources."""
    months = [r["period"] for r in rows if r["period"]]
    if not months:
        return date.today().replace(day=1)
    return Counter(months).most_common(1)[0][0]


def _month_label(d: date | None) -> str:
    if not d:
        return ""
    months = ["ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
              "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"]
    return f"{months[d.month - 1]} {d.year}"


def _as_of(period: date) -> date:
    nxt = (period.replace(year=period.year + 1, month=1, day=1)
           if period.month == 12 else period.replace(month=period.month + 1, day=1))
    return nxt - timedelta(days=1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="print the selection only, write nothing")
    ap.add_argument("--out", default=str(OUT_DIR))
    args = ap.parse_args()

    from parse_corpus import build_units, collect_files, parse_unit
    from app.services.parser_service import category_for_format, detect_period_month
    from app.services.portal_automation.aggregate import (
        build_unified_nifraim_bytes, build_unified_workbook_bytes,
        merged_company_key,
    )

    units = [u for u in build_units(collect_files())
             if u["items"][0]["path"].name not in EXCLUDE_NAMES]
    units = _drop_derived(units)

    parsed = []
    for u in units:
        r = parse_unit(u)
        if r["error"] or not r["records"]:
            continue
        cat = category_for_format(r["format"])
        if cat not in ("production", "commission"):
            continue          # recruits / volume / unknown do not belong here
        recs = r["_records"]
        path = Path(r["files"][0])
        # `uploaded_at` is not optional here: without it detect_period_month has
        # no anchor for steps 3 and 5 and falls through to a record date, which
        # produced months like 2006-10 and 2008-08 in the first dry run — and
        # those outvoted the real ones when picking the merged month.
        downloaded = datetime.fromtimestamp(u["mtime"])
        pm = detect_period_month(r["name"], recs, uploaded_at=downloaded)
        pm = _effective_period(pm, downloaded)
        parsed.append({
            **r, "category": cat, "mtime": u["mtime"], "path": path,
            "period": pm, "report": _report_key(r["name"]),
            "entity": Counter(
                merged_company_key(rec, commission=(cat == "commission"))
                for rec in recs
            ).most_common(1)[0][0],
            "fingerprint": (
                frozenset((rec.get("id_number"),
                           str(rec.get("fund_policy_number") or ""))
                          for rec in recs),
                round(sum(float(rec.get("total_premium") or 0) for rec in recs), 2),
                round(sum(float(rec.get("accumulation") or 0) for rec in recs), 2),
                round(sum(float(rec.get("commission_paid") or 0) for rec in recs), 2),
            ),
        })

    # 1) repeat runs of ONE report → newest.
    chosen: dict[tuple, dict] = {}
    for r in parsed:
        k = (r["category"], r["report"])
        if k not in chosen or r["mtime"] > chosen[k]["mtime"]:
            chosen[k] = r

    # 2) the SAME report saved under two names → newest. Identical policy set
    #    AND identical sums is not a coincidence: `אלטשולר נפרעים גמל.xlsx` and
    #    `עמלות דצמבר אלטשולר דצמבר 2025.xlsx` are both 134 rows / ₪2,094, and
    #    `הפניקס - פרודוקציה.xlsx` / `phoenix_production_202606.xlsx` are both
    #    80 rows / ₪1,774,008. Migdal's two books have DIFFERENT policy sets, so
    #    this never touches them.
    by_fp: dict[tuple, dict] = {}
    for r in chosen.values():
        k = (r["category"], r["fingerprint"])
        if k not in by_fp or r["mtime"] > by_fp[k]["mtime"]:
            by_fp[k] = r
    survivors = list(by_fp.values())

    # 3) SUPERSEDED books — an older report whose policies a newer one from the
    #    same insurer already covers. Measured, not assumed: an insurer really
    #    does ship complementary books (הפניקס גמל vs חיים ובריאות; the Harel
    #    כספת product-presence rows vs the agents-portal savings money), and
    #    those have disjoint policy sets, so containment leaves them alone. What
    #    it catches is the desktop archive: `עמלות מנורה ביטוחי בריאות.xlsx`
    #    (Jan, 796 rows) is the same book as the June portal zip (799 rows), and
    #    stacking them counts Menora's commission twice.
    superseded: list[tuple[dict, dict, float]] = []
    alive = sorted(survivors, key=lambda r: r["mtime"], reverse=True)
    keep_after_containment: list[dict] = []
    for i, r in enumerate(alive):
        mine = {k for k in r["fingerprint"][0] if k[0]}
        covered_by = None
        for newer in alive[:i]:
            if newer["category"] != r["category"] or newer["entity"] != r["entity"]:
                continue
            theirs = {k for k in newer["fingerprint"][0] if k[0]}
            if not mine:
                continue
            share = len(mine & theirs) / len(mine)
            if share >= CONTAINMENT:
                covered_by = (newer, share)
                break
        if covered_by:
            superseded.append((r, covered_by[0], covered_by[1]))
        else:
            keep_after_containment.append(r)
    survivors = keep_after_containment

    # 4) staleness floor, per side, relative to that side's newest period.
    stale: list[dict] = []
    kept: list[dict] = []
    for cat in ("production", "commission"):
        side = [r for r in survivors if r["category"] == cat]
        periods = [r["period"] for r in side if r["period"]]
        newest = max(periods) if periods else None
        for r in side:
            if newest and r["period"] and _months_between(r["period"], newest) > STALENESS_MONTHS:
                stale.append(r)
            else:
                kept.append(r)

    prod = [r for r in kept if r["category"] == "production"]
    comm = [r for r in kept if r["category"] == "commission"]

    def _show(title, rows):
        print(f"\n{title} — {len(rows)} sources")
        for r in sorted(rows, key=lambda x: (x["entity"], x["report"])):
            print(f"  {str(r['period']):10s} {r['entity'][:32]:32s} {r['name'][:42]:42s} "
                  f"rec={r['records']:5d} prem={r['premium']:12,.0f} "
                  f"acc={r['accumulation']:14,.0f} comm={r['commission']:10,.0f}")
    _show("פרודוקציה", prod)
    _show("נפרעים", comm)

    if superseded:
        print("\nsuperseded by a newer report from the same insurer "
              f"(≥{CONTAINMENT:.0%} of policies already covered):")
        for old_r, new_r, share in sorted(superseded, key=lambda x: x[0]["name"]):
            print(f"  {old_r['name'][:44]:44s} rec={old_r['records']:5d} "
                  f"→ {share:.0%} in {new_r['name'][:34]}")

    if stale:
        print(f"\nexcluded as stale (> {STALENESS_MONTHS} months behind the newest source):")
        for r in sorted(stale, key=lambda x: str(x["period"])):
            print(f"  {str(r['period']):10s} {r['name'][:50]:50s} "
                  f"rec={r['records']:5d} ({r['category']})")
    print(f"\n{len(parsed) - len(survivors) - len(superseded)} repeat runs collapsed "
          f"· {len(superseded)} superseded · {len(stale)} stale")

    prod_records = [rec for r in prod for rec in r["_records"]]
    comm_records = [rec for r in comm for rec in r["_records"]]

    prod_period = _modal_period(prod)
    comm_period = _modal_period(comm)
    print(f"\nproduction period {prod_period} · נפרעים period {comm_period}")
    print(f"production rows {len(prod_records):,} · נפרעים rows {len(comm_records):,}")

    if args.dry_run:
        return 0

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    p_name = f"פרודוקציה מאוחד {_month_label(prod_period)}.xlsx"
    c_name = f"נפרעים מאוחד {_month_label(comm_period)}.xlsx"
    for rec in comm_records:
        rec.setdefault("_period_label", _month_label(comm_period))

    (out / p_name).write_bytes(
        build_unified_workbook_bytes(prod_records, as_of=_as_of(prod_period)))
    (out / c_name).write_bytes(
        build_unified_nifraim_bytes(comm_records, period_label=_month_label(comm_period)))
    print(f"\nwrote {out / p_name}")
    print(f"wrote {out / c_name}")

    # Round-trip: the merged files must parse back through the same front door
    # the app ingests them with. A workbook that builds but does not re-parse is
    # the exact silent failure this whole exercise is about.
    from app.services.upload_ingest import parse_any
    for f in (out / p_name, out / c_name):
        res = parse_any(f.read_bytes(), f.name)
        print(f"  round-trip {f.name}: format={res['format']} "
              f"records={len(res['records'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
