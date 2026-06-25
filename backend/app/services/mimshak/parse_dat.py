"""Mimshak (Israeli insurance "מבנה אחיד") POC parser.

Usage:
    python parse_dat.py <folder-with-DAT-and-MBT-files> [--out OUT_DIR]

Outputs (under OUT_DIR, default ./out/):
    records.json          — one enriched record per (customer × policy).
    field_coverage.md     — human-readable field map and "missing in current
                            Excel parser" report.

Intentionally standalone: no FastAPI, no SQLAlchemy. Can be run from the repo
root inside the backend venv OR from any Python 3.10+.
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

# Absolute imports when run as a module (python -m scripts.mimshak_poc.parse_dat)
# or direct script-style (python parse_dat.py).
try:
    from . import mbt as mbt_mod
    from .xml_fields import XML_FIELD_MAP, CLIENT_RECORD_COLUMNS
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    import mbt as mbt_mod  # type: ignore
    from xml_fields import XML_FIELD_MAP, CLIENT_RECORD_COLUMNS  # type: ignore


# ── helpers ──────────────────────────────────────────────────────────────

def _local_tag(tag: str) -> str:
    """Strip XML namespace, if any. "{ns}Foo" -> "Foo"."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _is_nil(elem: ET.Element) -> bool:
    for key, val in elem.attrib.items():
        if key.endswith("nil") and val == "true":
            return True
    return False


def _text(elem: ET.Element) -> str | None:
    if _is_nil(elem):
        return None
    txt = elem.text
    if txt is None:
        return None
    txt = txt.strip()
    return txt or None


def _strip_leading_zeros(s: str | None) -> str | None:
    if s is None:
        return None
    stripped = s.lstrip("0")
    return stripped or "0"


# ── XML walk ─────────────────────────────────────────────────────────────

def find_dat(folder: Path) -> Path:
    """Pick the main DAT file. Prefers *HOLDNG* names. If multiple HOLDNG
    files exist (Migdal Safes vault keeps a sliding 3-month history —
    e.g. `...20260309...DAT`, `...20260414...DAT`, `...20260512...DAT`),
    return the LATEST: the filename encodes YYYYMMDD between `INP009` and
    the time suffix, so lexicographic sort = chronological sort = freshest
    last."""
    candidates = list(folder.glob("*.DAT")) + list(folder.glob("*.dat"))
    if not candidates:
        raise FileNotFoundError(f"No .DAT file found in {folder}")
    holdng = sorted(p for p in candidates if "HOLDNG" in p.name.upper())
    if holdng:
        return holdng[-1]
    return candidates[0]


def _collect_leaves(elem: ET.Element, seen: Counter, unmapped: set[str]):
    """Walk a subtree, counting every leaf-element occurrence and flagging
    elements with no entry in XML_FIELD_MAP."""
    tag = _local_tag(elem.tag)
    if list(elem):  # has children
        for child in elem:
            _collect_leaves(child, seen, unmapped)
    else:
        seen[tag] += 1
        if tag not in XML_FIELD_MAP:
            unmapped.add(tag)


def _extract_leaves(elem: ET.Element, out: dict[str, str]):
    """Flatten all descendant leaves into a dict. Last write wins — that's
    fine because we also produce structured child lists separately."""
    for child in elem.iter():
        if list(child):
            continue
        tag = _local_tag(child.tag)
        val = _text(child)
        if val is not None and tag not in out:
            out[tag] = val


def _extract_children_by_tag(elem: ET.Element, tag_name: str) -> list[ET.Element]:
    """Direct children only (no deep recursion) with matching local name."""
    return [c for c in elem if _local_tag(c.tag) == tag_name]


def _find_first(elem: ET.Element, tag_name: str) -> ET.Element | None:
    for c in elem.iter():
        if _local_tag(c.tag) == tag_name:
            return c
    return None


