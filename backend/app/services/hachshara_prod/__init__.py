"""Hachshara (הכשרה) production parser — the emailed `Ild_prod_*.zip` bundle.

Hachshara does not expose production in its agent portal (the portal plugin
`portal_automation/companies/hachshara.py` downloads only נפרעים). Production is
emailed to the agent as a ZIP named

    Ild_prod_<n>_<agent>_<DDMMYYYY>.zip     e.g. Ild_prod_1_09344_30042026.zip

holding CP862, fixed-width 2000-char, CRLF-terminated members:

    SP<agent>     customer master   — id, names, start date, accumulation
    SB<agent>     policy financial  — id, start date, product name
    RM<agent>.NNR fund holdings     — id, repeating (fund name, amount) blocks
    RP<agent>     all-blank in the 2026-04 sample (no data for this agent)
    RB<agent>     all-blank

Positions were reverse-engineered from the 2026-04 sample (6 clients, one agent).
Re-verify against a second month before trusting them broadly.

Two fields the rest of the app expects DO NOT EXIST in this file. An exhaustive
6- and 7-digit sliding-window intersection across SP ∩ SB ∩ RM found the national
ID as the only key the three members share:

    total_premium       — every candidate block is zeros
    fund_policy_number  — absent entirely

Both stay None. Do not synthesise them (cf. `phoenix_mu.py`, which leaves premium
None rather than fabricating). The consequence is known and accepted:
`comparison_service._match_products` keys on fund_policy_number, so Hachshara
customers match by ID while their products land in `unmatched_prod`.

Scaling, the highest-impact numeric trap:
    SP accumulation [350:358] — WHOLE SHEKELS, no /100
    RM fund amounts (15 digits) — AGOROT, /100
`_cross_check_accumulation` logs when the two disagree beyond valuation drift.

Public API:
    is_hachshara_prod_zip(zip_bytes) -> bool
    parse_hachshara_prod_zip(zip_bytes, filename) -> dict  (parse_excel-shaped)
"""

from __future__ import annotations

import io
import logging
import re
import zipfile
from datetime import date

from app.utils.visual_hebrew import reverse_visual_hebrew

logger = logging.getLogger(__name__)

COMPANY = "הכשרה"

# Record layout — offsets into the 2000-char fixed-width line.
# The ID is a zero-padded 9-digit field: SP/SB at [6:15], RM at [0:9].
_SP_ID = slice(6, 15)
_SP_LAST_NAME = slice(43, 58)
_SP_FIRST_NAME = slice(58, 73)
_SP_SIGN_DATE = slice(342, 350)      # DDMMYYYY
_SP_ACCUMULATION = slice(350, 358)   # whole shekels; echoed at [543:551]

_SB_ID = slice(6, 15)
_SB_PRODUCT = slice(125, 150)

_RM_ID = slice(0, 9)
# Fund holdings repeat from offset 85 with stride 30: 15-char visual-Hebrew
# fund name, then a 15-digit amount in agorot. Count varies per client (1..3 in
# the sample), so scan rather than hard-slice.
_RM_FUNDS_START = 85
_RM_FUND_STRIDE = 30
_RM_FUND_NAME_LEN = 15

# Accumulation is a month-end snapshot while the fund amounts are valued on
# their own date, so they legitimately differ by a little. 0.5% catches a
# shekel/agorot scaling error (which would be 100x) without crying at drift.
_ACC_DRIFT_TOLERANCE = 0.005

# Chars that a legacy DOS writer leaves in logical (LTR) order inside an
# otherwise visual-order Hebrew field: digits and their separators.
_LTR_RUN = re.compile(r"[0-9]+(?:[./\-][0-9]+)*")

_FILENAME_DATE = re.compile(r"_(\d{2})(\d{2})(\d{4})(?:\.zip)?$", re.IGNORECASE)
_FILENAME_AGENT = re.compile(r"_(\d{4,6})_\d{8}(?:\.zip)?$", re.IGNORECASE)


