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
    policy id  : reliable (9-wide zero-padded field at [2:11] — NOT [4:11])
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


def _is_cancelled_bundle(arj_name: str) -> bool:
    """True for the מבוטלות (cancelled-policies) inner bundle, which must be
    excluded from production. Matches the Hebrew word or the ASCII "-MM" code
    (active production is "-MP")."""
    if "מבוטל" in arj_name:
        return True
    return re.search(r"-MM\d", arj_name) is not None


def _snapshot_sort_key(arj_name: str) -> str:
    """Sort key for ordering snapshots newest-first. Menora names bundles
    `<report>-<code>-<DD_MM_YYYY>-<HH_MM_SS>.ARJ`; turn the date/time tail into
    a `YYYYMMDDHHMMSS` string that sorts chronologically. Undated names sort
    oldest (empty key) so any dated snapshot's data wins the policy-level dedup."""
    m = re.search(r"(\d{2})_(\d{2})_(\d{4})(?:-(\d{2})_(\d{2})_(\d{2}))?", arj_name)
    if not m:
        return ""
    d, mo, y = m.group(1), m.group(2), m.group(3)
    hms = "".join(g or "00" for g in (m.group(4), m.group(5), m.group(6)))
    return f"{y}{mo}{d}{hms}"


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
        # Skip the "מבוטלות" (cancelled-policies) bundle: Menora ships it in the
        # same production zip as the active "פרט" bundle, but its rows are dead
        # clients that no longer exist and must not enter production. The bundle
        # is tagged both by the Hebrew word and by the ASCII "-MM" marker
        # (active = "-MP"); match either so a garbled-encoding name still filters.
        # (QA 2026-07-23: "we shouldn't have downloaded the חיים מבוטל file".)
        kept = [n for n in arj_names if not _is_cancelled_bundle(n)]
        skipped = [n for n in arj_names if _is_cancelled_bundle(n)]
        if skipped:
            logger.info(
                "menora_legacy: skipping %d cancelled (מבוטלות) bundle(s): %s",
                len(skipped), [n[:40] for n in skipped],
            )
        # De-duplicate ACROSS snapshots at the policy level. Menora ships the
        # same report for several months in one zip (e.g. פרט dated 24_05 AND
        # 10_06 — 71 of 73 clients identical); parsing every snapshot naively
        # double-counts active clients into production (QA 2026-07-23:
        # "downloaded each customer in duplicate", flagged for Migdal, present
        # here too). We keep one row per (id_number, policy), preferring the
        # NEWEST snapshot's data — so a client that appears only in the older
        # snapshot is still kept (a policy-level union), rather than dropping
        # whole older bundles which would silently lose those clients.
        kept.sort(key=_snapshot_sort_key, reverse=True)  # newest bundle first
        arj_names = kept
        seen_policies: set[tuple] = set()
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
            except zipfile.BadZipFile:
                logger.warning("menora_legacy: %s is not a valid ZIP, skipping", arj_name)
                continue
            for rec in inner_records:
                key = (rec.get("id_number"), rec.get("fund_policy_number"))
                if key in seen_policies:
                    continue
                seen_policies.add(key)
                records.append(rec)

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

    # G.TXT is indexed under BOTH policy-key widths, because G's own layout is
    # unconfirmed (we have no spec, and the only samples we've measured are P.TXT).
    #
    #   wide   = the real policy from [2:11], zero-stripped (see _policy_from_p_line)
    #   narrow = the legacy [4:11] slice, kept verbatim
    #
    # The two namespaces cannot collide (different widths), so indexing both is
    # purely additive. Lookup below tries wide first and falls back to narrow, and
    # the narrow key is computed from the RAW P line — never from the emitted
    # field. Net effect: if G shares P's layout the join gets STRONGER (the old
    # 7-char key was not unique — with policies spread over 34/35/36/37 prefixes
    # two could share a suffix, and this dict is last-write-wins, so premiums
    # could silently attach to the wrong policy); if G's layout differs, the
    # narrow path reproduces the old join byte-for-byte. There is no input on
    # which premiums can be lost.
    g_by_policy: dict[str, dict] = {}
    if g_txt:
        for line in g_txt.split("\r\n"):
            if not line.strip():
                continue
            parsed = _parse_g_line(line)
            wide = _policy_from_p_line(line)
            if wide:
                g_by_policy[wide] = parsed
            narrow = line[4:11].strip()
            if narrow:
                g_by_policy[narrow] = parsed

    out: list[dict] = []
    rows = wide_hits = narrow_hits = misses = guard_rejects = 0
    for line in p_txt.split("\r\n"):
        if not line.strip() or len(line) < 60:
            continue
        rec = _parse_p_line(line)
        if not rec or not rec.get("id_number"):
            continue
        rows += 1
        if rec.get("fund_policy_number") is None:
            guard_rejects += 1
        # Enrich with financial fields when G.TXT has a matching policy.
        g: dict = {}
        for key, which in ((rec.get("fund_policy_number"), "wide"), (line[4:11].strip(), "narrow")):
            if key and key in g_by_policy:
                g = g_by_policy[key]
                if which == "wide":
                    wide_hits += 1
                else:
                    narrow_hits += 1
                break
        else:
            misses += 1
        for k, v in g.items():
            if v is not None and rec.get(k) is None:
                rec[k] = v
        out.append(rec)

    logger.info(
        "menora_legacy: %s premium join — rows=%d wide=%d narrow=%d miss=%d "
        "| policy-guard rejects=%d/%d",
        source_name[:40], rows, wide_hits, narrow_hits, misses, guard_rejects, rows,
    )
    return out