def parse_dat(dat_path: Path):
    """Yield (customer_id_or_none, policy_dict) for every HeshbonOPolisa."""
    tree = ET.parse(dat_path)
    root = tree.getroot()

    for policy_elem in root.iter():
        if _local_tag(policy_elem.tag) != "HeshbonOPolisa":
            continue
        yield _build_policy(policy_elem)


def _walk_ancestors_for_customer(root: ET.Element, policy_elem: ET.Element) -> ET.Element | None:
    """ElementTree doesn't give parents; walk the tree once to find the
    nearest YeshutLakoach ancestor of a policy element."""
    # Build a parent map once (small files — acceptable)
    if not hasattr(_walk_ancestors_for_customer, "_parent_cache"):
        _walk_ancestors_for_customer._parent_cache = {}
    cache = _walk_ancestors_for_customer._parent_cache
    if id(root) not in cache:
        pm = {}
        for p in root.iter():
            for c in p:
                pm[id(c)] = p
        cache[id(root)] = pm
    pm = cache[id(root)]
    current = policy_elem
    while id(current) in pm:
        current = pm[id(current)]
        if _local_tag(current.tag) == "YeshutLakoach":
            return current
    return None


def _build_policy(policy_elem: ET.Element) -> dict:
    """Extract a single policy as a nested dict: core fields, beneficiaries,
    funds, riders, deposits."""
    policy: dict = {"_raw_leaves": {}}
    # Collect every descendant leaf. First value wins, so direct children of
    # the policy (KIDOD-ACHID, MISPAR-POLISA-O-HESHBON, etc.) override any
    # deeper-nested duplicates. Financial fields live under PirteiTaktziv/Tsua/
    # PerutMitryot and are only reachable via deep descent.
    for descendant in policy_elem.iter():
        if list(descendant):
            continue
        tag = _local_tag(descendant.tag)
        if tag in policy["_raw_leaves"]:
            continue
        v = _text(descendant)
        if v is not None:
            policy["_raw_leaves"][tag] = v

    # ── Coverages / riders (Kisuim → ZihuiKisui) ─────────────────────────
    coverages = []
    for kisuim_block in _extract_children_by_tag(policy_elem, "Kisuim"):
        for coverage in _extract_children_by_tag(kisuim_block, "ZihuiKisui"):
            cov: dict = {}
            _extract_leaves(coverage, cov)
            # Nested beneficiaries / fund allocations under the coverage
            beneficiaries = []
            funds = []
            for mutav in coverage.iter():
                if _local_tag(mutav.tag) != "Mutav":
                    continue
                row: dict = {}
                _extract_leaves(mutav, row)
                # Heuristic: presence of a beneficiary ID marks a person;
                # otherwise treat as a fund allocation.
                if any(k in row for k in ("MISPAR-ZIHUY-MUTAV", "SHEM-PRATI-MUTAV", "SHEM-MISHPACHA-MUTAV")):
                    beneficiaries.append(row)
                else:
                    funds.append(row)
            cov["_beneficiaries"] = beneficiaries
            cov["_funds"] = funds
            coverages.append(cov)
    policy["_coverages"] = coverages

    # ── Top-level beneficiaries + fund allocations (some policies put these
    # directly under HeshbonOPolisa instead of nested in Kisuim) ─────────
    top_beneficiaries = []
    top_funds = []
    for mutav in policy_elem.iter():
        if _local_tag(mutav.tag) != "Mutav":
            continue
        # Skip if already captured under a coverage
        if any(id(mutav) == id(x) for cov in coverages for x in cov.get("_funds", []) + cov.get("_beneficiaries", [])):
            continue
        row: dict = {}
        _extract_leaves(mutav, row)
        if any(k in row for k in ("MISPAR-ZIHUY-MUTAV", "SHEM-PRATI-MUTAV", "SHEM-MISHPACHA-MUTAV")):
            top_beneficiaries.append(row)
        else:
            top_funds.append(row)
    if top_beneficiaries:
        policy["_beneficiaries"] = top_beneficiaries
    if top_funds:
        policy["_funds"] = top_funds

    # ── Loans / annual deposits — stash as-is if present ────────────────
    loan = _find_first(policy_elem, "Halvaa")
    if loan is not None:
        row: dict = {}
        _extract_leaves(loan, row)
        if row:
            policy["_loan"] = row

    annual = _find_first(policy_elem, "HafkadotShnatiyot")
    if annual is not None:
        row: dict = {}
        _extract_leaves(annual, row)
        if row:
            policy["_annual_deposits"] = row

    return policy