def is_hachshara_prod_zip(zip_bytes: bytes) -> bool:
    """True iff the ZIP holds the Hachshara SP/RM fixed-width member pair.

    Members are bare names with no extension, which separates this cleanly from
    the Mimshak (.DAT/.MBT), Menora legacy (.ARJ) and Menora amalot (CSV)
    bundles that share the `_parse_zip_bundle` front door. Require BOTH SP and
    RM so a stray archive cannot false-positive.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            names = [n.rsplit("/", 1)[-1].upper() for n in z.namelist()]
            has_sp = any(n.startswith("SP") for n in names)
            has_rm = any(n.startswith("RM") for n in names)
            return has_sp and has_rm
    except zipfile.BadZipFile:
        return False
    except Exception:
        return False


def parse_hachshara_prod_zip(zip_bytes: bytes, filename: str | None = None) -> dict:
    """Parse a Hachshara emailed production ZIP into parse_excel()-shaped output.

    `filename` carries the authoritative data-date (the records do not), so the
    caller must pass it. `_parse_zip_bundle` already has it in scope.
    """
    if not is_hachshara_prod_zip(zip_bytes):
        raise ValueError(
            "Not a Hachshara production bundle — expected a ZIP holding "
            "fixed-width SP*/RM* members (e.g. Ild_prod_1_09344_30042026.zip)"
        )

    members = _read_members(zip_bytes)
    data_date = _data_date_from_filename(filename)
    agent_number = _agent_from_filename(filename)

    by_id: dict[str, dict] = {}

    # SP is the master: it alone decides which clients exist.
    for line in members.get("SP", []):
        rec = _parse_sp_line(line)
        if rec:
            by_id[rec["id_number"]] = rec

    for line in members.get("SB", []):
        sb = _parse_sb_line(line)
        if sb and sb["id_number"] in by_id:
            target = by_id[sb["id_number"]]
            for k, v in sb.items():
                if v is not None:
                    target[k] = v

    for line in members.get("RM", []):
        rm = _parse_rm_line(line)
        if rm and rm["id_number"] in by_id:
            target = by_id[rm["id_number"]]
            if rm["dominant_fund"]:
                target["track"] = rm["dominant_fund"]
                target["fund_type"] = rm["dominant_fund"]
            _cross_check_accumulation(target, rm["funds_total"])

    records = list(by_id.values())
    odd_ids = [r["id_number"] for r in records if not _valid_tz(r["id_number"])]
    if odd_ids:
        # Expected — Hachshara books non-TZ identifiers too. Surfaced because a
        # sudden jump toward "all IDs invalid" means the field offset has moved.
        logger.info(
            "hachshara_prod: %d/%d ids fail the TZ check digit (e.g. %s)",
            len(odd_ids), len(records), odd_ids[0],
        )

    for rec in records:
        rec["receiving_company"] = COMPANY
        rec["is_active"] = "פעיל"
        rec["reconciliation_status"] = "no_data"
        # Absent from the source file — never fabricated. See module docstring.
        rec["total_premium"] = None
        rec["fund_policy_number"] = None
        if agent_number:
            rec["agent_number"] = agent_number
        if data_date:
            rec["processing_date"] = data_date.isoformat()

    logger.info(
        "hachshara_prod: parsed %d production records (agent=%s, data_date=%s)",
        len(records), agent_number or "n/a", data_date.isoformat() if data_date else "n/a",
    )

    return {
        "format": "production",
        "company_source": COMPANY,
        "records": records,
        "period_month": date(data_date.year, data_date.month, 1) if data_date else None,
    }


# ────────────────────────────────────────────────────────────────────────────
# Visual-order Hebrew
# ────────────────────────────────────────────────────────────────────────────


# Promoted to app/utils/visual_hebrew.py so phoenix_mu can use the same
# run-aware implementation instead of a naive [::-1]. Kept as a module-local
# alias because the SP/SB/RM parsers below reference it by this name.
_reverse_visual_hebrew = reverse_visual_hebrew


# ────────────────────────────────────────────────────────────────────────────
# Member reading + filename metadata
# ────────────────────────────────────────────────────────────────────────────


def _read_members(zip_bytes: bytes) -> dict[str, list[str]]:
    """Decode each member to CP862 text lines, keyed by its 2-letter record type.

    RP/RB are all-blank for this agent; they yield zero lines and must never raise.
    """
    out: dict[str, list[str]] = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        for name in z.namelist():
            base = name.rsplit("/", 1)[-1].upper()
            kind = base[:2]
            if kind not in ("SP", "SB", "RM", "RP", "RB"):
                continue
            text = z.read(name).decode("cp862", errors="replace")
            lines = [ln for ln in text.replace("\r\n", "\n").split("\n") if ln.strip()]
            out.setdefault(kind, []).extend(lines)
    return out


def _data_date_from_filename(filename: str | None) -> date | None:
    """`Ild_prod_1_09344_30042026.zip` -> date(2026, 4, 30)."""
    if not filename:
        return None
    m = _FILENAME_DATE.search(filename.strip())
    if not m:
        return None
    dd, mm, yyyy = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return date(yyyy, mm, dd)
    except ValueError:
        return None


def _agent_from_filename(filename: str | None) -> str | None:
    if not filename:
        return None
    m = _FILENAME_AGENT.search(filename.strip())
    return m.group(1) if m else None


# ────────────────────────────────────────────────────────────────────────────
# Field parsers
# ────────────────────────────────────────────────────────────────────────────


def _valid_tz(s: str) -> bool:
    """Israeli ID (ת"ז) check-digit validation."""
    s = (s or "").zfill(9)
    if not s.isdigit() or s == "0" * 9:
        return False
    total = 0
    for i, ch in enumerate(s):
        d = int(ch) * (1 if i % 2 == 0 else 2)
        total += d if d < 10 else d - 9
    return total % 10 == 0


def _id_at(line: str, where: slice) -> str | None:
    """Read the zero-padded 9-digit ID field.

    Deliberately NOT gated on `_valid_tz`, unlike `phoenix_mu`, which scans for a
    9-digit run anywhere in the record and needs the check digit to reject junk.
    Here the field is at a fixed offset, so position already disambiguates — and
    3 of the 6 clients in the 2026-04 sample carry IDs that fail the check digit
    (Hachshara also books non-TZ identifiers). Gating on it would silently drop
    half the customer file.
    """
    raw = line[where].strip()
    if not raw.isdigit() or len(raw) != 9 or raw == "0" * 9:
        return None
    # Production drops leading zeros; commission keeps them. Normalising here
    # is what lets compute_comparison reconcile the two sides.
    return raw.lstrip("0") or "0"


def _ddmmyyyy(raw: str) -> date | None:
    raw = (raw or "").strip()
    if len(raw) != 8 or not raw.isdigit():
        return None
    try:
        return date(int(raw[4:]), int(raw[2:4]), int(raw[:2]))
    except ValueError:
        return None


def _shekels(raw: str) -> float | None:
    raw = (raw or "").strip()
    if not raw.isdigit():
        return None
    return float(int(raw)) or None


def _agorot(raw: str) -> float | None:
    raw = (raw or "").strip()
    if not raw.isdigit():
        return None
    return (int(raw) / 100.0) or None


def _parse_sp_line(line: str) -> dict | None:
    """Customer master — the only member that decides a client exists."""
    id_number = _id_at(line, _SP_ID)
    if not id_number:
        return None
    return {
        "id_number": id_number,
        "first_name": _reverse_visual_hebrew(line[_SP_FIRST_NAME]) or None,
        "last_name": _reverse_visual_hebrew(line[_SP_LAST_NAME]) or None,
        "sign_date": _ddmmyyyy(line[_SP_SIGN_DATE]),
        "accumulation": _shekels(line[_SP_ACCUMULATION]),
    }


def _parse_sb_line(line: str) -> dict | None:
    """Policy financial — contributes the product name."""
    id_number = _id_at(line, _SB_ID)
    if not id_number:
        return None
    return {
        "id_number": id_number,
        "product": _reverse_visual_hebrew(line[_SB_PRODUCT]) or None,
    }


def _parse_rm_line(line: str) -> dict | None:
    """Fund holdings — variable-count (name, agorot) blocks from offset 85."""
    id_number = _id_at(line, _RM_ID)
    if not id_number:
        return None

    funds: list[tuple[str, float]] = []
    off = _RM_FUNDS_START
    while off + _RM_FUND_STRIDE <= len(line):
        name = _reverse_visual_hebrew(line[off:off + _RM_FUND_NAME_LEN])
        amount = _agorot(line[off + _RM_FUND_NAME_LEN:off + _RM_FUND_STRIDE])
        if name and amount:
            funds.append((name, amount))
        off += _RM_FUND_STRIDE

    dominant = max(funds, key=lambda f: f[1])[0] if funds else None
    return {
        "id_number": id_number,
        "dominant_fund": dominant,
        "funds_total": sum(a for _, a in funds) if funds else None,
    }


def _cross_check_accumulation(rec: dict, funds_total: float | None) -> None:
    """Tripwire for the shekels-vs-agorot trap.

    The fund amounts summed must land near SP's accumulation. A scaling mistake
    would be off by 100x; genuine valuation-date drift is well under a percent.
    Log-only — never blocks an ingest, since SP is the authoritative figure.
    """
    accum = rec.get("accumulation")
    if not accum or not funds_total:
        return
    drift = abs(funds_total - accum) / accum
    if drift > _ACC_DRIFT_TOLERANCE:
        logger.warning(
            "hachshara_prod: id=%s accumulation %.2f but funds sum to %.2f "
            "(%.1f%% drift) — check field offsets/scaling",
            rec["id_number"], accum, funds_total, drift * 100,
        )
