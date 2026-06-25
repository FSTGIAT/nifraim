#!/usr/bin/env python3
"""Search every MBT and DAT inside a Migdal Mimshak ZIP for given account/id
numbers. Reports exactly where each ID appears — file, row, column index, raw
cell value — so we can decide whether a "missing" record is truly absent or
the parser is looking at the wrong column.

Usage:
    python scripts/find_in_mimshak.py <zip-path> <id-or-policy> [<id-or-policy> ...]

Example (the 3 IDs the operator's notes claim are missing from the May 2026
ZIP — see .claude/projects/-home-roygi-test/next-session-mbt-dat-extract.md):
    python scripts/find_in_mimshak.py \\
        data/portal_downloads/d4b52f4a-85e4-4f41-bc97-8f3c9ac3ee8d/migdal_life.zip \\
        323338988 51695229 200104354

Matching rules — a "hit" is when any normalized form of the cell equals any
normalized form of the needle:
    raw      → exactly as stored
    digits   → only the digit chars (strips "01" prefix, dashes, slashes)
    stripped → digits with leading zeros removed

Standalone: stdlib only. No backend imports, no venv required.
"""

from __future__ import annotations

import io
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

_ENCODINGS = ("utf-8", "cp1255", "iso-8859-8", "latin-1")


def _decode(raw: bytes) -> str:
    for enc in _ENCODINGS:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace")


def _normalize_forms(s: str) -> set[str]:
    """All comparison forms for one cell or needle."""
    s = s.strip()
    digits = "".join(ch for ch in s if ch.isdigit())
    stripped = digits.lstrip("0") or ("0" if digits else "")
    forms = {s}
    if digits:
        forms.add(digits)
    if stripped:
        forms.add(stripped)
    return {f for f in forms if f}


def _scan_mbt(name: str, data: bytes, needle_forms: dict[str, set[str]]) -> list[dict]:
    """Pipe-delimited scan. Returns one hit per (needle, row, col)."""
    text = _decode(data)
    hits: list[dict] = []
    for row_idx, raw_line in enumerate(text.splitlines()):
        if not raw_line.strip():
            continue
        cells = [c.strip() for c in raw_line.split("|")]
        for col_idx, cell in enumerate(cells):
            if not cell:
                continue
            cell_forms = _normalize_forms(cell)
            for needle, nforms in needle_forms.items():
                if cell_forms & nforms:
                    hits.append({
                        "needle": needle,
                        "file": name,
                        "row": row_idx,
                        "col": col_idx,
                        "value": cell,
                        "row_summary": _row_snippet(cells),
                    })
    return hits


def _row_snippet(cells: list[str], max_cells: int = 6, max_len: int = 60) -> str:
    """Short readable summary of an MBT row — first few non-empty cells."""
    parts: list[str] = []
    for c in cells:
        if not c:
            continue
        v = c if len(c) <= max_len else c[: max_len - 1] + "…"
        parts.append(v)
        if len(parts) >= max_cells:
            break
    return " | ".join(parts)


def _scan_dat(name: str, data: bytes, needle_forms: dict[str, set[str]]) -> list[dict]:
    """XML walk. Match against every leaf text. Reports the local tag, the
    nearest customer/policy ancestor we can identify, and the value."""
    try:
        root = ET.parse(io.BytesIO(data)).getroot()
    except ET.ParseError as e:
        return [{
            "needle": "__error__", "file": name, "row": -1, "col": -1,
            "value": f"XML parse error: {e}", "row_summary": "",
        }]

    # Build parent map once for ancestor walking.
    parent = {id(c): p for p in root.iter() for c in p}

    def _local(tag: str) -> str:
        return tag.rsplit("}", 1)[-1] if "}" in tag else tag

    def _nearest_context(elem) -> str:
        """Walk up to find HeshbonOPolisa / YeshutLakoach for grounding."""
        cur = elem
        crumbs: list[str] = []
        while True:
            tag = _local(cur.tag)
            if tag in ("HeshbonOPolisa", "YeshutLakoach"):
                # Find a useful inner identifier
                for ident_tag in (
                    "MISPAR-POLISA-O-HESHBON",
                    "MISPAR-ZIHUY-LAKOACH",
                    "SHEM-MISHPACHA",
                ):
                    for d in cur.iter():
                        if _local(d.tag) == ident_tag and (d.text or "").strip():
                            crumbs.append(f"{tag}:{ident_tag}={d.text.strip()}")
                            break
                    if crumbs:
                        break
                if not crumbs:
                    crumbs.append(tag)
                break
            nxt = parent.get(id(cur))
            if nxt is None or nxt is cur:
                break
            cur = nxt
        return "/".join(reversed(crumbs)) or "<root>"

    hits: list[dict] = []
    for elem in root.iter():
        if list(elem):  # only leaves
            continue
        txt = (elem.text or "").strip()
        if not txt:
            continue
        cell_forms = _normalize_forms(txt)
        for needle, nforms in needle_forms.items():
            if cell_forms & nforms:
                hits.append({
                    "needle": needle,
                    "file": name,
                    "row": -1,
                    "col": _local(elem.tag),
                    "value": txt,
                    "row_summary": _nearest_context(elem),
                })
    return hits


def search(zip_path: Path, needles: list[str]) -> dict[str, list[dict]]:
    needle_forms = {n: _normalize_forms(n) for n in needles}
    grouped: dict[str, list[dict]] = defaultdict(list)

    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            data = zf.read(info)
            upper = info.filename.upper()
            if upper.endswith(".MBT"):
                hits = _scan_mbt(info.filename, data, needle_forms)
            elif upper.endswith(".DAT"):
                hits = _scan_dat(info.filename, data, needle_forms)
            else:
                continue
            for h in hits:
                grouped[h["needle"]].append(h)
    return grouped


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2

    zip_path = Path(argv[1])
    needles = argv[2:]
    if not zip_path.exists():
        print(f"ZIP not found: {zip_path}", file=sys.stderr)
        return 1

    grouped = search(zip_path, needles)

    print(f"ZIP: {zip_path}")
    print(f"Searching for {len(needles)} value(s): {', '.join(needles)}\n")

    for needle in needles:
        hits = grouped.get(needle, [])
        if hits:
            print(f"━━ {needle}  ({len(hits)} hit{'s' if len(hits) != 1 else ''}) ━━")
            # Group by file
            by_file: dict[str, list[dict]] = defaultdict(list)
            for h in hits:
                by_file[h["file"]].append(h)
            for fname, fhits in by_file.items():
                print(f"  {fname}  ({len(fhits)})")
                for h in fhits[:12]:  # cap noise per file
                    if isinstance(h["col"], int):
                        loc = f"row {h['row']} col {h['col']}"
                    else:
                        loc = f"<{h['col']}>"
                    print(f"    {loc:14}  value={h['value']!r}")
                    if h["row_summary"]:
                        print(f"                    ctx: {h['row_summary']}")
                if len(fhits) > 12:
                    print(f"    … +{len(fhits) - 12} more")
        else:
            print(f"━━ {needle}  ✗ NOT FOUND in any MBT or DAT")
        print()

    # Final summary line for scripting
    found = sum(1 for n in needles if grouped.get(n))
    print(f"Summary: {found}/{len(needles)} found")
    return 0 if found else 3


if __name__ == "__main__":
    sys.exit(main(sys.argv))