# ── Enrichment ───────────────────────────────────────────────────────────

def _flatten_to_clientrecord(customer: dict, policy: dict, insurer_name: str | None) -> dict:
    """Produce a dict that mirrors the columns a future DAT parser would write
    into ClientRecord — so the report can contrast with what the Excel flow
    currently fills."""
    leaves = policy.get("_raw_leaves", {})
    id_num_raw = customer.get("MISPAR-ZIHUY-LAKOACH") or leaves.get("MISPAR-ZIHUY-LAKOACH")
    out = {
        "id_number": _strip_leading_zeros(id_num_raw) if id_num_raw else None,
        "first_name": customer.get("SHEM-PRATI") or leaves.get("SHEM-PRATI"),
        "last_name": customer.get("SHEM-MISHPACHA") or leaves.get("SHEM-MISHPACHA"),
        "product": leaves.get("SHEM-TOCHNIT"),
        "product_type": leaves.get("SUG-MUTZAR"),
        "fund_policy_number": leaves.get("MISPAR-POLISA-O-HESHBON"),
        "product_status": leaves.get("STATUS-POLISA-O-CHESHBON"),
        "sign_date": leaves.get("TAARICH-HITZTARFUT-RISHON"),
        "receiving_company": insurer_name,
        "total_premium": leaves.get("SCHUM-BITUACH"),
        "accumulation": leaves.get("ERECH-MESOLAK-SOF-SHANA"),
        "management_fee": leaves.get("DMEI-NIHUL-ACHIDIM"),
        "management_fee_amount": leaves.get("DMEI-NIHUL-ACHERIM"),
        "client_phone": customer.get("MISPAR-CELLULARI") or leaves.get("MISPAR-CELLULARI"),
        "client_email": customer.get("E-MAIL") or leaves.get("E-MAIL"),
    }
    return out


# ── Report generation ───────────────────────────────────────────────────

