"""Menora legacy "תקן 4-era" production parser.

The Menora כספות AgentFilesMaster vault delivers production data as an
outer ZIP containing inner files NAMED `.ARJ` but actually standard ZIPs
(misnamed for legacy compatibility). Each inner ZIP holds:

    *.ALL   — CP1255 lookup tables (banks, branches, status codes)
    NNNNNN613M.TXT   — short summary records (1/policy)
    NNNNNN613N.TXT   — transaction detail (multiple/policy)
    NNNNNN613G.TXT   — financial summary (1/policy)
    NNNNNN613P.TXT   — policy + customer master (1/policy)  ← we parse this

No public field-position spec exists. Positions below were reverse-engineered
from 80-line sample bundles delivered 2026-05. Fields are conservative:

    id_number  : reliable (positioned + check-digit pattern)
    birthdate  : reliable (8-digit YYYYMMDD)
    name       : reliable (Hebrew, CP1255)
    policy id  : reliable (7-digit prefix)
    premium    : best-effort (regex over amount block)
    accumulation : best-effort

Premium/accumulation should be treated as approximate until anchored against
a known good sample from Menora's own dashboard.

Public API:
    is_menora_legacy_zip(zip_bytes) -> bool
    parse_menora_legacy_zip(zip_bytes) -> dict  (parse_excel-shaped result)
"""

from __future__ import annotations

import io
import logging
import re
import zipfile

logger = logging.getLogger(__name__)


def is_menora_legacy_zip(zip_bytes: bytes) -> bool:
    """True iff the outer ZIP contains files named `.ARJ` that are themselves
    ZIPs holding the Menora legacy P.TXT / G.TXT structure."""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as outer:
            arj_names = [n for n in outer.namelist() if n.lower().endswith(".arj")]
            if not arj_names:
                return False
            # Verify first ARJ is actually a ZIP (Menora misnames them)
            inner_bytes = outer.read(arj_names[0])
            if inner_bytes[:4] != b"PK\x03\x04":
                return False
            with zipfile.ZipFile(io.BytesIO(inner_bytes)) as inner:
                names = [n.upper() for n in inner.namelist()]
                # Signature: a *P.TXT or *G.TXT file present
                return any(n.endswith("P.TXT") or n.endswith("G.TXT") for n in names)
    except zipfile.BadZipFile:
        return False
    except Exception:
        return False


def parse_menora_legacy_zip(zip_bytes: bytes) -> dict:
    """Parse a Menora legacy production ZIP.

    Returns parser_service.parse_excel()-shaped dict:
        { "format": "production",
          "company_source": "מנורה",
          "records": [{...}, ...] }
    """
    if not is_menora_legacy_zip(zip_bytes):
        raise ValueError(
            "Not a Menora legacy bundle — expected ZIP containing inner "
            "ZIPs (named .ARJ) with *P.TXT/G.TXT fixed-width records"
        )

    records: list[dict] = []
    # Latest data-date across the bundle, derived from inner ARJ filenames
    # like `...-24_05_2026-07_47_23.ARJ` → 2026-05-24. Propagated to every
    # record's `processing_date` so detect_period_month can pick it up
    # without needing the outer zip filename to carry the month.
    latest_date: str | None = None

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as outer:
        arj_names = [n for n in outer.namelist() if n.lower().endswith(".arj")]
        for arj_name in arj_names:
            m = re.search(r"(\d{2})_(\d{2})_(\d{4})", arj_name)
            if m:
                iso = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
                if latest_date is None or iso > latest_date:
                    latest_date = iso
            inner_bytes = outer.read(arj_name)
            try:
                with zipfile.ZipFile(io.BytesIO(inner_bytes)) as inner:
                    inner_records = _parse_inner_bundle(inner, source_name=arj_name)
                    records.extend(inner_records)
            except zipfile.BadZipFile:
                logger.warning("menora_legacy: %s is not a valid ZIP, skipping", arj_name)
                continue

    if latest_date:
        for r in records:
            r.setdefault("processing_date", latest_date)

    logger.info(
        "menora_legacy: parsed %d production records from %d inner bundle(s) (date=%s)",
        len(records), len(arj_names), latest_date or "n/a",
    )

    return {
        "format": "production",
        "company_source": "מנורה",
        "records": records,
    }


# ────────────────────────────────────────────────────────────────────────────
# Internal: per-bundle parsing
# ────────────────────────────────────────────────────────────────────────────


