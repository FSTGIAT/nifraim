"""Parse Harel safe-vault (harelsafe.co.il) CP862 fixed-width PRODUCTION reports.

The agents portal only exposes savings production (גמל/מגוון) + חיים/בריאות
נפרעים. The חיים/בריאות **production** summaries — the five
``ר.ת.-מורחב`` reports — live ONLY in the harelsafe vault, delivered as CP862
fixed-width text files (the same SP/SB/RM/RP/RB family as הכשרה production, so
we reuse ``services.hachshara_prod``'s proven line parsers for the name / date /
product / fund fields). ``pd.read_excel`` cannot read them, so the regular
``_extract_production_rows`` reshape fails — this module replaces it for the
vault leg.

**The identity fields are NOT at הכשרה's offsets** (QA 2026-09-06, decoded from
kiko's real July-2026 vault files). ``[6:15]`` — which `hachshara_prod._SP_ID`
reads as the national ID — is הראל's **policy number**; the ת"ז sits later in the
record. Reusing הכשרה's slice put a policy into every row's ``מספר ת.ז`` and left
``מס' חשבון/פוליסה`` empty, which is what QA saw ("גלעד בארי" filed under
``103340379``, his policy, instead of ``031400617``, his ת"ז).

Measured layout — the check-digit pass rate is what separates the two fields:

    file                      lines  policy      ת"ז         ת"ז valid / total
    SP…  חיים פוליסות            65   [6:15]      [25:34]     64/65   ([6:15]:  2/65)
    RP…  בריאות פוליסות         229   [6:15]      [25:34]    228/229  ([6:15]: 19/229)
    SB…  חיים ביטוחים           107   [6:15]      —          join to SP by policy (107/107)
    RB…  בריאות ביטוחים        1354   [6:15]      [70:79]   1353/1354 ([6:15]: 146/1354)
    RM…  פוליסות מגוון           28   [0:9]       —          join to SP by policy (26/28)

SB and RM carry no ת"ז at all, so their identity is joined from the SP master by
POLICY (`fill_identity_from_masters`). RB carries its own ת"ז and takes only its
name from RP. The maps are per-family on purpose: SP and RP share exactly one
policy number, so a merged policy→ת"ז map would misattribute that row.

Rows come out in the exact schema ``harel_savings._write_production_xlsx``
expects, so they join the unified production view.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from app.services.hachshara_prod import (
    _id_at,
    _parse_sp_line,
    _parse_sb_line,
    _parse_rm_line,
    _valid_tz,
)

logger = logging.getLogger(__name__)

# InfoBay filename prefix → (clean report label, family). The label becomes both
# "סוג מוצר" and — for the master files — the fallback "מוצר".
_PREFIX_LABEL = {
    "SP": ("ר.ת.-מורחב חיים פוליסות", "master"),
    "RP": ("ר.ת.-מורחב בריאות פוליסות", "master"),
    "SB": ("ר.ת.-מורחב חיים ביטוחים", "insurance"),
    "RB": ("ר.ת.-מורחב בריאות ביטוחים", "insurance"),
    "RM": ("ר.ת. פוליסות מגוון", "funds"),
}
# label → prefix, so the identity join can tell SP from RP and SB from RB after
# parse_vault_file() has collapsed each file to (company_source, label, rows).
_LABEL_PREFIX = {label: prefix for prefix, (label, _fam) in _PREFIX_LABEL.items()}

# ── Identity field offsets (הראל, NOT הכשרה — see the module docstring) ──
_H_POLICY = slice(6, 15)     # SP / RP / SB / RB — zero-padded 9-digit policy
_H_RM_POLICY = slice(0, 9)   # RM puts the policy first
_H_TZ_MASTER = slice(25, 34)  # SP / RP — the national ID
_H_TZ_RB = slice(70, 79)     # RB — the national ID of the insured on the row

# A real vault file has a handful of non-TZ identifiers (measured: exactly one
# per file). A wholesale failure means the offset moved — log, never drop rows.
_TZ_TRIPWIRE = 0.80

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


def _policy_at(line: str, where: slice) -> Optional[str]:
    """Read the policy field. Tolerant where `_id_at` is strict, on purpose.

    `hachshara_prod._id_at` demands exactly 9 digits, which is right for a ת"ז
    (a short read means the offset moved). The policy field is only 9 chars WIDE,
    so it cannot overflow — but a space-padded rather than zero-padded value
    would fail `_id_at`'s length test and, since `parse_vault_file` skips rows
    with no policy, drop a real row silently. Accept any digit run instead.

    Leading zeros are stripped, matching `_id_at` and the repo-wide `lstrip("0")`
    idiom. NOTE: `aggregate._policy_str` deliberately does NOT strip them, and
    `comparison_service._policy_matches` does not either — so if the הראל נפרעים
    export ever prints its `מספר פוליסה` zero-padded, the two sides will not
    pair. Unverified against a live נפרעים file; every policy in the 07-2026
    vault files is zero-padded to 9 (`007455322` → `7455322`).
    """
    raw = line[where].strip()
    if not raw.isdigit() or not raw.strip("0"):
        return None
    return raw.lstrip("0")


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


def _is_real_spreadsheet(raw_path: Path) -> bool:
    """True if the bytes are a genuine xlsx/xls, whatever the name says.

    `_classify` matches on the FILENAME, because the vault serves CP862 content
    under an `.xlsx` name. The converse also happens: a real spreadsheet whose
    name carries a vault label — "הראל מגוון - פרודוקציה (מאי 2026).xlsx" is a
    real xlsx from the agents-portal savings leg and matches the RM keyword. Sent
    to `parse_vault_file`, CP862-decoding a zip yields 0 rows, and `harel_savings`
    reports "כספת מגוון: 0 שורות" while silently dropping a file that would have
    parsed perfectly through the normal reshape. So sniff the magic bytes: an
    xlsx is a ZIP (PK), a legacy xls an OLE2 compound file. CP862 fixed-width is
    neither.
    """
    try:
        head = raw_path.read_bytes()[:8]
    except OSError:
        return False
    return head[:4] == b"PK\x03\x04" or head == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def is_vault_file(raw_path: Path) -> bool:
    """True if this looks like a Harel vault CP862 report (not an xlsx export)."""
    return _classify(raw_path) is not None and not _is_real_spreadsheet(raw_path)


def _tz_tripwire(label: str, ids: list[str]) -> None:
    """Log when the ת"ז field stops looking like ת"ז — i.e. the offset moved.

    This is the check that would have caught the הכשרה-offset bug on day one:
    reading the policy field instead scores 2/65 here, the real field 64/65.
    Log-only — הראל does book a few non-TZ identifiers, so gating rows on the
    check digit would silently drop real customers (cf. `hachshara_prod._id_at`).
    """
    if not ids:
        return
    ok = sum(1 for i in ids if _valid_tz(i))
    rate = ok / len(ids)
    if rate < _TZ_TRIPWIRE:
        logger.warning(
            "harel_vault: %s — only %d/%d ids (%.0f%%) pass the ת\"ז check digit. "
            "The identity offset has probably moved; expected ~99%%.",
            label, ok, len(ids), rate * 100,
        )


def parse_vault_file(raw_path: Path) -> Optional[tuple[str, str, list[dict]]]:
    """Parse one vault report → (company_source, label, production-row dicts).

    Returns None if the filename prefix is unrecognized (caller should fall back
    to the regular xlsx reshape). Rows without a policy number are skipped.

    SB/RM rows come out with ``מספר ת.ז`` empty — those files carry no ת"ז at
    all. `fill_identity_from_masters` fills them from SP by policy, so it MUST
    run before the rows are written.
    """
    meta = _classify(raw_path)
    if meta is None or _is_real_spreadsheet(raw_path):
        return None
    label, family = meta
    prefix = _LABEL_PREFIX[label]
    company_source = f"הראל {label}"
    rows: list[dict] = []
    seen_ids: list[str] = []

    # NOTE — accumulation (צבירה) is deliberately NOT carried from these vault
    # reports. The agents-portal savings leg already downloads הראל
    # גמל/מגוון/פנסיה/השתלמות WITH accumulation and is the single authoritative
    # source. The vault's savings overlaps it: "הראל מגוון" is a life-savings
    # policy, so the SAME money appears in the agents-portal מגוון, in the SP
    # (חיים פוליסות) master, AND in the RM (מגוון) report — e.g. POLICY
    # 102902132 shows ~500,256 in SP and ~500,221 in RM. Summing any of them on
    # top of the agents leg double/triple-counts. The vault's job here is
    # PRODUCT PRESENCE (which customers hold which חיים/בריאות products — kiko
    # had zero ר.ת.-מורחב records), so we emit id + policy + product + name only.
    for ln in _lines(raw_path):
        if family == "master":
            # SP/RP: name + sign_date come from הכשרה's verified slices; the
            # identity fields do NOT (see the module docstring).
            r = _parse_sp_line(ln)
            policy = _valid_id(_policy_at(ln, _H_POLICY))
            if not r or not policy:
                continue
            idn = _valid_id(_id_at(ln, _H_TZ_MASTER))
            if idn:
                seen_ids.append(idn)
            rows.append(_row(
                company_source, label, idn, policy,
                product=label,
                first=(r.get("first_name") or "").strip(),
                last=(r.get("last_name") or "").strip(),
                sign_date=r.get("sign_date"),
            ))
        elif family == "insurance":
            # SB has no ת"ז (joined from SP by policy); RB carries its own.
            r = _parse_sb_line(ln)
            policy = _valid_id(_policy_at(ln, _H_POLICY))
            if not r or not policy:
                continue
            # ONLY RB carries a ת"ז. Reading [70:79] on SB returns whatever
            # digits happen to sit there (measured: 16/106 even pass the check
            # digit, so a shape test alone would not catch it) — SB's identity
            # must come from the SP master by policy.
            idn = _valid_id(_id_at(ln, _H_TZ_RB)) if prefix == "RB" else None
            if idn:
                seen_ids.append(idn)
            rows.append(_row(
                company_source, label, idn, policy,
                product=(r.get("product") or "").strip() or label,
            ))
        elif family == "funds":
            r = _parse_rm_line(ln)
            policy = _valid_id(_policy_at(ln, _H_RM_POLICY))
            if not r or not policy:
                continue
            rows.append(_row(
                company_source, label, None, policy,
                product=(r.get("dominant_fund") or "").strip() or label,
            ))

    _tz_tripwire(label, seen_ids)
    return company_source, label, rows


def _row(company_source, label, idn, policy, *, product, first="", last="",
         accumulation=None, sign_date=None) -> dict:
    return {
        "יצרן": company_source,
        "סוג מוצר": label,
        "מוצר": product,
        "מס' חשבון/פוליסה": policy,
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


def fill_identity_from_masters(parsed: list[tuple[str, str, list[dict]]]) -> None:
    """Stamp the ת"ז and the name onto the rows that lack them. In place.

    Only SP and RP carry names, and only SP/RP/RB carry a ת"ז, so:

      * SB (חיים ביטוחים) and RM (מגוון) have neither → both are joined from the
        **SP** master by POLICY.
      * RB (בריאות ביטוחים) already has its own ת"ז → it takes only the name,
        from **RP**, by ת"ז.

    The maps stay per-family deliberately: SP and RP share exactly one policy
    number in the live files, so a merged policy→identity map would attribute
    that row to the wrong customer.
    """
    sp_by_policy: dict[str, tuple[Optional[str], str, str]] = {}
    rp_by_tz: dict[str, tuple[str, str]] = {}

    for _cs, label, rows in parsed:
        prefix = _LABEL_PREFIX.get(label)
        if prefix == "SP":
            for row in rows:
                pol = row["מס' חשבון/פוליסה"]
                if pol and pol not in sp_by_policy:
                    sp_by_policy[pol] = (
                        row["מספר ת.ז"], row["שם פרטי לקוח"], row["שם משפחה לקוח"],
                    )
        elif prefix == "RP":
            for row in rows:
                tz = row["מספר ת.ז"]
                if tz and (row["שם פרטי לקוח"] or row["שם משפחה לקוח"]) \
                        and tz not in rp_by_tz:
                    rp_by_tz[tz] = (row["שם פרטי לקוח"], row["שם משפחה לקוח"])

    unmatched = 0
    for _cs, label, rows in parsed:
        prefix = _LABEL_PREFIX.get(label)
        if prefix in ("SB", "RM"):
            for row in rows:
                hit = sp_by_policy.get(row["מס' חשבון/פוליסה"])
                if not hit:
                    unmatched += 1
                    continue
                tz, first, last = hit
                if not row["מספר ת.ז"]:
                    row["מספר ת.ז"] = tz
                if not row["שם פרטי לקוח"] and not row["שם משפחה לקוח"]:
                    row["שם פרטי לקוח"], row["שם משפחה לקוח"] = first, last
        elif prefix == "RB":
            for row in rows:
                if row["שם פרטי לקוח"] or row["שם משפחה לקוח"]:
                    continue
                nm = rp_by_tz.get(row["מספר ת.ז"])
                if nm:
                    row["שם פרטי לקוח"], row["שם משפחה לקוח"] = nm

    if unmatched:
        # Expected in small numbers — a מגוון policy the SP master does not list.
        # Those rows keep their policy and carry no money, and compute_comparison
        # skips id-less records, so they are harmless.
        logger.info(
            "harel_vault: %d SB/RM rows had no matching SP policy (no ת\"ז)",
            unmatched,
        )


# Kept as the historical name so `harel_savings`'s vault fold keeps working; the
# behaviour is now the full identity join, not names alone.
fill_names_from_masters = fill_identity_from_masters
