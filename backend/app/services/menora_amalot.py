"""Menora מבטחים נפרעים (commission) CSV-in-ZIP parser.

The כספות (AgentFilesMaster) vault's **"דוח ניפרעים לסוכן"** report downloads as
an outer ZIP wrapping a single CP1255-encoded CSV
(`AmalotLife_<agent>_<date>_NS<...>.csv`). The CSV has a 3-line title preamble
("מנורה מבטחים ביטוח בע\"מ דו'ח נפרעים לסוכן" / "לתקופה : MM/YYYY" / "במדד : N")
above a 92-column header row.

That header carries the standard Menora commission signature
(`מספר ת.ז מבוטח/עמית` + `שם סוג עמלה`), so once we locate the header and read
the CSV into a DataFrame we hand it straight to
`parser_service._parse_menora` — identical field decoding to the xlsx variant.
Result routes as format `menora` → category `commission` → auto-compare.

Sibling of `mimshak` and `menora_legacy`: both are ZIP front-doors registered in
`upload_ingest._parse_zip_bundle`.
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from datetime import date

# Same two columns parser_service.detect_format() uses for the menora signature.
MENORA_AMALOT_SIGNATURE = {"מספר ת.ז מבוטח/עמית", "שם סוג עמלה"}
_ENCODINGS = ("cp1255", "utf-8-sig", "iso-8859-8")
_HEADER_SCAN_ROWS = 40


def _read_csv_member(content: bytes) -> str | None:
    """Return the decoded text of the single .csv member, or None if this isn't
    a ZIP / has no CSV inside."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile:
        return None
    csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    if not csv_names:
        return None
    raw = zf.read(csv_names[0])
    for enc in _ENCODINGS:
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("cp1255", errors="replace")


def _find_header_idx(rows: list[list[str]]) -> int | None:
    for i, r in enumerate(rows[:_HEADER_SCAN_ROWS]):
        if MENORA_AMALOT_SIGNATURE.issubset({c.strip() for c in r}):
            return i
    return None


# "לתקופה : 05/2026 עד- 05/2026" in the title preamble — the authoritative
# reporting period. Filename-based detection is unreliable here because the
# filename embeds a DD-MM-YYYY generation timestamp (e.g. `..._10-06-2026_...`)
# that detect_period_month misreads as month 10 / year 06.
_RE_PERIOD = re.compile(r"לתקופה\s*:?\s*(\d{1,2})\s*/\s*(\d{4})")


def _extract_period_month(rows: list[list[str]], hdr_idx: int) -> date | None:
    for r in rows[:hdr_idx]:
        line = " ".join(c for c in r if c and c.strip())
        m = _RE_PERIOD.search(line)
        if m:
            mm, yy = int(m.group(1)), int(m.group(2))
            try:
                return date(yy, mm, 1)
            except ValueError:
                return None
    return None


def is_menora_amalot_zip(content: bytes) -> bool:
    """True if `content` is a ZIP wrapping a Menora amalot/נפרעים CSV."""
    text = _read_csv_member(content)
    if not text:
        return False
    rows = list(csv.reader(io.StringIO(text)))
    return _find_header_idx(rows) is not None


def parse_menora_amalot_zip(content: bytes) -> dict:
    """Extract the CSV, locate the signature header row, and decode it through
    the shared Menora commission parser. Returns parse_excel()-shaped output:
        { "format": "menora", "company_source": "מנורה", "records": [...] }
    """
    import pandas as pd

    from app.services.parser_service import _parse_menora

    text = _read_csv_member(content)
    if not text:
        raise ValueError("Menora amalot ZIP: no .csv member found")

    rows = list(csv.reader(io.StringIO(text)))
    hdr_idx = _find_header_idx(rows)
    if hdr_idx is None:
        raise ValueError(
            "Menora amalot ZIP: signature header row "
            f"({MENORA_AMALOT_SIGNATURE}) not found in first {_HEADER_SCAN_ROWS} rows"
        )

    # dtype=str + keep_default_na=False → every cell is a clean string, matching
    # how _parse_menora expects to coerce (it runs parse_numeric/parse_date per
    # field). Header on the signature row; the title preamble above is skipped.
    df = pd.read_csv(
        io.StringIO(text), skiprows=hdr_idx, dtype=str, keep_default_na=False
    )
    df.columns = [str(c).strip() for c in df.columns]

    result = _parse_menora(df)
    # Authoritative period from the title preamble — overrides the unreliable
    # filename/data-date inference in detect_period_month (upload_ingest prefers
    # result["period_month"] when present).
    period = _extract_period_month(rows, hdr_idx)
    if period is not None:
        result["period_month"] = period
    return result