# ────────────────────────────────────────────────────────────────────────────
# Field-position parsers (P.TXT, G.TXT)
# Reverse-engineered from 80-row sample bundles 2026-05-31.
# Positions verified against multiple rows; comments cite L0 as example.
# ────────────────────────────────────────────────────────────────────────────


def _policy_from_p_line(line: str) -> str | None:
    """Menora's policy number: a 9-wide, ZERO-PADDED field at [2:11].

    Returns None — never a truncated fallback — when the field isn't 9 digits.
    A wrong-but-plausible policy number is exactly the failure class this guard
    exists to remove; `None` degrades loudly (comparison_service._match_products
    skips a row with no policy) instead of silently mis-matching.

    Deliberately does NOT check `line[0:2] == "06"`. Every sample we have starts
    `06`, but nothing proves that holds across agents and bundles, and a mismatch
    would silently null a VALID policy. The proof that the policy lives at [2:11]
    is independent of whatever [0:2] means, so validate the policy, not its
    neighbour.

    The lstrip is load-bearing, and measured: the field is 9 wide but the policy
    inside it can be shorter. Real row from a live bundle has [2:11]='011738333'
    → 11738333, which is the value the נפרעים report carries for that client.
    Measured length histogram over a real 80-row bundle: 72×9, 7×8, 1×7 digits —
    so "always 9 digits" would be a wrong assertion.
    """
    field = line[2:11]
    if len(field) != 9 or not field.isdigit():
        return None
    return field.lstrip("0") or field


def _parse_p_line(line: str) -> dict | None:
    """Parse one row of P.TXT (customer + policy master).

    Reference row:
        06361004450400800000000100690000000000002238945619680121יחיים יבכוב...

        pos 0-1    : '06' (constant record-type marker — not interpreted)
        pos 2-10   : 9-wide zero-padded policy number  ← '361004450' above
        pos 11     : '4' (constant)
        pos 12-14  : '008'
        pos 15-27  : agent code embedded (e.g. ...0069 = agent 0069)
        pos 28-37  : ten zeros
        pos 38-48  : 10-digit block = 1 pad zero + 9-digit ת"ז (incl. check digit)
        pos 48-55  : 8-digit birthdate YYYYMMDD
        pos 56-78  : Hebrew name (22 chars, space-padded)

    NOTE: the id block is 10 chars wide ([38:48]); the check digit lives at
    position 47. A previous `line[38:47]` slice was one char short and silently
    dropped the final digit of every ת"ז (QA 2026-07-23: "missing the last
    digit"). Verified against real P.TXT: [38:48]='0022389456' → id 22389456.

    NOTE 2 — same class of bug, found the same way. The policy was read with
    `line[4:11]`, a 7-char slice that dropped its first two digits, because this
    docstring used to claim pos 0-3 was a "record-type prefix (0636/0635/0634)".
    It isn't: [0:2] is the constant '06' and the 34/35/36/37 that follows is the
    POLICY's own leading pair. QA 2026-07: "במנורה - מספר הפוליסה מופיעה בלי שני
    המספרים הראשונים". Confirmed three ways — the reference row above
    ([2:11]='361004450', [11] still the documented '4'); 66 of 77 production rows
    that lost exactly a 34/35/36/37 prefix against manually-uploaded ground
    truth; and re-parsing a real bundle, where policies matching the נפרעים
    report for the same ת"ז went from 1/80 to 80/80. See _policy_from_p_line.
    """
    try:
        policy_number = _policy_from_p_line(line)
        id_raw = line[38:48]  # full 10-char block; lstrip handles the pad zero
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
        # After the whole-field reverse, parts[0] is the GIVEN name and the
        # remainder is the surname. The old code mapped parts[0]→last_name on a
        # "Menora convention: surname first" comment — true of the raw visual
        # field, but the reverse has already undone that ordering, so every row
        # came out inverted (stored first_name='כוכבי מליחי', last_name='סיגלית'
        # for סיגלית כוכבי מליחי). Keep split(None, 1) so a two-word surname
        # stays whole.
        if len(parts) >= 2:
            first_name = parts[0]
            last_name = parts[1]
        elif parts:
            first_name = parts[0]
            last_name = None
        else:
            first_name = None
            last_name = None

        return {
            "id_number": id_number,
            "first_name": first_name,
            "last_name": last_name,
            "fund_policy_number": policy_number,
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