def _render_field_coverage_md(
    dat_path: Path,
    element_counts: Counter,
    unmapped_tags: set[str],
    mbt_summary: dict,
    sample_stats: dict,
) -> str:
    lines: list[str] = []
    lines.append("# Mimshak DAT / MBT field-coverage report\n")
    lines.append(f"**Source file:** `{dat_path.name}`  \n")
    lines.append(f"**Sample stats:** {sample_stats['customers']} customers · "
                 f"{sample_stats['policies']} policies · "
                 f"{sample_stats['coverages']} coverages · "
                 f"{sample_stats['beneficiaries']} beneficiaries · "
                 f"{sample_stats['funds']} fund allocations\n")

    # Section A — mapping table -------------------------------------------
    lines.append("\n## Section A · XML element map\n")
    lines.append("All XML leaf elements encountered, in descending frequency. "
                 "`target` is the `ClientRecord` column we'd write into (or "
                 "`—` if it's richer than the flat schema can represent).\n")
    lines.append("| # seen | Element | English | Meaning (He) | → ClientRecord |")
    lines.append("|-------:|---------|---------|--------------|----------------|")
    for tag, count in element_counts.most_common():
        label, meaning, target = XML_FIELD_MAP.get(tag, ("(unmapped)", "—", None))
        target_cell = target if target else "—"
        lines.append(f"| {count} | `{tag}` | {label} | {meaning} | {target_cell} |")

    # Section B — gaps vs current Excel ----------------------------------
    lines.append("\n## Section B · Data present in DAT but NOT in any current Excel parser\n")
    lines.append("Elements mapped to `ClientRecord` columns that `record.py` does "
                 "have — but also rich structures (per-policy beneficiaries, fund "
                 "allocations, yield history) that the flat schema cannot hold.\n")
    lines.append("### Rich structures (need child tables or JSON column)\n")
    lines.append("- Per-policy **beneficiaries** — name, DOB, national ID, % share, relationship code")
    lines.append("- Per-policy **fund allocations** — fund code, name, deposit %, holding %")
    lines.append("- Per-policy **deposit history** — `PerutHafkadotMetchilatShana`")
    lines.append("- Per-policy **loans** — `Halvaa` block (amount, rate, status)")
    lines.append("- Per-coverage **rider lifecycle** — start/end dates, insurer label, type code")
    lines.append("- Per-coverage **premium history** — `hitpatchutpremia`\n")

    lines.append("### Flat fields not in any Excel parser today\n")
    known_columns = CLIENT_RECORD_COLUMNS
    flat_missing = []
    for tag in element_counts:
        label, meaning, target = XML_FIELD_MAP.get(tag, (None, None, None))
        if label is None:
            continue
        if target is None and tag in {
            "ERECH-PIDYON-SOF-SHANA", "SHEUR-TSUA-NETO", "SHEUR-TSUA-BRUTO-CHS-1",
            "REVACH-HEFSED-BENIKOI-HOZAHOT", "SIMAN-REVACH-HEFSED",
            "SACHAR-BERAMAT-HAFKADA", "GOVA-DMEI-NIHUL-NIKBA-AL-PI-HOTZAOT-BAPOAL",
            "KAYAM-CHOV-O-PIGUR", "KAYAM-MEYUPE-KOACH",
            "IND-SCHUM-BITUAH-KOLEL-CHISACHON", "BITUL-KIZUZ-MEMSHALTI",
            "TAARICH-IDKUN-STATUS", "TAARICH-NECHONUT",
            "MIN", "TAARICH-LEYDA", "MATZAV-MISHPACHTI",
            "SHEM-YISHUV", "SHEM-RECHOV", "MIKUD",
        }:
            flat_missing.append((tag, label, meaning))
    for tag, label, meaning in flat_missing:
        lines.append(f"- `{tag}` — {label} ({meaning})")
    if not flat_missing:
        lines.append("_(none detected in this sample)_")

    lines.append("\n### Unmapped XML elements\n")
    lines.append("Elements we encountered in the sample but haven't yet catalogued "
                 "in `xml_fields.py`. Inspect these to decide whether they're "
                 "informational plumbing or data worth capturing.\n")
    if unmapped_tags:
        for tag in sorted(unmapped_tags):
            lines.append(f"- `{tag}` ({element_counts[tag]}×)")
    else:
        lines.append("_(none)_")

    # Section C — recommended follow-up -----------------------------------
    lines.append("\n## Section C · Recommended follow-up persist targets\n")
    lines.append("Priority-ordered sketch of how the DAT could extend Nifraim's data model:\n")
    lines.append("1. **Drop-in writes to `ClientRecord`** — same columns the Excel "
                 "path already uses, populated from the XML's `HeshbonOPolisa` + "
                 "`PERSON.MBT` enrichment. Zero schema work; replaces the SaaS "
                 "middleman for `total_premium`, `accumulation`, `management_fee*`, "
                 "`product`, `fund_policy_number`, `client_email`, etc.")
    lines.append("2. **JSON extension column** (`client_records.mimshak_extras JSONB`) "
                 "— capture surrender value, gross/net yield, P/L indicators, and "
                 "all the flag fields (`KAYAM-*`, `IND-*`) without new tables. "
                 "Queryable in Postgres via `->>` for reports.")
    lines.append("3. **Child tables for rich structure**:")
    lines.append("   - `policy_beneficiaries` — id, policy_id, beneficiary_id, "
                 "name, dob, share_pct, relationship")
    lines.append("   - `policy_funds` — id, policy_id, fund_code, fund_name, "
                 "allocation_pct, holding_pct")
    lines.append("   - `policy_yield_history` — id, policy_id, period, gross_pct, "
                 "net_pct, p_and_l")
    lines.append("   Only worth it once the UI needs to surface this data.")
    lines.append("4. **Ingestion UX** — zip upload (all files in one go). The "
                 "DAT filename (`…HOLDNGINP009….DAT`) encodes sender + timestamp, "
                 "so we can dedup/replace by that key.\n")

    # MBT summary ---------------------------------------------------------
    lines.append("## MBT companion files\n")
    lines.append("| File | Rows loaded | Notes |")
    lines.append("|------|-------------|-------|")
    for name, info in mbt_summary.items():
        lines.append(f"| {name} | {info['rows']} | {info['notes']} |")

    return "\n".join(lines) + "\n"


