"""Generate a production xlsx from a Mimshak HOLDNG folder.

Phase 1a — fills sheets 5 + 6 + the insurance portion of the summary sheets.
Savings sheets 3 + 4 are empty placeholders (Phase 1b).

Usage:
    python to_production_xlsx.py <folder-with-DAT-and-MBT> [--out PATH]
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from contextlib import contextmanager
from pathlib import Path

# Support both "python to_production_xlsx.py" and "python -m scripts.…"
try:
    from . import mbt as mbt_mod
    from .parse_dat import find_dat, _local_tag, _text, _strip_leading_zeros
    from .xlsx_writer import (
        build_insurance_product_row,
        build_coverage_row,
        build_lifehlth_product_row,
        build_covrlife_product_row,
        build_life_product_row,
        build_workbook,
        _fmt_date,
    )
    from .column_maps import TADIRUT_TASHLUM_LABELS
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    import mbt as mbt_mod  # type: ignore
    from parse_dat import find_dat, _local_tag, _text, _strip_leading_zeros  # type: ignore
    from xlsx_writer import (  # type: ignore
        build_insurance_product_row,
        build_coverage_row,
        build_lifehlth_product_row,
        build_covrlife_product_row,
        build_life_product_row,
        build_workbook,
        _fmt_date,
    )
    from column_maps import TADIRUT_TASHLUM_LABELS  # type: ignore


@contextmanager
def _resolve_input(input_path: Path):
    """Yield a folder path for the parser.

    - If `input_path` is a folder, yield it as-is.
    - If `input_path` is a .zip, extract to a temp dir and yield that; cleaned up on exit.
    """
    if input_path.is_dir():
        yield input_path
        return

    if input_path.is_file() and input_path.suffix.lower() == ".zip":
        with tempfile.TemporaryDirectory(prefix="mimshak_") as tmp:
            with zipfile.ZipFile(input_path) as zf:
                zf.extractall(tmp)
            tmp_path = Path(tmp)
            # Some insurer zips wrap everything in a single sub-folder — flatten.
            contents = list(tmp_path.iterdir())
            if len(contents) == 1 and contents[0].is_dir():
                yield contents[0]
            else:
                yield tmp_path
        return

    raise ValueError(f"{input_path} is neither a directory nor a .zip file")


def _collect_leaves(elem: ET.Element) -> dict[str, str]:
    """All descendant leaves as a dict (first value wins)."""
    out: dict[str, str] = {}
    for e in elem.iter():
        if list(e):
            continue
        tag = _local_tag(e.tag)
        if tag in out:
            continue
        v = _text(e)
        if v is not None:
            out[tag] = v
    return out


def run(folder: Path, out_path: Path, verbose: bool = False) -> int:
    dat_path = find_dat(folder)
    if verbose:
        print(f"→ DAT: {dat_path.name}", file=sys.stderr)

    mbt_data = mbt_mod.load_all(folder)

    tree = ET.parse(dat_path)
    root = tree.getroot()

    # Top-level insurer name
    insurer_name = ""
    for e in root.iter():
        if _local_tag(e.tag) == "SHEM-YATZRAN":
            insurer_name = _text(e) or ""
            break

    # Customer map: strip-zeroed national ID → YeshutLakoach leaves
    customers_by_id: dict[str, dict[str, str]] = {}
    for yl in root.iter():
        if _local_tag(yl.tag) != "YeshutLakoach":
            continue
        leaves = _collect_leaves(yl)
        cid = _strip_leading_zeros(leaves.get("MISPAR-ZIHUY-LAKOACH", ""))
        if cid:
            customers_by_id[cid] = leaves

    insurance_rows: list[list] = []
    coverage_rows: list[list] = []
    agent_num = None

    for policy_elem in root.iter():
        if _local_tag(policy_elem.tag) != "HeshbonOPolisa":
            continue

        policy_leaves = _collect_leaves(policy_elem)

        # Resolve customer for this policy via NetuneiAmitOmevutach/MISPAR-ZIHUY
        pol_cid = None
        for nam in policy_elem.iter():
            if _local_tag(nam.tag) != "NetuneiAmitOmevutach":
                continue
            for sub in nam:
                if _local_tag(sub.tag) == "MISPAR-ZIHUY":
                    pol_cid = _strip_leading_zeros(_text(sub) or "")
                    break
            break
        customer = customers_by_id.get(pol_cid, {}) if pol_cid else {}

        mbt_person = mbt_data["persons"].get(pol_cid) if pol_cid else None
        if agent_num is None:
            agent_num = policy_leaves.get("MPR-MEFITZ-BE-YATZRAN") or ""

        valuation_date = _fmt_date(policy_leaves.get("TAARICH-NECHONUT"))

        # Payment frequency lives in NetuneiGvia/TADIRUT-TASHLUM (policy-level)
        payment_freq_code = policy_leaves.get("TADIRUT-TASHLUM")
        payment_freq_label = TADIRUT_TASHLUM_LABELS.get(str(payment_freq_code or "").strip(), "")

        # Agency name: for now pulled from NetuneiGvia/SHEM-MESHALEM as a best-guess
        # proxy; needs an agent-registry lookup to match the reference exactly.
        agency_name = ""

        # Gather this policy's coverages
        policy_coverages: list[dict[str, str]] = []
        for kisuim_block in policy_elem:
            if _local_tag(kisuim_block.tag) != "Kisuim":
                continue
            for zk in kisuim_block:
                if _local_tag(zk.tag) != "ZihuiKisui":
                    continue
                cov_leaves = _collect_leaves(zk)
                policy_coverages.append(cov_leaves)

        # Sheet 5 row
        insurance_rows.append(build_insurance_product_row(
            insurer_name=insurer_name,
            customer=customer,
            policy=policy_leaves,
            coverages=policy_coverages,
            mbt_person=mbt_person,
            valuation_date=valuation_date,
            agency_name=agency_name,
        ))

        # Sheet 6 rows — one per coverage
        for cov in policy_coverages:
            insured_id = _strip_leading_zeros(cov.get("MISPAR-ZIHUY-LAKOACH") or "")
            insured_customer = customers_by_id.get(insured_id) if insured_id else None
            coverage_rows.append(build_coverage_row(
                insurer_name=insurer_name,
                customer=customer,
                policy=policy_leaves,
                coverage=cov,
                insured_customer=insured_customer,
                mbt_person=mbt_person,
                valuation_date=valuation_date,
                agency_name=agency_name,
                payment_frequency_label=payment_freq_label,
            ))

    # ─── Augment with policies from LIFEHLTH.MBT ─────────────────────────
    # The DAT file's HOLDNG records only cover the agent's currently-active
    # primary policies (typically 5-10). LIFEHLTH.MBT carries the agent's
    # FULL register (life + health + mortgage life — typically 50-150+).
    # Add the policies not already captured by the DAT pass so the
    # production view reflects the agent's whole book.
    #
    # Scope filters (match the Migdal "agent production report" view):
    # - Class 4 (savings-linked riders) is excluded — those don't appear
    #   in the manual reference and inflate the count.
    # - Customer must exist in PERSON.MBT — that's the canonical "primary
    #   insured" list. LIFEHLTH/COVRLIFE customer-id columns sometimes
    #   reference beneficiaries / children who aren't the agent's clients.
    primary_customers = set(mbt_data.get("persons", {}).keys())

    def _normalize_customer_id(raw: str) -> str:
        """Migdal stores customer ids in MBT files as `01` + 9-digit national.
        Strip the 2-digit branch prefix then leading zeros to align with
        PERSON.MBT keys (which use plain stripped 9-digit ids)."""
        if raw and raw.startswith("01") and len(raw) == 11:
            raw = raw[2:]
        return raw.lstrip("0") if raw else ""

    lifehlth_path = folder / "LIFEHLTH.MBT"
    extra_lifehlth = 0
    # Hoisted out of the `if lifehlth_path.exists()` block so the COVRLIFE pass
    # below can dedup against LIFEHLTH-only (matching Surense's counting model,
    # which counts a life policy once from DAT *and* once from COVRLIFE *and*
    # once from LIFE.MBT — but only once across LIFEHLTH duplicates).
    seen_lifehlth_policies: set[str] = set()
    if lifehlth_path.exists():
        try:
            from .mbt import _read_text, _split_pipe
        except ImportError:
            from mbt import _read_text, _split_pipe  # type: ignore
        for raw_line in _read_text(lifehlth_path).splitlines():
            if not raw_line.strip():
                continue
            cells = _split_pipe(raw_line)
            if len(cells) < 50:
                continue
            # All LIFEHLTH classes (1-5) are health sub-types per ref —
            # see comment in build_lifehlth_product_row. Don't skip any class.
            # Col 10 is policy ID, col 9 is customer ID (verified by overlap test
            # against PERSON.MBT — 109/109 matches on col 9, 0/109 on col 10).
            policy_id = (cells[10].lstrip("0") if cells[10] else "") or cells[10]
            if not policy_id or policy_id in seen_lifehlth_policies:
                continue
            customer_short = _normalize_customer_id(cells[9])
            if primary_customers and customer_short not in primary_customers:
                continue
            seen_lifehlth_policies.add(policy_id)
            mbt_person = mbt_data["persons"].get(customer_short)
            insurance_rows.append(build_lifehlth_product_row(
                cells=cells,
                mbt_person=mbt_person,
                insurer_name=insurer_name,
                agent_num=agent_num,
            ))
            extra_lifehlth += 1

    # ─── Augment with policies from COVRLIFE.MBT ─────────────────────────
    # COVRLIFE holds 399 rider rows / 115 distinct policies — these are
    # mostly health-coverage policies whose primary records aren't in
    # LIFEHLTH. We emit one row per distinct policy_ref, classifying each
    # by *inheriting* the parent customer's dominant LIFEHLTH class
    # (col 2) rather than running the brittle rider-name keyword
    # classifier. Rationale: rider names like "ביטוח חיים למקרה מוות"
    # appear on HEALTH policies and would otherwise be mis-classified.
    from collections import Counter as _Counter
    covrlife_path = folder / "COVRLIFE.MBT"
    extra_covrlife = 0

    # Per-customer LIFEHLTH dominant class (computed from raw LIFEHLTH)
    cust_dom_class: dict[str, str] = {}
    if lifehlth_path.exists():
        cust_classes: dict[str, _Counter] = {}
        for raw in _read_text(lifehlth_path).splitlines():
            if not raw.strip(): continue
            c = _split_pipe(raw)
            if len(c) < 11: continue
            cid = _normalize_customer_id(c[9])
            klass = c[2]
            if cid and klass:
                cust_classes.setdefault(cid, _Counter())[klass] += 1
        for cid, ctr in cust_classes.items():
            cust_dom_class[cid] = ctr.most_common(1)[0][0]

    CLASS_TO_LABELS = {
        "1": ("ביטוח חיים", "מגדל - חיים"),
        "2": ("ביטוח בריאות", "מגדל - בריאות"),
        "3": ("ביטוח חיים משכנתא", "מגדל - ביטוח חיים משכנתא"),
    }

    if covrlife_path.exists():
        # Dedup COVRLIFE only against LIFEHLTH (not DAT) — the 6 life policies
        # that live in BOTH DAT and COVRLIFE should be emitted twice to match
        # Surense's product count (which lists each source's policies).
        seen_covrlife: set[str] = set()
        for raw_line in _read_text(covrlife_path).splitlines():
            if not raw_line.strip():
                continue
            cells = _split_pipe(raw_line)
            if len(cells) < 20:
                continue
            # COVRLIFE col 1 has the `01`-prefixed policy ref; strip prefix
            # then leading zeros to normalize against LIFEHLTH col 10.
            policy_ref = cells[1]
            if policy_ref.startswith("01") and len(policy_ref) == 11:
                policy_ref = policy_ref[2:]
            policy_id = policy_ref.lstrip("0") or policy_ref
            if not policy_id or policy_id in seen_covrlife or policy_id in seen_lifehlth_policies:
                continue
            customer_short = cells[18].lstrip("0") if cells[18] else ""
            if primary_customers and customer_short not in primary_customers:
                continue
            seen_covrlife.add(policy_id)

            # Look up the customer's dominant LIFEHLTH class — use it to
            # override the rider-name keyword classifier in build_covrlife.
            dom_class = cust_dom_class.get(customer_short)
            override = CLASS_TO_LABELS.get(dom_class) if dom_class else None

            mbt_person = mbt_data["persons"].get(customer_short)
            row = build_covrlife_product_row(
                cells=cells,
                mbt_person=mbt_person,
                insurer_name=insurer_name,
                agent_num=agent_num,
            )
            # Apply class override: row[1]=סוג מוצר, row[2]=מוצר
            if override is not None:
                row[1] = override[0]
                row[2] = override[1]
            insurance_rows.append(row)
            extra_covrlife += 1

    # ─── Augment with policies from LIFE.MBT ─────────────────────────────
    # DAT's HOLDNG snapshot is the primary source for life policies and
    # normally matches LIFE.MBT 1:1 for current-month active policies.
    # This loop is a defensive fallback: any LIFE.MBT entry whose policy_id
    # the DAT pass didn't already emit gets added so paid-up / dormant
    # policies don't silently vanish when DAT drops them.
    life_path = folder / "LIFE.MBT"
    extra_life = 0
    if life_path.exists():
        try:
            from .mbt import _read_text, _split_pipe
        except ImportError:
            from mbt import _read_text, _split_pipe  # type: ignore
        # No cross-source dedup — LIFE.MBT entries duplicate the DAT snapshot's
        # life policies by design (register vs active-holdings view). Surense
        # emits both; we now match that.
        seen_life: set[str] = set()
        for raw_line in _read_text(life_path).splitlines():
            if not raw_line.strip():
                continue
            cells = _split_pipe(raw_line)
            if len(cells) < 20:
                continue
            policy_id = (cells[10].lstrip("0") if cells[10] else "") or cells[10]
            if not policy_id or policy_id in seen_life:
                continue
            seen_life.add(policy_id)
            customer_short = _normalize_customer_id(cells[11])
            mbt_person = mbt_data["persons"].get(customer_short)
            insurance_rows.append(build_life_product_row(
                cells=cells,
                mbt_person=mbt_person,
                insurer_name=insurer_name,
                agent_num=agent_num,
            ))
            extra_life += 1

    wb = build_workbook(insurance_rows, coverage_rows, agent_number=agent_num)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)

    dat_count = len(insurance_rows) - extra_lifehlth - extra_covrlife - extra_life
    print(
        f"✓ wrote {len(insurance_rows)} policies "
        f"(DAT={dat_count}, "
        f"LIFEHLTH+={extra_lifehlth}, COVRLIFE+={extra_covrlife}, "
        f"LIFE+={extra_life}) "
        f"+ {len(coverage_rows)} coverages "
        f"to {out_path} (insurer={insurer_name}, agent={agent_num})",
        file=sys.stderr,
    )
    return 0


def main():
    p = argparse.ArgumentParser(
        description="Mimshak → production xlsx (Phase 1a)",
        epilog="Input can be either a folder of unzipped DAT+MBT files OR a .zip from the insurer.",
    )
    p.add_argument("input", type=Path, help="Folder OR .zip containing the DAT and MBT files")
    p.add_argument("--out", type=Path, default=None, help="Output xlsx path")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()

    if not args.input.exists():
        print(f"error: {args.input} does not exist", file=sys.stderr)
        sys.exit(2)

    out = args.out or (Path(__file__).parent / "out" / "production.xlsx")

    try:
        with _resolve_input(args.input) as folder:
            if args.verbose:
                print(f"→ using folder: {folder}", file=sys.stderr)
            rc = run(folder, out, verbose=args.verbose)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(2)
    sys.exit(rc)


if __name__ == "__main__":
    main()
