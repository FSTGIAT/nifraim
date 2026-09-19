#!/usr/bin/env python3
"""Offline parser harness — run EVERY parser over every real insurer file on disk.

Why this exists: parser regressions in this app are *silent*. A file still
"parses" while quietly losing a column (see `fix(mimshak): accumulation dropped
every balance component after the first`). So this walks the real download
corpus, drives the same front door production uses
(`upload_ingest.parse_any`), and prints a coverage matrix carrying the numbers
that actually matter: records, non-null ת"ז, Σpremium, Σaccumulation, Σcommission.

    backend/venv/bin/python backend/scripts/parse_corpus.py
    backend/venv/bin/python backend/scripts/parse_corpus.py --json out.json

A "unit" is what the pipeline actually ingests, which is not always one file:

  * a Harel כספת download is a SET (SP/RP/SB/RB/RM) — ת"ז and names only exist
    on the SP/RP masters and are joined onto the rest, so a single vault file
    parsed alone legitimately has zero ת"ז;
  * a Migdal Mimshak bundle is a folder of .DAT + .MBT lookups;
  * a Phoenix MU / Harel vault set yields Hebrew production ROWS, which the real
    pipeline writes to a production xlsx and re-parses — so the harness does the
    same instead of measuring an intermediate shape.

Plugin intermediates (`_raw_גמל.xls`, `phoenix_gemel_raw.xlsx`, …) are excluded:
a failure there is not a parser bug.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import traceback
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # backend/
sys.path.insert(0, str(ROOT))
REPO = ROOT.parent

CORPUS_ROOTS = [
    REPO / "data" / "portal_downloads",
    Path("/mnt/c/Users/roygi/Desktop/KIKO"),
    Path("/mnt/c/fnxbox"),
    REPO,                                            # stray spreadsheets only
]

SKIP_NAME_PREFIXES = ("_raw_", "MU_parsed_preview")
SKIP_NAME_SUBSTR = ("_raw_dump", "phoenix_gemel_raw", "phoenix_nifraim_raw")
SKIP_EXT = {".png", ".log", ".py", ".exe", ".psl", ".csv", ".apk", ".html",
            ".docx", ".pdf", ".json", ".txt", ".md", ".yml", ".yaml", ".js",
            ".sh", ".ps1", ".toml"}
SKIP_DIRS = {"downloaded_unified", "node_modules", "graphify-out", "venv"}

# Password-protected deliverables. The insurer sets these; the file is useless
# without them, so the harness must be able to open them.
KNOWN_PASSWORDS = {
    "הפניקס אקסלנס- דוח 09.2025.xls": "0451",
    "הפניקס אקסלנס- דוח 09.2025 (1).xls": "0451",
}


def _is_candidate(p: Path) -> bool:
    n = p.name
    if n.startswith(".") or n == "Dockerfile":
        return False
    if any(n.startswith(x) for x in SKIP_NAME_PREFIXES):
        return False
    if any(x in n for x in SKIP_NAME_SUBSTR):
        return False
    if p.suffix.lower() in SKIP_EXT:
        return False
    if set(p.parts) & SKIP_DIRS:
        return False
    try:
        return p.stat().st_size >= 512
    except OSError:
        return False


def collect_files() -> list[dict]:
    by_hash: dict[str, dict] = {}
    for root in CORPUS_ROOTS:
        if not root.exists():
            continue
        # The repo root holds source files too — only stray spreadsheets there.
        walk = ([q for q in root.glob("*") if q.suffix.lower() in (".xlsx", ".xls")]
                if root == REPO else root.rglob("*"))
        for p in walk:
            if not p.is_file() or not _is_candidate(p):
                continue
            try:
                b = p.read_bytes()
            except OSError:
                continue
            h = hashlib.sha256(b).hexdigest()[:12]
            mt = p.stat().st_mtime
            prev = by_hash.get(h)
            if prev is None or mt > prev["mtime"]:
                by_hash[h] = {"hash": h, "path": p, "mtime": mt, "size": len(b)}
    return sorted(by_hash.values(), key=lambda d: -d["mtime"])


# ── units ────────────────────────────────────────────────────────────────────

def build_units(files: list[dict]) -> list[dict]:
    """Group the flat file list into the units the pipeline actually ingests."""
    from app.services.harel_vault_prod import is_vault_file
    from app.services.phoenix_mu import is_phoenix_mu

    by_dir: dict[Path, list[dict]] = defaultdict(list)
    for f in files:
        by_dir[f["path"].parent].append(f)

    units: list[dict] = []
    for folder, items in by_dir.items():
        vault = [i for i in items if is_vault_file(i["path"])]
        mbt = [i for i in items if i["path"].suffix.upper() == ".MBT"]
        dat = [i for i in items if i["path"].suffix.upper() == ".DAT"]
        claimed: set[Path] = set()

        if vault:
            units.append({"kind": "harel_vault_set", "folder": folder,
                          "items": vault,
                          "name": f"כספת הראל ({len(vault)} דוחות)"})
            claimed |= {i["path"] for i in vault}

        if mbt and dat:
            members = mbt + dat
            units.append({"kind": "mimshak_bundle", "folder": folder,
                          "items": members,
                          "name": f"Mimshak bundle ({len(members)} members)"})
            claimed |= {i["path"] for i in members}

        for i in items:
            if i["path"] in claimed:
                continue
            try:
                head = i["path"].read_bytes()[:4000]
            except OSError:
                continue
            kind = "phoenix_mu" if (not i["path"].suffix and is_phoenix_mu(head)) else "file"
            units.append({"kind": kind, "folder": folder, "items": [i],
                          "name": i["path"].name})

    # Two runs of the same portal deliver byte-identical sets — collapse them.
    seen: dict[tuple, dict] = {}
    for u in units:
        key = (u["kind"], tuple(sorted(i["hash"] for i in u["items"])))
        newest = max(i["mtime"] for i in u["items"])
        u["mtime"] = newest
        if key not in seen or newest > seen[key]["mtime"]:
            seen[key] = u
    return sorted(seen.values(), key=lambda u: -u["mtime"])


# ── parsing ──────────────────────────────────────────────────────────────────

def _rows_to_xlsx(rows: list[dict], columns: list[str]) -> bytes:
    """Hebrew production ROWS → a production xlsx, exactly as the plugins do.

    phoenix_mu and harel_vault_prod both emit the Hebrew column dicts that go
    into a production workbook, NOT ClientRecord dicts. The real pipeline writes
    that workbook and re-ingests it, so measuring the intermediate would measure
    a shape the DB never sees.
    """
    import pandas as pd
    buf = io.BytesIO()
    pd.DataFrame(rows, columns=columns).to_excel(buf, index=False)
    return buf.getvalue()


def parse_unit(unit: dict) -> dict:
    from app.services.upload_ingest import parse_any

    row = {"unit": unit["kind"], "name": unit["name"],
           "files": [str(i["path"]) for i in unit["items"]],
           "hash": ",".join(sorted(i["hash"] for i in unit["items"]))[:64],
           "format": None, "company": None, "records": 0, "with_id": 0,
           "premium": 0.0, "accumulation": 0.0, "commission": 0.0,
           "error": None, "parts": []}
    try:
        if unit["kind"] == "harel_vault_set":
            _parse_vault_set(unit, row)
        elif unit["kind"] == "mimshak_bundle":
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                for i in unit["items"]:
                    z.writestr(i["path"].name, i["path"].read_bytes())
            _fill(row, parse_any(buf.getvalue(), unit["folder"].name + ".zip"))
        elif unit["kind"] == "phoenix_mu":
            from app.services.phoenix_mu import parse_phoenix_mu, PRODUCTION_COLUMNS
            p = unit["items"][0]["path"]
            rows = parse_phoenix_mu(p.read_bytes())["records"]
            xlsx = _rows_to_xlsx(rows, PRODUCTION_COLUMNS)
            _fill(row, parse_any(xlsx, f"הפניקס {p.name}.xlsx"))
        else:
            p = unit["items"][0]["path"]
            _fill(row, parse_any(p.read_bytes(), p.name, KNOWN_PASSWORDS.get(p.name)))
    except Exception as e:                                   # noqa: BLE001
        row["error"] = f"{type(e).__name__}: {e}"
        row["traceback"] = traceback.format_exc(limit=6)
    return row


def _parse_vault_set(unit: dict, row: dict) -> None:
    """Parse all vault reports together, join identity from the masters, then
    push each label through the production xlsx door."""
    from app.services import harel_vault_prod as hv
    from app.services.upload_ingest import parse_any

    parsed = []
    for i in unit["items"]:
        res = hv.parse_vault_file(i["path"])
        if res is not None:
            parsed.append(res)
    hv.fill_identity_from_masters(parsed)

    merged = {"format": None, "company_source": None, "records": []}
    for company_source, label, rows in parsed:
        if not rows:
            row["parts"].append({"label": label, "records": 0})
            continue
        xlsx = _rows_to_xlsx(rows, hv._PRODUCTION_COLUMNS)
        res = parse_any(xlsx, f"{company_source} - פרודוקציה.xlsx")
        sub = {"label": label, "company": res["company_source"],
               "records": len(res["records"]),
               "with_id": sum(1 for r in res["records"] if r.get("id_number"))}
        row["parts"].append(sub)
        merged["format"] = res["format"]
        merged["company_source"] = "הראל (כספת)"
        merged["records"].extend(res["records"])
    _fill(row, merged)


def _fill(row: dict, res: dict) -> None:
    recs = res.get("records") or []
    # Kept for in-process consumers (build_unified_from_corpus); stripped before
    # the JSON dump so the report stays a report.
    row["_records"] = recs
    row["format"] = res.get("format")
    row["company"] = res.get("company_source")
    row["records"] = len(recs)
    row["with_id"] = sum(1 for r in recs if r.get("id_number"))
    # ClientRecord column names — `total_premium` (NOT "premium") and
    # `commission_paid` (NOT "commission_amount"). Getting these wrong makes
    # every file look like it carries no money at all.
    for key, col in (("premium", "total_premium"),
                     ("accumulation", "accumulation"),
                     ("commission", "commission_paid")):
        row[key] = round(sum(float(r.get(col) or 0) for r in recs), 2)
    # None-vs-0 matters: a parser that fabricates 0.0 where the file has no
    # premium column at all looks identical in a sum.
    row["premium_none"] = sum(1 for r in recs if r.get("total_premium") is None)
    row["accum_none"] = sum(1 for r in recs if r.get("accumulation") is None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="write full rows to this path")
    ap.add_argument("--only", help="substring filter on the unit name")
    args = ap.parse_args()

    units = build_units(collect_files())
    if args.only:
        units = [u for u in units if args.only in u["name"]]
    print(f"corpus: {len(units)} ingest units\n")

    rows = []
    for u in units:
        r = parse_unit(u)
        rows.append(r)
        status = "FAIL" if r["error"] else ("EMPTY" if not r["records"] else "ok")
        print(f"{status:5s} {r['name'][:50]:50s} {str(r['format'])[:24]:24s} "
              f"{str(r['company'])[:16]:16s} rec={r['records']:6d} id={r['with_id']:6d} "
              f"prem={r['premium']:13,.0f} acc={r['accumulation']:15,.0f} "
              f"comm={r['commission']:11,.0f}")
        if r["error"]:
            print(f"      └─ {r['error']}")

    print(f"\n{sum(1 for r in rows if not r['error'] and r['records'])}/{len(rows)} "
          f"produced records · {sum(1 for r in rows if r['error'])} errors · "
          f"{sum(1 for r in rows if not r['error'] and not r['records'])} empty")

    if args.json:
        slim = [{k: v for k, v in r.items() if k != "_records"} for r in rows]
        Path(args.json).write_text(json.dumps(slim, ensure_ascii=False, indent=2,
                                              default=str), encoding="utf-8")
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
