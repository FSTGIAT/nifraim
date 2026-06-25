#!/usr/bin/env python3
"""Dump every MBT + DAT file from a Migdal Mimshak bundle to one xlsx.

One sheet per source file:
  LIFE.MBT, LIFEHLTH.MBT, COVRLIFE.MBT, PERSON.MBT, AGENTS.MBT, COMPANY.MBT, DAT

For MBT (pipe-delimited): one row per source row, one column per cell.
For DAT (XML): one row per HeshbonOPolisa, flattened leaves as columns.

Hebrew cells stored in visual order get a second column showing the logical-
order (readable) form, so you can eyeball names directly.

Usage:
    python scripts/dump_mimshak_raw.py <zip-or-folder> [--out OUT.xlsx]

Defaults to the May 2026 Migdal bundle in data/portal_downloads/.
"""

from __future__ import annotations

import argparse
import io
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

# Columns in each MBT file that hold visual-order Hebrew text (need reversal
# to be readable). Indexes verified from the May 2026 Migdal sample.
HEBREW_COLS = {
    "LIFE.MBT":     [14],                              # customer name
    "LIFEHLTH.MBT": [14],                              # insured name
    "COVRLIFE.MBT": [19],                              # coverage / rider name
    "PERSON.MBT":   [4, 15, 16, 24, 25],               # role, address, city, last, first
}

_ENCODINGS = ("utf-8", "cp1255", "iso-8859-8", "latin-1")


def _decode(raw: bytes) -> str:
    for enc in _ENCODINGS:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace")


def _reverse_hebrew_runs(s: str) -> str:
    """Reverse runs of Hebrew characters within a string (visual→logical)."""
    if not s or not any("֐" <= c <= "׿" for c in s):
        return s
    out, buf = [], []
    for c in s:
        if "֐" <= c <= "׿" or c == " ":
            buf.append(c)
        else:
            if buf:
                out.append("".join(reversed(buf)))
                buf = []
            out.append(c)
    if buf:
        out.append("".join(reversed(buf)))
    return "".join(out).strip()


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


# ── Sheet writers ────────────────────────────────────────────────────────

HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="2F5597")


