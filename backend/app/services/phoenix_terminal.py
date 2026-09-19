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

**The two files do NOT share a layout** — measured on a real export
(`LIFE.MBT` 133 cells/row, `LIFEHLTH.MBT` 58). One shared index map was being
applied to both, and on the 58-cell file it read:

    [19] → 14612.00 on EVERY row (uniq=1 of 109)   ← not a premium at all
    [74] → out of range → accumulation silently None

`api/production.py` already documents the downstream symptom from its own side
("~76 clients each carrying exactly ₪14,612 of monthly health premium"), and
`ClientRows.vue` renders a warning for it. Same number, same cause.

LIFE.MBT (133 cells):
    [9]  policy number (full, leading-zero padded)   [10] id_number (9-digit + pad)
    [14] customer name "first last" (Hebrew)          [15] start date DDMMYYYY
    [16] end date                                     [74] policy value (צבירה)
    [111] total value
    premium: NOT resolved. [19]/[20] are the same 14612/14556 constants on 4 of
    6 rows, and 6 rows cannot settle an index. Left None rather than guessed —
    the precedent `phoenix_mu.py` and `harel_vault_prod.py` both set.

LIFEHLTH.MBT (58 cells):
    [43] payments per year (12 on all rows)
    [48] annual premium        [49] premium per payment  → this is `סה"כ פרמיה`
    no accumulation column.
    [48] / ([49]x12) is a near-constant 0.9964 across 107 rows — an annual-
    payment discount, i.e. two views of one premium. [49] is the per-payment
    (monthly) figure, which is the unit `סה"כ פרמיה` is consumed as
    (`rate_select` applies `premium x rate` with no /12). Worth re-checking
    against Phoenix נפרעים the first time a terminal run lands in the book.
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

# Per-FILE cell indices. `premium`/`accum` are None where the file has no such
# column — emitting None is correct; emitting the wrong cell is not.
_LAYOUTS = {
    "LIFE.MBT": {
        "cells": 133, "policy": 9, "id": 10, "name": 14, "start": 15,
        "premium": None, "accum": 74,
    },
    "LIFEHLTH.MBT": {
        "cells": 58, "policy": 9, "id": 10, "name": 14, "start": 15,
        "premium": 49, "accum": None,
    },
}


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


def _verified_premium_index(policies: dict, layout: dict, fname: str) -> int | None:
    """The layout's premium index, or None when the column is a constant.

    Guards the failure mode this module was fixed for: a single index map
    applied to two different layouts read a fixed 14612.00 out of every
    LIFEHLTH row. One number repeated across a whole book is never a set of
    per-policy premiums, so refuse it rather than publish it.
    """
    idx = layout.get("premium")
    if idx is None:
        return None
    seen: set[str] = set()
    for rec in policies.values():
        cells = rec.get("cells") or []
        if idx < len(cells):
            seen.add((cells[idx] or "").strip())
        if len(seen) > 1:
            return idx
    if len(policies) > 3 and len(seen) <= 1:
        logger.warning(
            "phoenix_terminal: %s cell[%d] is constant %r across %d rows — "
            "not a premium; emitting None. Phoenix may have shifted columns.",
            fname, idx, next(iter(seen), ""), len(policies),
        )
        return None
    return idx


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

        layout = _LAYOUTS[fname]
        # A money column that holds the SAME value on every row of the file is
        # a header/constant, not a per-policy amount. Refuse it instead of
        # shipping one number to hundreds of clients — that is exactly the
        # failure this layout split fixes, so it must not silently return if
        # Phoenix shifts its columns again.
        premium_idx = _verified_premium_index(policies, layout, fname)

        for policy_id, rec in policies.items():
            cells = rec.get("cells") or []

            def cell(i: int | None) -> str:
                if i is None:
                    return ""
                return cells[i] if i < len(cells) else ""

            id_raw = cell(layout["id"]).strip()
            id_number = (id_raw.lstrip("0") or id_raw) if id_raw else ""
            if not id_number or not id_number.isdigit():
                continue
            # Prefer PERSON name when available, else the file's embedded name.
            person = persons.get(id_number)
            if person and (person.get("first_name_he") or person.get("last_name_he")):
                first = person.get("first_name_he") or ""
                last = person.get("last_name_he") or ""
            else:
                first, last = _split_name(mbt._maybe_reverse_hebrew(cell(layout["name"])))
            records.append({
                "יצרן": "הפניקס",
                "סוג מוצר": product,
                "מוצר": "ביטוח חיים",
                "מס' חשבון/פוליסה": cell(layout["policy"]).lstrip("0") or cell(layout["policy"]),
                "מספר ת.ז": id_number,
                "שם פרטי לקוח": first,
                "שם משפחה לקוח": last,
                'סה"כ פרמיה': _num(cell(premium_idx)),
                "צבירה": _num(cell(layout["accum"])),
                "סטטוס מוצר": "פעיל",
                "תאריך הצטרפות למוצר": _ddmmyyyy(cell(layout["start"])),
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
