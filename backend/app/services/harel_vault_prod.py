"""Parse Harel safe-vault (harelsafe.co.il) CP862 fixed-width PRODUCTION reports.

The agents portal only exposes savings production (גמל/מגוון) + חיים/בריאות
נפרעים. The חיים/בריאות **production** summaries — the five
``ר.ת.-מורחב`` reports — live ONLY in the harelsafe vault, delivered as CP862
fixed-width text files (the same SP/SB/RM/RP/RB family as הכשרה production, so
we reuse ``services.hachshara_prod``'s proven line parsers for id / name /
product / fund / accumulation). ``pd.read_excel`` cannot read them, so the
regular ``_extract_production_rows`` reshape fails — this module replaces it for
the vault leg.

Vault file → report (mapped by the InfoBay filename prefix, verified live on
kiko's SXV49345 vault 2026-07-30):

    SP…  ר.ת.-מורחב חיים פוליסות   (customer master: id, name, accumulation, sign_date)
    RP…  ר.ת.-מורחב בריאות פוליסות (customer master: id, name)
    SB…  ר.ת.-מורחב חיים ביטוחים   (id + specific insurance product)
    RB…  ר.ת.-מורחב בריאות ביטוחים (id + specific insurance product)
    RM…  ר.ת. פוליסות מגוון         (id + fund + accumulation)

Rows come out in the exact schema ``harel_savings._write_production_xlsx``
expects, so they join the unified production view.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from app.services.hachshara_prod import (
    _parse_sp_line,
    _parse_sb_line,
    _parse_rm_line,
)

# InfoBay filename prefix → (clean report label, family). The label becomes both
# "סוג מוצר" and — for the master files — the fallback "מוצר".
_PREFIX_LABEL = {
    "SP": ("ר.ת.-מורחב חיים פוליסות", "master"),
    "RP": ("ר.ת.-מורחב בריאות פוליסות", "master"),
    "SB": ("ר.ת.-מורחב חיים ביטוחים", "insurance"),
    "RB": ("ר.ת.-מורחב בריאות ביטוחים", "insurance"),
    "RM": ("ר.ת. פוליסות מגוון", "funds"),
}

_PRODUCTION_COLUMNS = [
    "יצרן", "סוג מוצר", "מוצר", "מס' חשבון/פוליסה", "מספר ת.ז",
    "שם פרטי לקוח", "שם משפחה לקוח", 'סה"כ פרמיה', "צבירה",
    "סטטוס מוצר", "תאריך הצטרפות למוצר", "מספר סוכן", "מספר חשבון",
]


# Fallback classification by the Hebrew label harel.py stamps into the filename
# when the vault serves a name-less / colliding download ("הראל - <label>.xlsx"
# or "הראל - <label> - SP…"). Order matters: the "ביטוחים" / "פוליסות" tests must
# see the חיים/בריאות qualifier, and מגוון has no such qualifier.
_LABEL_KEYWORDS = [
    (("חיים", "פוליסות"), _PREFIX_LABEL["SP"]),
    (("בריאות", "פוליסות"), _PREFIX_LABEL["RP"]),
    (("חיים", "ביטוחים"), _PREFIX_LABEL["SB"]),
    (("בריאות", "ביטוחים"), _PREFIX_LABEL["RB"]),
    (("מגוון",), _PREFIX_LABEL["RM"]),
]


def _classify(raw_path: Path) -> Optional[tuple[str, str]]:
    """Return (label, family) for a vault file, or None if the name is unknown.

    Handles all three shapes harel.py can produce: the native InfoBay name
    ("SP4934506"), a collision-renamed one ("הראל - <label> - SP4934506"), and
    the name-less fallback ("הראל - <label>.xlsx"). The content is always CP862
    regardless of the .xlsx extension."""
    name = raw_path.name
    # 1) an SP/RP/SB/RB/RM code followed by a digit, anywhere in the name.
    m = re.search(r"(SP|RP|SB|RB|RM)\d", name.upper())
    if m:
        return _PREFIX_LABEL[m.group(1)]
    # 2) otherwise match the Hebrew report label baked into the filename.
    for keywords, meta in _LABEL_KEYWORDS:
        if all(kw in name for kw in keywords):
            return meta
    return None


def _valid_id(idv) -> Optional[str]:
    if not idv:
        return None
    s = str(idv).strip()
    if s.isdigit() and 4 <= len(s) <= 9:
        return s
    return None


def _lines(raw_path: Path) -> list[str]:
    raw = raw_path.read_bytes().decode("cp862", errors="replace")
    raw = raw.replace("\r\n", "\n").replace("\x85", "\n")
    return [ln for ln in raw.split("\n") if ln.strip()]


def is_vault_file(raw_path: Path) -> bool:
    """True if this looks like a Harel vault CP862 report (not an xlsx export)."""
    return _classify(raw_path) is not None


def parse_vault_file(raw_path: Path) -> Optional[tuple[str, str, list[dict]]]:
    """Parse one vault report → (company_source, label, production-row dicts).

    Returns None if the filename prefix is unrecognized (caller should fall back
    to the regular xlsx reshape). Rows without a valid id are skipped.
    """
    meta = _classify(raw_path)
    if meta is None:
        return None
    label, family = meta
    company_source = f"הראל {label}"
    rows: list[dict] = []

    # NOTE — accumulation (צבירה) is deliberately NOT carried from these vault
    # reports. The agents-portal savings leg already downloads הראל
    # גמל/מגוון/פנסיה/השתלמות WITH accumulation and is the single authoritative
    # source. The vault's savings overlaps it: "הראל מגוון" is a life-savings
    # policy, so the SAME money appears in the agents-portal מגוון, in the SP
    # (חיים פוליסות) master, AND in the RM (מגוון) report — e.g. customer
    # 102902132 shows ~500,256 in SP and ~500,221 in RM. Summing any of them on
    # top of the agents leg double/triple-counts. The vault's job here is
    # PRODUCT PRESENCE (which customers hold which חיים/בריאות products — kiko
    # had zero ר.ת.-מורחב records), so we emit id + product + name only.
    for ln in _lines(raw_path):
        if family == "master":
            r = _parse_sp_line(ln)
            idn = _valid_id(r.get("id_number")) if r else None
            if not idn:
                continue
            rows.append(_row(
                company_source, label, idn,
                product=label,
                first=(r.get("first_name") or "").strip(),
                last=(r.get("last_name") or "").strip(),
                sign_date=r.get("sign_date"),
            ))
        elif family == "insurance":
            r = _parse_sb_line(ln)
            idn = _valid_id(r.get("id_number")) if r else None
            if not idn:
                continue
            rows.append(_row(
                company_source, label, idn,
                product=(r.get("product") or "").strip() or label,
            ))
        elif family == "funds":
            r = _parse_rm_line(ln)
            idn = _valid_id(r.get("id_number")) if r else None
            if not idn:
                continue
            rows.append(_row(
                company_source, label, idn,
                product=(r.get("dominant_fund") or "").strip() or label,
            ))
    return company_source, label, rows


def _row(company_source, label, idn, *, product, first="", last="",
         accumulation=None, sign_date=None) -> dict:
    return {
        "יצרן": company_source,
        "סוג מוצר": label,
        "מוצר": product,
        "מס' חשבון/פוליסה": None,
        "מספר ת.ז": idn,
        "שם פרטי לקוח": first,
        "שם משפחה לקוח": last,
        'סה"כ פרמיה': None,
        "צבירה": accumulation,
        "סטטוס מוצר": "פעיל",
        "תאריך הצטרפות למוצר": sign_date,
        "מספר סוכן": None,
        "מספר חשבון": None,
    }


def fill_names_from_masters(parsed: list[tuple[str, str, list[dict]]]) -> None:
    """Stamp names onto insurance/funds rows using the id→name map from the
    master (SP/RP) files, which are the only vault reports carrying names.
    Mutates the row dicts in place."""
    id_name: dict[str, tuple[str, str]] = {}
    for _cs, _label, rows in parsed:
        for row in rows:
            first, last = row["שם פרטי לקוח"], row["שם משפחה לקוח"]
            if (first or last) and row["מספר ת.ז"] not in id_name:
                id_name[row["מספר ת.ז"]] = (first, last)
    for _cs, _label, rows in parsed:
        for row in rows:
            if not row["שם פרטי לקוח"] and not row["שם משפחה לקוח"]:
                nm = id_name.get(row["מספר ת.ז"])
                if nm:
                    row["שם פרטי לקוח"], row["שם משפחה לקוח"] = nm
