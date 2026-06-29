"""Phoenix terminal PRODUCTION parser — the option-13 ``MU_NK_HAYV`` file.

The Phoenix legacy PowerTerm terminal (agent.fnx.co.il) menu **option 13**
("הורדת קבצים ל-PC") KERMIT-downloads the agent's life book as a single dense
``MU_NK_HAYV_MOSHE_<period>`` file (CP862, visual-order Hebrew) into
``C:\\fnxbox``. Historically this needed a manual Mimshak desktop converter to
turn it into the ``.MBT`` set before `phoenix_terminal.py` could parse it. This
module parses the MU file **directly** into production-schema records so the
phoenix_terminal worker is fully hands-free — no external converter.

File layout (reverse-engineered against real exports, 2026-06-29):
  • Lookup tables — short lines prefixed ``09xxxx`` (and ``06xxxx`` …) mapping a
    code to a product name in visual-order (reversed) Hebrew, e.g.
    ``090001          ברועמ01`` → 0001 = "מעורב".
  • Data records — fixed-width lines ≥200 chars, typed by their 2-char prefix:
        01 (548)  client/policy HEADER — carries the 9-digit ת"ז (just before the
                  blank name field — the file holds NO customer names) + dates.
        02 (284)  product/coverage rows — policy, amounts, and (usually) the ת"ז.
        03/04/05/17/19  riders/extra coverages (not emitted).

  Confirmed 02 field offsets (0-indexed slices):
        [10:16]  policy / plan code
        [49:55]  amount A  (candidate annual premium — UNVERIFIED, left out)
        [70:75]  accumulation / policy value, WHOLE SHEKELS — no /100 (CONFIRMED:
                 "41479" echoed verbatim at [172:188]; the trailing [75:77] is a
                 product/rate code that only ever takes 17/25/45, not cents)
        [172:188] trailer holding the 9-digit ת"ז when present

Only the high-confidence fields are emitted: id_number (checksum-validated),
accumulation, policy, company="הפניקס". Premium stays None (the Phoenix savings
book is accumulation-based; we never fabricate a premium from an unverified
column). See memory phoenix_terminal_production.
"""

from __future__ import annotations

import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Same production schema as phoenix_terminal.py so detect_format → production and
# the two Phoenix terminal paths aggregate identically.
from app.services.phoenix_terminal import PRODUCTION_COLUMNS

_MIN_REC = 200          # data records are ≥200 chars; lookup-table lines are short
_ID_SLICE = slice(172, 188)
_ACC_SLICE = slice(70, 75)          # 5 chars = whole shekels; [75:77] is a code, NOT cents
_POLICY_SLICE = slice(10, 16)


def _valid_tz(s: str) -> bool:
    """Israeli ID (ת"ז) check-digit validation — filters junk 9-digit runs."""
    s = (s or "").zfill(9)
    if not s.isdigit() or s == "0" * 9:
        return False
    total = 0
    for i, ch in enumerate(s):
        d = int(ch) * (1 if i % 2 == 0 else 2)
        total += d if d < 10 else d - 9
    return total % 10 == 0


def _num(raw: str):
    """Accumulation field is already WHOLE SHEKELS (the echo at [172:188] proves
    no decimal scaling) — parse as an integer, NOT cents."""
    raw = (raw or "").strip()
    if not raw or not raw.isdigit():
        return None
    v = int(raw)
    return v if v else None


def _header_id(header: str) -> str | None:
    """The client ת"ז in an 01 header sits just before the blank name field."""
    for m in re.finditer(r"(\d{9})\s{8,}", header):
        if _valid_tz(m.group(1)):
            return m.group(1)
    for m in re.finditer(r"\d{9}", header):
        if _valid_tz(m.group(0)):
            return m.group(0)
    return None


def _own_id(rec: str) -> str | None:
    m = re.search(r"\d{9}", rec[_ID_SLICE])
    return m.group(0) if m and _valid_tz(m.group(0)) else None


def _join_date(header: str) -> str | None:
    """DDMMYYYY near the start of an 01 header → YYYY-MM-DD."""
    m = re.search(r"(\d{2})(\d{2})(\d{4})", header[16:24])
    if not m:
        return None
    dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
    if not ("19" <= yyyy[:2] <= "20" and "01" <= mm <= "12" and "01" <= dd <= "31"):
        return None
    return f"{yyyy}-{mm}-{dd}"


def parse_phoenix_mu(content: bytes) -> dict:
    """Parse the raw MU_NK_HAYV bytes into production-schema records.

    Returns {"format": "production", "company_source": "הפניקס", "records": [...]}.
    """
    txt = content.decode("cp862", errors="replace")
    lines = txt.split("\n")

    records: list[dict] = []
    cur_id: str | None = None
    cur_date: str | None = None
    for line in lines:
        if len(line) < _MIN_REC:
            continue
        kind = line[:2]
        if kind == "01":
            cur_id = _header_id(line)
            cur_date = _join_date(line)
        elif kind == "02":
            pid = _own_id(line) or cur_id
            if not pid or not _valid_tz(pid):
                continue
            accum = _num(line[_ACC_SLICE])
            policy = line[_POLICY_SLICE].strip()
            records.append({
                "יצרן": "הפניקס",
                "סוג מוצר": "חיים",
                "מוצר": "ביטוח חיים",
                "מס' חשבון/פוליסה": policy.lstrip("0") or policy,
                "מספר ת.ז": pid.lstrip("0") or pid,
                "שם פרטי לקוח": "",          # MU file carries no names
                "שם משפחה לקוח": "",
                'סה"כ פרמיה': None,           # accumulation-based book; premium not fabricated
                "צבירה": accum,
                "סטטוס מוצר": "פעיל",
                "תאריך הצטרפות למוצר": cur_date,
                "מספר סוכן": None,
            })

    logger.info("phoenix_mu: parsed %d production records (%d unique ids) from MU file",
                len(records), len({r["מספר ת.ז"] for r in records}))
    return {"format": "production", "company_source": "הפניקס", "records": records}


def is_phoenix_mu(content: bytes) -> bool:
    """Sniff the MU_NK_HAYV format: CP862 with the 090001 product-table marker."""
    head = content[:4000].decode("cp862", errors="replace")
    return "090001" in head and "090002" in head


def build_phoenix_mu_production_xlsx(mu_path: Path, out_path: Path) -> Path:
    """Parse the MU file and write a production-schema xlsx (same shape as
    phoenix_terminal.build_phoenix_production_xlsx, so ingest routes it as
    production/הפניקס)."""
    import pandas as pd

    content = Path(mu_path).read_bytes()
    parsed = parse_phoenix_mu(content)
    records = parsed["records"]
    if not records:
        raise RuntimeError(f"phoenix_mu: no production records parsed from {mu_path}")
    df = pd.DataFrame(records, columns=PRODUCTION_COLUMNS)
    out_path = Path(out_path)
    df.to_excel(out_path, index=False)
    logger.info("phoenix_mu: wrote %d rows → %s", len(df), out_path.name)
    return out_path