# ── Main ─────────────────────────────────────────────────────────────────

def run(folder: Path, out_dir: Path) -> int:
    dat_path = find_dat(folder)
    print(f"→ main DAT: {dat_path.name}", file=sys.stderr)

    # MBT lookups
    mbt_data = mbt_mod.load_all(folder)
    mbt_summary = {
        "AGENTS.MBT": {"rows": len(mbt_data["agents"]), "notes": "agent codes"},
        "COMPANY.MBT": {"rows": 1 if mbt_data["company"].get("raw") else 0, "notes": "insurer metadata (often blank)"},
        "PERSON.MBT": {"rows": len(mbt_data["persons"]), "notes": "customer master: email, DOB, gender, city"},
        "COVRLIFE.MBT": {"rows": sum(len(v) for v in mbt_data["covrlife"].values()), "notes": f"{len(mbt_data['covrlife'])} policies × riders"},
        "LIFE.MBT": {"rows": len(mbt_data["life"]), "notes": "per-policy life summary"},
        "LIFEHLTH.MBT": {"rows": len(mbt_data["lifehlth"]), "notes": "life+health bundles"},
    }
    if "errors" in mbt_data:
        for err in mbt_data["errors"]:
            print(f"⚠ MBT load error: {err}", file=sys.stderr)

    # Parse XML + collect stats
    tree = ET.parse(dat_path)
    root = tree.getroot()
    insurer_name = None
    yatzran = next((e for e in root.iter() if _local_tag(e.tag) == "SHEM-YATZRAN"), None)
    if yatzran is not None:
        insurer_name = _text(yatzran)

    element_counts: Counter = Counter()
    unmapped_tags: set[str] = set()
    _collect_leaves(root, element_counts, unmapped_tags)

    # Build a customer-ID → YeshutLakoach leaves map. YeshutLakoach lives under
    # NetuneiMutzar (a sibling of HeshbonotOPolisot) and carries the customer
    # master (name, address, email, etc). Each policy references its customer
    # via NetuneiAmitOmevutach/MISPAR-ZIHUY inside the HeshbonOPolisa.
    customers_by_id: dict[str, dict[str, str]] = {}
    for yl in root.iter():
        if _local_tag(yl.tag) != "YeshutLakoach":
            continue
        leaves: dict[str, str] = {}
        for child in yl.iter():
            if list(child):
                continue
            tag = _local_tag(child.tag)
            val = _text(child)
            if val is not None and tag not in leaves:
                leaves[tag] = val
        cid = _strip_leading_zeros(leaves.get("MISPAR-ZIHUY-LAKOACH", ""))
        if cid:
            customers_by_id[cid] = leaves

    records = []
    customers_seen: set[str] = set()
    total_coverages = 0
    total_beneficiaries = 0
    total_funds = 0

    for policy_elem in root.iter():
        if _local_tag(policy_elem.tag) != "HeshbonOPolisa":
            continue

        # Resolve customer ID from the policy's NetuneiAmitOmevutach block
        policy_customer_id_raw = None
        for nam in policy_elem.iter():
            if _local_tag(nam.tag) == "NetuneiAmitOmevutach":
                for sub in nam:
                    if _local_tag(sub.tag) == "MISPAR-ZIHUY":
                        policy_customer_id_raw = _text(sub)
                        break
                break
        policy_customer_id = _strip_leading_zeros(policy_customer_id_raw) if policy_customer_id_raw else None
        customer_leaves = customers_by_id.get(policy_customer_id, {}) if policy_customer_id else {}

        policy = _build_policy(policy_elem)
        total_coverages += len(policy.get("_coverages", []))
        total_beneficiaries += sum(len(c.get("_beneficiaries", [])) for c in policy.get("_coverages", []))
        total_beneficiaries += len(policy.get("_beneficiaries", []))
        total_funds += sum(len(c.get("_funds", [])) for c in policy.get("_coverages", []))
        total_funds += len(policy.get("_funds", []))

        # MBT enrichment
        cid = policy_customer_id
        if cid:
            customers_seen.add(cid)
        person = mbt_data["persons"].get(cid) if cid else None

        policy_id_raw = policy["_raw_leaves"].get("MISPAR-POLISA-O-HESHBON")
        policy_id = _strip_leading_zeros(policy_id_raw) if policy_id_raw else None
        riders_from_mbt = mbt_data["covrlife"].get(policy_id, []) if policy_id else []
        life_summary = mbt_data["life"].get(policy_id) if policy_id else None
        lifehlth_summary = mbt_data["lifehlth"].get(policy_id) if policy_id else None

        record = {
            "customer": {
                "id_number": cid,
                "raw_leaves": customer_leaves,
                "mbt_person": person,  # email, DOB, gender, city …
            },
            "policy": policy,
            "mbt": {
                "riders": riders_from_mbt,
                "life_summary": life_summary,
                "lifehlth_summary": lifehlth_summary,
            },
            "clientrecord_equivalent": _flatten_to_clientrecord(
                customer_leaves, policy, insurer_name
            ),
        }
        records.append(record)

    # Emit outputs
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "records.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    sample_stats = {
        "customers": len(customers_seen),
        "policies": len(records),
        "coverages": total_coverages,
        "beneficiaries": total_beneficiaries,
        "funds": total_funds,
    }
    (out_dir / "field_coverage.md").write_text(
        _render_field_coverage_md(
            dat_path, element_counts, unmapped_tags, mbt_summary, sample_stats
        ),
        encoding="utf-8",
    )

    print(
        f"✓ parsed {sample_stats['customers']} customers, "
        f"{sample_stats['policies']} policies, "
        f"{sample_stats['coverages']} coverages, "
        f"{sample_stats['beneficiaries']} beneficiaries, "
        f"{sample_stats['funds']} fund allocations",
        file=sys.stderr,
    )
    print(
        f"  enriched via PERSON.MBT ({len(mbt_data['persons'])} rows), "
        f"COVRLIFE.MBT ({sum(len(v) for v in mbt_data['covrlife'].values())} rows), "
        f"LIFE.MBT ({len(mbt_data['life'])} rows)",
        file=sys.stderr,
    )
    print(f"  → {out_dir/'records.json'}", file=sys.stderr)
    print(f"  → {out_dir/'field_coverage.md'}", file=sys.stderr)
    return 0


def main():
    p = argparse.ArgumentParser(description="Mimshak DAT/MBT POC parser")
    p.add_argument("folder", type=Path, help="Folder containing the DAT and MBT files")
    p.add_argument("--out", type=Path, default=None, help="Output directory (default: ./out next to this script)")
    args = p.parse_args()

    if not args.folder.is_dir():
        print(f"error: {args.folder} is not a directory", file=sys.stderr)
        sys.exit(2)

    out_dir = args.out or (Path(__file__).parent / "out")
    sys.exit(run(args.folder, out_dir))


if __name__ == "__main__":
    main()
