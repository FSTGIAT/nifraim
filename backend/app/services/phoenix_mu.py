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
        01 (548)  client/policy HEADER — carries the 9-digit ת"ז (its own name
                  field really is blank) + dates.
        02 (284)  product/coverage rows — policy, amounts, the 4-digit product
                  code at [40:44], and (usually) the ת"ז.
        04 (308)  CLIENT record — ת"ז, NAME (visual Hebrew at [90:112]), birth
                  date, address. Long mis-read as a rider, which is why this
                  book was reported as nameless.
        03/05/17/19  riders/extra coverages (not emitted).

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
from app.utils.visual_hebrew import reverse_visual_hebrew

_MIN_REC = 200          # data records are ≥200 chars; lookup-table lines are short
_ID_SLICE = slice(172, 188)
_ACC_SLICE = slice(70, 75)          # 5 chars = whole shekels; [75:77] is a code, NOT cents
_POLICY_SLICE = slice(10, 16)

# 4-digit product code on an 02 row, keying the `09xxxx` lookup table.
# Verified against MU_NK_HAYV_MOSHE_2026_06: all 261 02-rows resolve.
_PRODUCT_CODE_SLICE = slice(40, 44)

# Client name on an 04 record — visual-order Hebrew, right-aligned, ending at
# 112 where the 8-digit birth date begins.
_NAME_SLICE = slice(90, 112)

_04_ID = re.compile(r"ז(\d{9})")
# The writer separates first and last name with run-of-spaces padding; a long
# name can squeeze that to a single space.
_NAME_GAP = re.compile(r"\s{2,}")


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


def _product_lookup(lines: list[str]) -> dict[str, str]:
    """The file's own product table: 4-digit code → logical product name.

    Short `09xxxx` lines carry a right-aligned visual-Hebrew name plus a
    trailing 2-digit product-family code:

        '090003         וקיזיר04'   ->  0003 = 'ריזיקו'   (family 04)
        '090004      םייח הרקמ03'   ->  0004 = 'מקרה חיים'

    Without this every 02 row was emitted as a flat 'ביטוח חיים', so an agent
    opening a client saw the same product name on every policy they own.
    """
    lut: dict[str, str] = {}
    for line in lines:
        if len(line) >= _MIN_REC or not line.startswith("09") or len(line) <= 6:
            continue
        code = line[2:6]
        if not code.isdigit():
            continue
        body = line[6:].rstrip()
        if body[-2:].isdigit():
            body = body[:-2]
        name = reverse_visual_hebrew(body)
        if name:
            lut.setdefault(code, name)
    return lut


def _split_name(logical: str) -> tuple[str, str]:
    """'ליאור   ניסימוב' → ('ליאור', 'ניסימוב')."""
    logical = (logical or "").strip()
    if not logical:
        return "", ""
    parts = [p for p in _NAME_GAP.split(logical) if p]
    if len(parts) >= 2:
        return parts[0], " ".join(parts[1:])
    bits = logical.split(" ", 1)
    return (bits[0], bits[1]) if len(bits) == 2 else (logical, "")


def _client_names(lines: list[str]) -> dict[str, tuple[str, str]]:
    """ת"ז → (first, last) from the 04 CLIENT records.

    The 01 header's name field really is blank, which is why this parser long
    reported the Phoenix book as nameless — but the names are simply held on a
    different record type. 04 was being skipped as a "rider"; it is in fact the
    client demographic row (name, birth date, address), and it covers 47 of the
    48 clients in the reference file — the one gap is a 000000000 placeholder.
    """
    out: dict[str, tuple[str, str]] = {}
    for line in lines:
        if len(line) < _MIN_REC or line[:2] != "04":
            continue
        m = _04_ID.search(line)
        if not m:
            continue
        first, last = _split_name(reverse_visual_hebrew(line[_NAME_SLICE]))
        if first or last:
            tz = m.group(1)
            out[tz.lstrip("0") or tz] = (first, last)
    return out


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

    products = _product_lookup(lines)
    names = _client_names(lines)

    records: list[dict] = []
    cur_id: str | None = None
    cur_date: str | None = None
    unknown_codes: set[str] = set()
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
            key = pid.lstrip("0") or pid
            code = line[_PRODUCT_CODE_SLICE]
            product = products.get(code)
            if not product:
                unknown_codes.add(code)
            first, last = names.get(key, ("", ""))
            records.append({
                "יצרן": "הפניקס",
                "סוג מוצר": "חיים",
                # The policy's OWN product, resolved through the file's lookup
                # table. Falls back to the family name only when a code is
                # genuinely absent from the table — never as the default.
                "מוצר": product or "ביטוח חיים",
                "מס' חשבון/פוליסה": policy.lstrip("0") or policy,
                "מספר ת.ז": key,
                "שם פרטי לקוח": first,
                "שם משפחה לקוח": last,
                'סה"כ פרמיה': None,           # accumulation-based book; premium not fabricated
                "צבירה": accum,
                "סטטוס מוצר": "פעיל",
                "תאריך הצטרפות למוצר": cur_date,
                "מספר סוכן": None,
            })

    named = sum(1 for r in records if r["שם פרטי לקוח"] or r["שם משפחה לקוח"])
    logger.info(
        "phoenix_mu: parsed %d production records (%d unique ids) from MU file; "
        "%d/%d named, %d products in lookup",
        len(records), len({r["מספר ת.ז"] for r in records}),
        named, len(records), len(products),
    )
    if unknown_codes:
        # Loud on purpose: a code missing from the table means a real product
        # is being reported under the generic family name.
        logger.warning("phoenix_mu: %d product code(s) not in the lookup table: %s",
                       len(unknown_codes), sorted(unknown_codes)[:10])
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