def _style_header(ws, ncols: int) -> None:
    for c in range(1, ncols + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.freeze_panes = "A2"


def _autosize(ws, max_width: int = 40) -> None:
    for col_cells in ws.columns:
        if not col_cells:
            continue
        letter = get_column_letter(col_cells[0].column)
        longest = max((len(str(c.value)) for c in col_cells if c.value is not None), default=8)
        ws.column_dimensions[letter].width = min(max(longest + 2, 8), max_width)


def write_mbt_sheet(wb: Workbook, name: str, data: bytes) -> int:
    text = _decode(data)
    rows = [ln for ln in text.splitlines() if ln.strip()]
    if not rows and not text.strip():
        ws = wb.create_sheet(name)
        ws["A1"] = "(empty file)"
        return 0

    # If MBT has no row separators (e.g. AGENTS.MBT is newline-list of agent
    # codes), fall back to one row per line.
    if "|" not in rows[0] if rows else False:
        ws = wb.create_sheet(name)
        ws.append(["row", "value"])
        for i, ln in enumerate(rows, 1):
            ws.append([i, ln])
        _style_header(ws, 2)
        _autosize(ws)
        return len(rows)

    cell_grid = [[c.strip() for c in ln.split("|")] for ln in rows]
    ncols = max(len(r) for r in cell_grid)
    heb_cols = HEBREW_COLS.get(name, [])

    ws = wb.create_sheet(name)
    # Headers: col 0, col 1, …; add a parallel "col_N (logical)" for each
    # visual-Hebrew column so the reader can see readable names.
    headers = []
    for i in range(ncols):
        headers.append(f"col {i}")
        if i in heb_cols:
            headers.append(f"col {i} (logical)")
    ws.append(headers)
    _style_header(ws, len(headers))

    for r in cell_grid:
        row_out = []
        for i in range(ncols):
            v = r[i] if i < len(r) else ""
            row_out.append(v)
            if i in heb_cols:
                row_out.append(_reverse_hebrew_runs(v))
        ws.append(row_out)

    _autosize(ws)
    return len(rows)


def write_dat_sheet(wb: Workbook, name: str, data: bytes) -> int:
    """For DAT: one row per HeshbonOPolisa, columns = every distinct leaf
    tag seen across all policies. Union of leaves so nothing is hidden."""
    try:
        root = ET.parse(io.BytesIO(data)).getroot()
    except ET.ParseError as e:
        ws = wb.create_sheet(name)
        ws["A1"] = f"XML parse error: {e}"
        return 0

    # Build parent map to attach customer context
    parent = {id(c): p for p in root.iter() for c in p}

    policies: list[dict[str, str]] = []
    for pol in root.iter():
        if _local(pol.tag) != "HeshbonOPolisa":
            continue
        row: dict[str, str] = {}
        for d in pol.iter():
            if list(d):
                continue
            tag = _local(d.tag)
            v = (d.text or "").strip()
            if v and tag not in row:
                row[tag] = v
        # Walk up to nearest YeshutLakoach for customer name
        cur = pol
        while id(cur) in parent:
            cur = parent[id(cur)]
            if _local(cur.tag) == "YeshutLakoach":
                for d in cur.iter():
                    if list(d):
                        continue
                    tag = _local(d.tag)
                    if tag in ("SHEM-PRATI", "SHEM-MISHPACHA", "TAARICH-LEYDA", "MIN"):
                        row.setdefault(f"customer_{tag}", (d.text or "").strip())
                break
        policies.append(row)

    if not policies:
        ws = wb.create_sheet(name)
        ws["A1"] = "(no HeshbonOPolisa nodes)"
        return 0

    # Union of all keys, preferring the most meaningful order
    priority = [
        "MISPAR-POLISA-O-HESHBON", "MISPAR-ZIHUY-LAKOACH",
        "customer_SHEM-PRATI", "customer_SHEM-MISHPACHA",
        "SHEM-TOCHNIT", "SUG-MUTZAR", "STATUS-POLISA-O-CHESHBON",
        "TAARICH-HITZTARFUT-RISHON", "TAARICH-IDKUN-STATUS",
        "SCHUM-BITUACH", "DMEI-NIHUL-ACHIDIM",
    ]
    all_keys = list(priority)
    seen = set(priority)
    for p in policies:
        for k in p.keys():
            if k not in seen:
                all_keys.append(k)
                seen.add(k)

    ws = wb.create_sheet(name)
    ws.append(all_keys)
    _style_header(ws, len(all_keys))
    for p in policies:
        ws.append([p.get(k, "") for k in all_keys])
    _autosize(ws)
    return len(policies)


# ── Driver ───────────────────────────────────────────────────────────────

def resolve_input(path: Path):
    """Return a folder path containing the MBT + DAT files."""
    if path.is_dir():
        return path, None
    if path.is_file() and path.suffix.lower() == ".zip":
        tmp = tempfile.mkdtemp(prefix="mimshak_raw_")
        tmp_path = Path(tmp)
        with zipfile.ZipFile(path) as zf:
            zf.extractall(tmp_path)
        # Unwrap single-subfolder
        contents = list(tmp_path.iterdir())
        if len(contents) == 1 and contents[0].is_dir():
            return contents[0], tmp_path
        return tmp_path, tmp_path
    raise ValueError(f"{path}: not a folder or .zip")


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", nargs="?", type=Path,
                   default=Path("data/portal_downloads/d4b52f4a-85e4-4f41-bc97-8f3c9ac3ee8d/migdal_life.zip"))
    p.add_argument("--out", type=Path,
                   default=Path("/tmp/migdal_raw_dump.xlsx"))
    args = p.parse_args(argv[1:])

    folder, cleanup = resolve_input(args.input)
    print(f"Input:  {args.input}")
    print(f"Reading from: {folder}")
    print(f"Output: {args.out}\n")

    wb = Workbook()
    # Remove the default sheet
    wb.remove(wb.active)

    # Fixed order so the workbook always reads the same way
    mbt_order = ["LIFE.MBT", "LIFEHLTH.MBT", "COVRLIFE.MBT", "PERSON.MBT", "AGENTS.MBT", "COMPANY.MBT"]
    summary = []

    for name in mbt_order:
        path = folder / name
        if not path.exists():
            print(f"  (skipped — not present) {name}")
            continue
        n = write_mbt_sheet(wb, name, path.read_bytes())
        summary.append((name, n))
        print(f"  {name:18}  {n:>4} rows")

    # DAT files — there can be multiple (monthly snapshots); pick the latest
    dat_files = sorted(folder.glob("*.DAT")) + sorted(folder.glob("*.dat"))
    if dat_files:
        latest = dat_files[-1]   # lexicographic sort = chronological for HOLDNG names
        n = write_dat_sheet(wb, "DAT", latest.read_bytes())
        summary.append(("DAT (latest)", n))
        print(f"  DAT (latest)        {n:>4} policies  ({latest.name})")
        # If more than 1 DAT, dump the others as additional sheets named by date
        for extra in dat_files[:-1]:
            tag = "DAT_" + extra.name[-21:-13]  # YYYYMMDD chunk
            n = write_dat_sheet(wb, tag, extra.read_bytes())
            summary.append((tag, n))
            print(f"  {tag:18}  {n:>4} policies  ({extra.name})")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(args.out)

    print(f"\nWrote {args.out}  ({args.out.stat().st_size} bytes)")
    print(f"  {len(summary)} sheet(s):")
    for name, n in summary:
        print(f"    {name:22} {n} rows/policies")

    if cleanup:
        import shutil
        shutil.rmtree(cleanup, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