def _parse_inner_bundle(inner: zipfile.ZipFile, *, source_name: str) -> list[dict]:
    """Extract production records from one inner Menora bundle.

    Reads P.TXT (customer master) for id/name/policy and joins G.TXT
    (financial summary) by policy_id where available.
    """
    p_txt: str | None = None
    g_txt: str | None = None

    # Menora legacy files use CP862 (DOS Hebrew, visual order) — NOT CP1255.
    # CP862 stores letters in display (LTR) order, so the decoded Unicode
    # string needs to be reversed per-field to match logical Hebrew.
    for n in inner.namelist():
        up = n.upper()
        if up.endswith("P.TXT") and p_txt is None:
            p_txt = inner.read(n).decode("cp862", errors="replace")
        elif up.endswith("G.TXT") and g_txt is None:
            g_txt = inner.read(n).decode("cp862", errors="replace")

    if not p_txt:
        logger.warning("menora_legacy: %s has no P.TXT, skipping", source_name)
        return []

    # G.TXT keyed by policy_id (7-digit positions 4-11) so we can fill in
    # amounts on P.TXT rows
    g_by_policy: dict[str, dict] = {}
    if g_txt:
        for line in g_txt.split("\r\n"):
            if not line.strip():
                continue
            policy = line[4:11].strip()
            if not policy:
                continue
            g_by_policy[policy] = _parse_g_line(line)

    out: list[dict] = []
    for line in p_txt.split("\r\n"):
        if not line.strip() or len(line) < 60:
            continue
        rec = _parse_p_line(line)
        if not rec or not rec.get("id_number"):
            continue
        # Enrich with financial fields when G.TXT has a matching policy
        g = g_by_policy.get(rec.get("fund_policy_number") or "", {})
        for k, v in g.items():
            if v is not None and rec.get(k) is None:
                rec[k] = v
        out.append(rec)
    return out


# ────────────────────────────────────────────────────────────────────────────
# Field-position parsers (P.TXT, G.TXT)
# Reverse-engineered from 80-row sample bundles 2026-05-31.
# Positions verified against multiple rows; comments cite L0 as example.
# ────────────────────────────────────────────────────────────────────────────


def _parse_p_line(line: str) -> dict | None:
    """Parse one row of P.TXT (customer + policy master).

    Reference row:
        06361004450400800000000100690000000000002238945619680121יחיים יבכוב...

        pos 0-3    : record-type prefix (0636/0635/0634)
        pos 4-10   : 7-digit policy number
        pos 11     : '4' (constant)
        pos 12-14  : '008'
        pos 15-27  : agent code embedded (e.g. ...0069 = agent 0069)
        pos 28-37  : ten zeros
        pos 38-47  : 10-digit (9-digit id_number + 1 check digit)
        pos 48-55  : 8-digit birthdate YYYYMMDD
        pos 56-78  : Hebrew name (22 chars, space-padded)
    """
    try:
        policy_number = line[4:11].strip()
        id_raw = line[38:47]  # 9-digit + check
        dob_raw = line[48:56]
        name_raw = line[56:78]

        # Sanity: id_number must be all digits
        if not id_raw.isdigit():
            return None
        # Strip leading zeros for the canonical id_number
        id_number = id_raw.lstrip("0") or id_raw

        # Birthdate (validate as YYYYMMDD)
        birth = None
        if dob_raw.isdigit() and len(dob_raw) == 8:
            yyyy, mm, dd = dob_raw[:4], dob_raw[4:6], dob_raw[6:]
            if 1900 <= int(yyyy) <= 2100 and 1 <= int(mm) <= 12 and 1 <= int(dd) <= 31:
                birth = f"{yyyy}-{mm}-{dd}"

        # CP862 stores Hebrew in display order — reverse to get logical
        # Unicode that renders correctly. Example: bytes y-ch-y-l-m → CP862
        # decoded "יחילמ" → reversed "מליחי" (the real surname).
        # Reverse the whole field then split — preserves word grouping and
        # gives proper RTL rendering downstream.
        name_logical = name_raw.strip()[::-1].strip()
        parts = name_logical.split(None, 1)
        # Menora convention: surname first, then first name. Map to schema.
        if len(parts) >= 2:
            last_name = parts[0]
            first_name = parts[1]
        elif parts:
            last_name = parts[0]
            first_name = None
        else:
            last_name = None
            first_name = None

        return {
            "id_number": id_number,
            "first_name": first_name,
            "last_name": last_name,
            "fund_policy_number": policy_number or None,
            "receiving_company": "מנורה",
            "product_type": "ביטוח חיים",
            "product": "פרודוקציה - חיים",
            "is_active": "פעיל",
            "reconciliation_status": "no_data",
        }
    except Exception as e:
        logger.debug("menora_legacy: P.TXT line parse failed: %s", e)
        return None


def _parse_g_line(line: str) -> dict:
    """Parse one row of G.TXT (financial summary, joined by policy_id).

    Verified on 80-row sample bundles 2026-05-31:

        pos 150-163 (13 chars): annual_premium  `0000002739.96`
        pos 163-174 (11 chars): monthly_premium (annual / 12) — ignored

    Positions before 150 hold the constant prefix + policy face/coverage
    block (large value like 5,000,000 or 3,500,000,000 — NOT premium).

    For `חיים פרודוקציה ישן` (life-insurance) bundles, G.TXT has NO
    accumulation column — life insurance is pure protection. We leave
    accumulation None; future pension/savings bundles need a separate
    parser branch.
    """
    try:
        if len(line) < 163:
            return {}
        annual_raw = line[150:163].strip()
        if not annual_raw:
            return {}
        annual = float(annual_raw)
        if annual > 0:
            return {"total_premium": annual}
        return {}
    except (ValueError, IndexError):
        return {}


__all__ = ["is_menora_legacy_zip", "parse_menora_legacy_zip"]
