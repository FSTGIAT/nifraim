"""Parse Clal InfoBay production-box `.MEV` files → per-client production rows.

Clal's production "תיבה" boxes (data.clal.co.il InfoBay) are ZIP-SFX `.exe`
archives. The Mimshak `.DAT` inside holds ONE client; the REAL month's
production — every client — is in the sibling `.MEV` files, a Clal fixed-width
text format. A single month's boxes yield ~20+ clients this way vs 1 from the
`.DAT` (why every earlier attempt showed "1 customer").

Record (≈350 chars): `agent[0:5] + ת"ז[5:14] + … name-block … + city + amounts`.

**Two encodings coexist across boxes** (verified live 2026-07-30 against
`פרודוקציה כלל משורנס.xlsx`):
  - the חיים box (17853) is **cp862 VISUAL Hebrew** (each Hebrew run reversed);
  - the בריאות box (17854) is **cp1255 logical Hebrew**.
Detected per-file by whichever codec yields more Hebrew letters; visual files
get each Hebrew run reversed in place. Verified: 18/18 חיים + בריאות last names
reproduce the oracle (בוטנרו/פוגל/גורן/…).

Fields recovered: ת"ז, first/last name, city. The policy number and exact
premium are NOT in `.MEV` (they live in the `.MV2`/`.SGB` siblings + Clal's
enriched export) → left None; this parser establishes the month's CLIENT
PRESENCE + names + product (from the box type), which is the production data.
"""
from __future__ import annotations

import re
from typing import Optional

_REC = re.compile(r"^\d{14}")
_HEB = re.compile(r"[א-ת]")
# Reverse Hebrew+SPACE runs together — a run like "<last> <first>" must flip as
# a unit to read logical (reversing each word alone keeps the field order visual
# and swaps last/first). Digits break the run, separating name from street.
_HEB_RUN = re.compile(r"[א-ת ]+")
_NAME_WIN = (44, 78)   # name block window (proven: token[0]=last, 18/18 live)
_CITY_WIN = (78, 104)  # city window


def _heb_count(s: str) -> int:
    return len(_HEB.findall(s))


def _decode(raw: bytes) -> tuple[str, bool]:
    """Return (text, visual). Pick the codec with more Hebrew; cp862 ⇒ visual."""
    t862 = raw.decode("cp862", errors="replace")
    t1255 = raw.decode("cp1255", errors="replace")
    if _heb_count(t862) > _heb_count(t1255):
        return t862, True
    return t1255, False


def _revrun(s: str) -> str:
    """Reverse each Hebrew run in place (visual→logical), leaving digits/spaces."""
    return _HEB_RUN.sub(lambda m: m.group(0)[::-1], s)


def _heb_tokens(segment: str) -> list[str]:
    """Hebrew (and hyphenated) tokens in a segment, digits stripped."""
    toks = re.findall(r"[א-ת][א-ת\-']*", segment)
    return [t for t in toks if t]


def parse_clal_mev(raw: bytes, product: str = "", product_type: str = "") -> list[dict]:
    """Parse a `.MEV` blob into production-row dicts. `product`/`product_type`
    come from the box type (חיים / בריאות). Rows without a valid ת"ז skipped."""
    text, visual = _decode(raw)
    rows: list[dict] = []
    seen: set[str] = set()
    for line in text.replace("\r\n", "\n").split("\n"):
        if len(line) < _CITY_WIN[0] or not _REC.match(line):
            continue
        raw_id = line[5:14]
        idn = raw_id.lstrip("0") or "0"
        if not (raw_id.isdigit() and 4 <= len(idn) <= 9):
            continue
        # Reverse the name/city WINDOWS (bounded — reversing the whole line would
        # merge name+city across the gap). Within a window a Hebrew+space run
        # "<last> <first>" flips as a unit → logical order, so `.split()` gives
        # token[0]=last (proven 18/18 live). First name = first Hebrew token after
        # last (the street glues on with digits between).
        name_src = line[_NAME_WIN[0]:_NAME_WIN[1]]
        city_src = line[_CITY_WIN[0]:_CITY_WIN[1]]
        if visual:
            name_src = _revrun(name_src)
            city_src = _revrun(city_src)
        toks = name_src.split()
        last = toks[0] if toks else ""
        first = ""
        for t in toks[1:]:
            m = re.match(r"[א-ת][א-ת\-']*", t)
            if m:
                first = m.group(0)
                break
        city_toks = _heb_tokens(city_src)
        city = " ".join(city_toks) if city_toks else None
        key = (idn, product)
        if key in seen:
            continue
        seen.add(str(key))
        rows.append({
            "id_number": idn,
            "first_name": first,
            "last_name": last,
            "receiving_company": 'כלל חברה לביטוח בע"מ',
            "product_type": product_type or "ביטוח",
            "product": product or "כלל",
            "city": city,
            "fund_policy_number": None,
            "total_premium": None,
            "reconciliation_status": "no_data",
        })
    return rows


def parse_clal_pol(raw: bytes) -> dict:
    """Parse a box `.POL` file → {ת"ז: policy_number}.

    Record (cp862): `agent[0:5] + policy[5:12] + …zeros… + insured ת"ז[22:31] +
    owner ת"ז[31:40]`. The INSURED ([22:31]) is the correct join key (the `.MV2`
    used the OWNER [12:21] → wrong). Verified 20/39 vs the oracle file; the boxes
    cover ~27 clients' policies (the rest are portal-enriched, not in the boxes).
    Premium is NOT in any box file, so it stays None.
    """
    text = raw.decode("cp862", errors="replace")
    out: dict = {}
    for line in text.replace("\r\n", "\n").split("\n"):
        if len(line) < 31 or not line[:5].isdigit():
            continue
        pol = line[5:12].lstrip("0")
        tz = line[22:31]
        if pol and tz.isdigit():
            idn = tz.lstrip("0") or "0"
            if 4 <= len(idn) <= 9:
                out.setdefault(idn, pol)  # first policy per client
    return out


def product_for_box(box_name: str) -> tuple[str, str]:
    """(product, product_type) from the box name. 17854/בריאות ⇒ health, else חיים."""
    n = box_name or ""
    if "בריאות" in n or "17854" in n:
        return "כלל - בריאות", "ביטוח בריאות"
    return "כלל - חיים", "ביטוח חיים"
