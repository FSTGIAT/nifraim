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

    wb = build_workbook(insurance_rows, coverage_rows, agent_number=agent_num)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)

    print(
        f"✓ wrote {len(insurance_rows)} policies + {len(coverage_rows)} coverages "
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
