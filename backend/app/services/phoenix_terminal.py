"""Phoenix terminal PRODUCTION parser — the option-14 ".MBT set".

The Phoenix legacy PowerTerm terminal (agent.fnx.co.il) menu **option 14**
("בנית קבצי פרודוקציה") builds the agent's production book as a set of CP1255/
visual-order Mimshak `.MBT` files in the Windows Downloads folder
(`LIFE.MBT`, `COVRLIFE.MBT`, `LIFEHLTH.MBT`, `COMPANY.MBT`, sometimes
`PERSON.MBT`). This is Phoenix's real PRODUCTION (full policy book) — the
agentportal SPA only exposes נפרעים, and the SFE vault is sparse (1 holding).

The `.MBT` files are already decoded by `services/mimshak/mbt.py` (built for the
Migdal Mimshak path). Here we ASSEMBLE them into production-schema records
(`company_source="הפניקס"`) so they aggregate into the unified production file.

LIFE.MBT column map (133 pipe-delimited cells, pinned from real exports):
    [9]  policy number (full, leading-zero padded)   [10] id_number (9-digit + pad)
    [14] customer name "first last" (Hebrew)          [15] start date DDMMYYYY
    [16] end date                                     [19] annual premium
    [74] policy value / accumulation (צבירה)          [111] total value
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.services.mimshak import mbt

logger = logging.getLogger(__name__)

PRODUCTION_COLUMNS = [
    "יצרן", "סוג מוצר", "מוצר", "מס' חשבון/פוליסה", "מספר ת.ז",
    "שם פרטי לקוח", "שם משפחה לקוח", 'סה"כ פרמיה', "צבירה",
    "סטטוס מוצר", "תאריך הצטרפות למוצר", "מספר סוכן",
]

# LIFE.MBT cell indices (pinned against live exports — refine here if Phoenix
# shifts columns).
_C_POLICY = 9
_C_ID = 10
_C_NAME = 14
_C_START = 15
_C_PREMIUM = 19
_C_ACCUM = 74


def _split_name(full: str) -> tuple[str, str]:
    full = (full or "").strip()
    if not full:
        return "", ""
    parts = full.split(None, 1)
    return (parts[0], parts[1]) if len(parts) == 2 else (parts[0], "")


def _ddmmyyyy(raw: str) -> str | None:
    """'01092010' → '2010-09-01' (DDMMYYYY). Returns None if not 8 digits."""
    raw = (raw or "").strip()
    if len(raw) != 8 or not raw.isdigit():
        return None
    dd, mm, yyyy = raw[0:2], raw[2:4], raw[4:8]
    return f"{yyyy}-{mm}-{dd}"


def _num(raw: str):
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        v = float(raw)
        return v if v != 0 else None
    except ValueError:
        return None


def is_phoenix_mbt_set(folder: Path) -> bool:
    """A Phoenix production .MBT set is a folder containing LIFE.MBT."""
    folder = Path(folder)
    return folder.is_dir() and (folder / "LIFE.MBT").exists()


def parse_phoenix_mbt_set(folder: Path) -> dict:
    """Assemble the .MBT set into production-schema records.

    Returns {"format": "production", "company_source": "הפניקס", "records": [...]}.
    Drives off LIFE.MBT + LIFEHLTH.MBT (one row per policy); PERSON.MBT (when
    present) supplies cleaner names by id.
    """
    folder = Path(folder)
    persons = {}
    try:
        if (folder / "PERSON.MBT").exists():
            persons = mbt.parse_persons(folder / "PERSON.MBT")
    except Exception as e:
        logger.warning("phoenix_terminal: PERSON.MBT parse failed: %s", e)

    records: list[dict] = []
    for fname, product in (("LIFE.MBT", "חיים"), ("LIFEHLTH.MBT", "חיים ובריאות")):
        p = folder / fname
        if not p.exists():
            continue
        try:
            policies = mbt.parse_life(p)
        except Exception as e:
            logger.warning("phoenix_terminal: %s parse failed: %s", fname, e)
            continue
        for policy_id, rec in policies.items():
            cells = rec.get("cells") or []

            def cell(i: int) -> str:
                return cells[i] if i < len(cells) else ""

            id_raw = cell(_C_ID).strip()
            id_number = (id_raw.lstrip("0") or id_raw) if id_raw else ""
            if not id_number or not id_number.isdigit():
                continue
            # Prefer PERSON name when available, else LIFE's embedded name.
            person = persons.get(id_number)
            if person and (person.get("first_name_he") or person.get("last_name_he")):
                first = person.get("first_name_he") or ""
                last = person.get("last_name_he") or ""
            else:
                first, last = _split_name(mbt._maybe_reverse_hebrew(cell(_C_NAME)))
            records.append({
                "יצרן": "הפניקס",
                "סוג מוצר": product,
                "מוצר": "ביטוח חיים",
                "מס' חשבון/פוליסה": cell(_C_POLICY).lstrip("0") or cell(_C_POLICY),
                "מספר ת.ז": id_number,
                "שם פרטי לקוח": first,
                "שם משפחה לקוח": last,
                'סה"כ פרמיה': _num(cell(_C_PREMIUM)),
                "צבירה": _num(cell(_C_ACCUM)),
                "סטטוס מוצר": "פעיל",
                "תאריך הצטרפות למוצר": _ddmmyyyy(cell(_C_START)),
                "מספר סוכן": None,
            })

    logger.info("phoenix_terminal: assembled %d production records from %s",
                len(records), folder)
    return {"format": "production", "company_source": "הפניקס", "records": records}


def build_phoenix_production_xlsx(folder: Path, out_path: Path) -> Path:
    """Write the assembled production records to a production-schema xlsx so the
    standard ingest/`detect_format` routes it as production (יצרן/סטטוס מוצר/
    סה"כ פרמיה signature). Named with 'פרודוקציה' so the commission filename
    veto never fires."""
    import pandas as pd

    parsed = parse_phoenix_mbt_set(folder)
    records = parsed["records"]
    if not records:
        raise RuntimeError(f"phoenix_terminal: no production records in {folder}")
    df = pd.DataFrame(records, columns=PRODUCTION_COLUMNS)
    out_path = Path(out_path)
    df.to_excel(out_path, index=False)
    logger.info("phoenix_terminal: wrote %d rows → %s", len(df), out_path.name)
    return out_path
