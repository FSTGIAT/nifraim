"""Build the 6-sheet production xlsx from Mimshak DAT records.

Phase 1a scope — only the insurance half is filled in (sheets 5 + 6 + the
insurance-only summary rows for sheets 1 + 2). Savings sheets are created
empty with headers so Nifraim's parser still sees the workbook structure;
Phase 1b will populate them from a savings DAT.

Each per-sheet builder takes pre-shaped dicts (not raw XML) so callers can
merge across multiple insurers before writing.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

# Import the column constants whether this module is loaded as a package
# submodule (app.services.mimshak.xlsx_writer) or standalone via the sys.path
# fallback in to_production_xlsx.py.
try:
    from .column_maps import (
        COLUMNS_INSURANCE_PRODUCTS,
        COLUMNS_INSURANCE_COVERAGES,
        COLUMNS_SUMMARY_BY_INSURER,
        COLUMNS_SUMMARY_BY_PRODUCT,
        COLUMNS_SAVINGS_PRODUCTS,
        COLUMNS_INVESTMENT_TRACKS,
        INSURER_NAME_OVERRIDES,
        SUG_MUTZAR_LABELS,
        STATUS_POLISA_LABELS,
        SUG_TEUDA_LABELS,
        MIN_LABELS,
        SUG_MEVUTACH_LABELS,
        TADIRUT_TASHLUM_LABELS,
        SUG_KISUI_LABELS,
        COV_PERIOD_DEFINED,
        COV_PERIOD_OPEN,
    )
except ImportError:
    from column_maps import (  # type: ignore
        COLUMNS_INSURANCE_PRODUCTS,
        COLUMNS_INSURANCE_COVERAGES,
        COLUMNS_SUMMARY_BY_INSURER,
        COLUMNS_SUMMARY_BY_PRODUCT,
        COLUMNS_SAVINGS_PRODUCTS,
        COLUMNS_INVESTMENT_TRACKS,
        INSURER_NAME_OVERRIDES,
        SUG_MUTZAR_LABELS,
        STATUS_POLISA_LABELS,
        SUG_TEUDA_LABELS,
        MIN_LABELS,
        SUG_MEVUTACH_LABELS,
        TADIRUT_TASHLUM_LABELS,
        SUG_KISUI_LABELS,
        COV_PERIOD_DEFINED,
        COV_PERIOD_OPEN,
    )


# ── Value formatters ─────────────────────────────────────────────────────

def _fmt_date(raw: str | None) -> date | None:
    """YYYYMMDD (or YYYYMMDDHHMMSS) → python date."""
    if not raw:
        return None
    digits = "".join(c for c in raw if c.isdigit())
    if len(digits) < 8:
        return None
    try:
        return date(int(digits[:4]), int(digits[4:6]), int(digits[6:8]))
    except (ValueError, TypeError):
        return None


def _compute_age(dob: date | None, ref_date: date | None) -> int | None:
    if not dob or not ref_date:
        return None
    age = ref_date.year - dob.year
    if (ref_date.month, ref_date.day) < (dob.month, dob.day):
        age -= 1
    return age if 0 <= age <= 120 else None


def _lookup(table: dict[str, str], code: str | None, fallback: str = "") -> str:
    if code is None:
        return fallback
    return table.get(str(code).strip(), fallback or str(code))


def _to_float(raw: str | None) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        return float(str(raw).replace(",", ""))
    except (ValueError, TypeError):
        return None


def _strip_zeros(s: str | None) -> str | None:
    if not s:
        return s
    out = s.lstrip("0")
    return out or "0"


def _id_number_int(s: str | None):
    """Return id_number as int (reference xlsx stores it as int, not string)."""
    clean = _strip_zeros(s)
    if not clean:
        return ""
    try:
        return int(clean)
    except (ValueError, TypeError):
        return clean


def _format_phone(raw: str | None) -> str:
    """Israeli mobile: `0544280175` → `054-428-0175`. Keeps any other format unchanged."""
    if not raw:
        return ""
    digits = "".join(c for c in raw if c.isdigit())
    if len(digits) == 10 and digits.startswith("05"):
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return raw


def _normalize_insurer(name: str | None) -> str:
    if not name:
        return ""
    return INSURER_NAME_OVERRIDES.get(name, name)


# Migdal's production report uses a fixed bucket label per `סוג מוצר` in the
# `מוצר` column — every life row reads "מגדל - חיים", every health row
# "מגדל - בריאות", etc. The raw policy product name (e.g. "מגדל קשת לפרט")
# lives in DAT's SHEM-TOCHNIT, but the report normalizes it away.
_PRODUCT_BUCKET_BY_SUG: dict[str, str] = {
    "ביטוח חיים": "מגדל - חיים",
    "ביטוח בריאות": "מגדל - בריאות",
    "ביטוח חיים משכנתא": "מגדל - ביטוח חיים משכנתא",
    "ביטוח סיעוד": "מגדל - סיעוד",
    "ביטוח כללי": "מגדל - כללי",
    "ביטוח נסיעות": "מגדל - נסיעות",
}


def _bucket_product_label(sug_mutzar: str) -> str:
    """Return the REF-style `מוצר` bucket label for a given `סוג מוצר`."""
    return _PRODUCT_BUCKET_BY_SUG.get(sug_mutzar, sug_mutzar)


def _default_employer_name(customer: dict) -> str:
    """Personal-insurance rows in the reference xlsx default `שם מעסיק` to
    "<last_name> <first_name>" (last name first)."""
    last = (customer.get("SHEM-MISHPACHA") or "").strip()
    first = (customer.get("SHEM-PRATI") or "").strip()
    if last or first:
        return f"{last} {first}".strip()
    return ""


def _coverage_period_label(start: date | None, end: date | None) -> str:
    return COV_PERIOD_DEFINED if end else COV_PERIOD_OPEN


def _pick_coverage_premium(cov: dict) -> float:
    """Pick the most relevant "monthly premium" value from a ZihuiKisui block.
    Precedence: DMEI-BITUAH-LETASHLUM-BAPOAL (actual premium due) → PREMIA-ZFOYA
    (expected premium) → SCHUM-BITUACH. All may be zero for paid-up policies."""
    for key in ("DMEI-BITUAH-LETASHLUM-BAPOAL", "PREMIA-ZFOYA", "SCHUM-BITUACH"):
        v = _to_float(cov.get(key))
        if v and v > 0:
            return v
    return _to_float(cov.get("SCHUM-BITUACH")) or 0.0


# ── Row shaping ──────────────────────────────────────────────────────────

def build_insurance_product_row(
    *,
    insurer_name: str,
    customer: dict,          # YeshutLakoach leaves
    policy: dict,            # HeshbonOPolisa.raw_leaves
    coverages: list[dict],   # ZihuiKisui leaves, used for total premium
    mbt_person: dict | None,
    valuation_date: date | None,
    agency_name: str = "",
) -> list:
    """Return a list of cells in COLUMNS_INSURANCE_PRODUCTS order."""
    dob = _fmt_date(customer.get("TAARICH-LEYDA"))
    age = _compute_age(dob, valuation_date)
    # Sum picks per-coverage premium (not just SCHUM-BITUACH). Mirrors SaaS behavior.
    total_premium = sum(_pick_coverage_premium(c) for c in coverages)
    email = customer.get("E-MAIL") or (mbt_person or {}).get("email")
    phone = customer.get("MISPAR-CELLULARI") or (mbt_person or {}).get("mobile")
    city = customer.get("SHEM-YISHUV") or (mbt_person or {}).get("city_he")
    id_int = _id_number_int(customer.get("MISPAR-ZIHUY-LAKOACH"))

    # Employer defaults for personal-insurance rows
    employer_id = policy.get("MPR-MAASIK-BE-YATZRAN") or (id_int if isinstance(id_int, int) else "")
    employer_name = policy.get("SHEM-MAASIK") or _default_employer_name(customer)

    # Normalize `מוצר` to REF's bucket label (matches Migdal's production
    # report convention — see `_bucket_product_label`). The raw SHEM-TOCHNIT
    # value (e.g. "מגדל קשת לפרט") is preserved on the coverage sheet, not here.
    sug_mutzar = (
        _lookup(SUG_MUTZAR_LABELS, policy.get("SUG-MUTZAR"), fallback="")
        or _lookup(SUG_MUTZAR_LABELS, "1")
    )
    return [
        _normalize_insurer(insurer_name),
        sug_mutzar,
        _bucket_product_label(sug_mutzar),
        policy.get("MISPAR-POLISA-O-HESHBON") or "",
        agency_name,
        customer.get("SHEM-PRATI") or "",
        customer.get("SHEM-MISHPACHA") or "",
        id_int,
        _format_phone(phone),
        email or "",
        dob,
        age,
        _lookup(MIN_LABELS, customer.get("MIN")),
        city or "",
        "",  # סיווג לקוח (not in DAT)
        round(total_premium, 2) if total_premium else 0.0,
        _lookup(STATUS_POLISA_LABELS, policy.get("STATUS-POLISA-O-CHESHBON")),
        _fmt_date(policy.get("TAARICH-IDKUN-STATUS")),
        _fmt_date(policy.get("TAARICH-HITZTARFUT-MUTZAR") or policy.get("TAARICH-HITZTARFUT-RISHON")),
        employer_id,
        employer_name,
        policy.get("MPR-MEFITZ-BE-YATZRAN") or "",
        "",  # תיאור מספר סוכן — blank in reference too
        "",  # מיופה כוח אחרון (TODO: PerutMeyupeKoach name resolution)
        agency_name,  # מת"ל — same value as סוכנות in reference
        _fmt_date(policy.get("TAARICH-NECHONUT")),
    ]


def build_lifehlth_product_row(
    *,
    cells: list[str],
    mbt_person: dict | None,
    insurer_name: str,
    agent_num: str | None,
) -> list:
    """Construct an insurance product row directly from a LIFEHLTH.MBT line.

    LIFEHLTH.MBT carries the agent's FULL policy register (life + health +
    mortgage life), not just the current-month HOLDNG slice that the DAT
    file ships. Column layout (verified against the May 2026 Migdal Safes
    sample):

        col  2 — product class (1=life, 2=health, 3=mortgage life, 4=other)
        col  9 — full policy id (`01` + 9 digits)
        col 10 — short customer id (9-digit national)
        col 14 — customer full name (visual-Hebrew encoding)
        col 15 — policy start date (DDMMYYYY)
        col 16 — policy end date
        col 17 — status code (1 = active)
        col 39 — last activity date
        col 48 — annual premium
        col 49 — monthly premium

    The first three classes match the Migdal "production report" product
    labels 1:1 (ביטוח חיים / ביטוח בריאות / ביטוח חיים משכנתא); class 4 falls
    back to a generic Hebrew label.
    """
    # Import here to avoid circular imports at module load
    from app.services.mimshak.mbt import _maybe_reverse_hebrew

    def _safe(idx):
        return cells[idx] if len(cells) > idx else ""

    # MBT files store dates as DDMMYYYY (e.g. "01062015" → 2015-06-01),
    # not the YYYYMMDD that _fmt_date expects. Swap to YYYYMMDD first.
    def _fmt_ddmmyyyy(raw: str | None) -> date | None:
        if not raw or len(raw) != 8 or not raw.isdigit():
            return None
        return _fmt_date(raw[4:8] + raw[2:4] + raw[0:2])

    # Col 10 is the policy id (8-9 digits), col 9 is the customer id
    # (`01` + 9-digit national). Verified by PERSON.MBT overlap test.
    policy_id = _strip_zeros(_safe(10)) or _safe(10)
    raw_cid = _safe(9)
    if raw_cid.startswith("01") and len(raw_cid) == 11:
        raw_cid = raw_cid[2:]
    customer_id_raw = raw_cid.lstrip("0") or raw_cid
    id_int = _id_number_int(customer_id_raw)

    name_he = _maybe_reverse_hebrew(_safe(14))
    parts = name_he.strip().split(" ", 1)
    first_name = parts[0] if parts and parts[0] else ""
    last_name = parts[1] if len(parts) > 1 else ""

    # LIFEHLTH.MBT — empirically verified against REF
    # (מגדל פרודוקציה חהשוואת רועי.xlsx): every col-2 class (1-5) maps to
    # ביטוח בריאות in the operator's reference report (109/109 policies match
    # by policy number). The col-2 codes are health sub-types (dental,
    # surgery, etc.), not a life/health split despite the file name.
    sug_mutzar, product_name = "ביטוח בריאות", "מגדל - בריאות"

    monthly_premium = _to_float(_safe(49)) or 0.0
    start_date = _fmt_ddmmyyyy(_safe(15))
    last_activity = _fmt_ddmmyyyy(_safe(39))
    status_code = _safe(17)
    status_label = "פעיל" if status_code == "1" else ("מבוטל" if status_code else "")

    email = (mbt_person or {}).get("email") or ""
    phone = (mbt_person or {}).get("mobile") or ""
    city = (mbt_person or {}).get("city_he") or ""
    dob = _fmt_ddmmyyyy((mbt_person or {}).get("dob_raw"))
    age = _compute_age(dob, datetime.now().date()) if dob else None
    gender = _lookup(MIN_LABELS, (mbt_person or {}).get("gender_code"))

    return [
        _normalize_insurer(insurer_name),
        sug_mutzar,
        product_name,
        policy_id,
        "",  # סוכנות (not in MBT — same as DAT path)
        first_name,
        last_name,
        id_int,
        _format_phone(phone),
        email,
        dob,
        age,
        gender,
        city,
        "",  # סיווג לקוח
        round(monthly_premium, 2),
        status_label,
        last_activity,
        start_date,
        id_int,  # מזהה מעסיק (personal policy → same as ID)
        _default_employer_name({"SHEM-PRATI": first_name, "SHEM-MISHPACHA": last_name}),
        agent_num or "",
        "",  # תיאור מספר סוכן
        "",  # מיופה כוח אחרון
        "",  # מת"ל
        None,  # נכון ליום (DAT-specific; LIFEHLTH has no global valuation date)
    ]


def build_life_product_row(
    *,
    cells: list[str],
    mbt_person: dict | None,
    insurer_name: str,
    agent_num: str | None,
) -> list:
    """Construct an insurance product row directly from a LIFE.MBT line.

    LIFE.MBT carries the agent's primary life policies. The DAT HOLDNG
    snapshot normally covers the same set, but this builder exists as a
    defensive fallback for the edge case where a LIFE.MBT entry is absent
    from the current month's DAT (e.g. a paid-up policy that fell out of
    the active-holdings slice). Column layout (verified against the May
    2026 Migdal Safes sample, 133-column rows):

        col 10 — policy id (`0` + 8 digits) — matches DAT MISPAR-POLISA-O-HESHBON
        col 11 — customer national id (`01` + 9 digits)
        col 14 — customer name (visual-order Hebrew)
        col 15 — sign date (DDMMYYYY)
        col 16 — end date (DDMMYYYY)
        col 20 — annual premium amount
    """
    from app.services.mimshak.mbt import _maybe_reverse_hebrew

    def _safe(idx):
        return cells[idx] if len(cells) > idx else ""

    def _fmt_ddmmyyyy(raw: str | None) -> date | None:
        if not raw or len(raw) != 8 or not raw.isdigit():
            return None
        return _fmt_date(raw[4:8] + raw[2:4] + raw[0:2])

    policy_id = _strip_zeros(_safe(10)) or _safe(10)
    raw_cid = _safe(11)
    if raw_cid.startswith("01") and len(raw_cid) == 11:
        raw_cid = raw_cid[2:]
    customer_id_raw = raw_cid.lstrip("0") or raw_cid
    id_int = _id_number_int(customer_id_raw)

    # Prefer PERSON.MBT name (logical-order, already-reversed) over the
    # visual-order col 14 fallback.
    person = mbt_person or {}
    first_name = person.get("first_name_he") or ""
    last_name = person.get("last_name_he") or ""
    if not (first_name or last_name):
        name_he = _maybe_reverse_hebrew(_safe(14)).strip()
        parts = name_he.split(" ", 1)
        first_name = parts[0] if parts and parts[0] else ""
        last_name = parts[1] if len(parts) > 1 else ""

    annual_premium = _to_float(_safe(20)) or 0.0
    monthly_premium = round(annual_premium / 12, 2) if annual_premium else 0.0
    start_date = _fmt_ddmmyyyy(_safe(15))
    end_date = _fmt_ddmmyyyy(_safe(16))
    today = datetime.now().date()
    status_label = "פעיל" if (end_date is None or end_date >= today) else "סילוק"

    sug_mutzar = "ביטוח חיים"
    product_name = _bucket_product_label(sug_mutzar)

    email = person.get("email") or ""
    phone = person.get("mobile") or ""
    city = person.get("city_he") or ""
    dob = _fmt_ddmmyyyy(person.get("dob_raw"))
    age = _compute_age(dob, today) if dob else None
    gender = _lookup(MIN_LABELS, person.get("gender_code"))

    return [
        _normalize_insurer(insurer_name),
        sug_mutzar,
        product_name,
        policy_id,
        "",  # סוכנות
        first_name,
        last_name,
        id_int,
        _format_phone(phone),
        email,
        dob,
        age,
        gender,
        city,
        "",  # סיווג לקוח
        monthly_premium,
        status_label,
        None,  # תאריך עדכון סטטוס
        start_date,
        id_int,  # מזהה מעסיק
        _default_employer_name({"SHEM-PRATI": first_name, "SHEM-MISHPACHA": last_name}),
        agent_num or "",
        "",  # תיאור מספר סוכן
        "",  # מיופה כוח אחרון
        "",  # מת"ל
        None,  # נכון ליום
    ]


def build_covrlife_product_row(
    *,
    cells: list[str],
    mbt_person: dict | None,
    insurer_name: str,
    agent_num: str | None,
) -> list:
    """Construct an insurance product row from a COVRLIFE.MBT line.

    COVRLIFE carries riders/coverages — 399 raw rows for 115 distinct
    policies in the May 2026 Migdal sample. One row per distinct policy
    is sufficient for the production view; the coverage name (col 19)
    becomes the product label.

    Column layout (verified):
        col  0 — rider_code
        col  1 — policy_ref (`01` + 9 digits)
        col  4 — rider_start (DDMMYYYY)
        col  5 — rider_end
        col  8 — annual premium
        col  9 — monthly premium
        col 18 — short customer id (9 digits)
        col 19 — coverage name (LOGICAL Hebrew, already readable — used as
                 product label and keyword-classified into ביטוח חיים /
                 בריאות / משכנתא)
    """
    def _safe(idx):
        return cells[idx] if len(cells) > idx else ""

    policy_id = _strip_zeros(_safe(1)) or _safe(1)
    customer_short = _strip_zeros(_safe(18)) or _safe(18)
    id_int = _id_number_int(_safe(18))
    # NOT reversed. This column is stored in LOGICAL order, unlike the name
    # columns in the same bundle (PERSON col 24, LIFE/LIFEHLTH col 14) which
    # genuinely are visual. It used to go through `_maybe_reverse_hebrew`, which
    # turned 'ביטוח מעורב - מסולק' into 'ברועמ חוטיב-קלוסמ' and shipped that as
    # the product name in the merged production file. Measured over 8 separate
    # Migdal downloads: 191-211 logical rows per file, zero visual. Do not add a
    # reverse back here without re-measuring — and note the keyword classifier
    # below only works on logical text, so a reversed value also silently
    # defaulted every coverage to ביטוח חיים.
    coverage_name = _safe(19).strip()

    # Classify product type from coverage name keywords. Order matters —
    # match the more specific terms first.
    health_kw = ("ניתוח", "אשפוז", "תרופ", "בריאות", "רפוא", "מחלות", "שיניים", "סיעוד")
    mort_kw   = ("משכנתא",)
    life_kw   = ("חיים", "מוות", "נכות", "תאונה", "אובדן")
    if any(kw in coverage_name for kw in mort_kw):
        sug_mutzar, product = "ביטוח חיים משכנתא", "מגדל - ביטוח חיים משכנתא"
    elif any(kw in coverage_name for kw in health_kw):
        sug_mutzar, product = "ביטוח בריאות", coverage_name or "מגדל - בריאות"
    elif any(kw in coverage_name for kw in life_kw):
        sug_mutzar, product = "ביטוח חיים", coverage_name or "מגדל - חיים"
    else:
        sug_mutzar, product = "ביטוח חיים", coverage_name or "מגדל"

    monthly_premium = _to_float(_safe(9)) or 0.0
    start_date = _fmt_date(_safe(4))
    status_label = "פעיל" if _safe(3) == "01" else ("מבוטל" if _safe(3) else "")

    # Customer details via PERSON.MBT lookup
    person = mbt_person or {}
    first_name = person.get("first_name_he") or ""
    last_name = person.get("last_name_he") or ""
    email = person.get("email") or ""
    phone = person.get("mobile") or ""
    city = person.get("city_he") or ""
    dob = _fmt_date(person.get("dob_raw"))
    age = _compute_age(dob, datetime.now().date()) if dob else None
    gender = _lookup(MIN_LABELS, person.get("gender_code"))

    return [
        _normalize_insurer(insurer_name),
        sug_mutzar,
        product,
        policy_id,
        "",  # סוכנות
        first_name,
        last_name,
        id_int,
        _format_phone(phone),
        email,
        dob,
        age,
        gender,
        city,
        "",  # סיווג לקוח
        round(monthly_premium, 2),
        status_label,
        None,  # תאריך עדכון סטטוס
        start_date,
        id_int,  # מזהה מעסיק
        f"{first_name} {last_name}".strip() or "",
        agent_num or "",
        "",  # תיאור מספר סוכן
        "",  # מיופה כוח אחרון
        "",  # מת"ל
        None,  # נכון ליום
    ]


def build_coverage_row(
    *,
    insurer_name: str,
    customer: dict,
    policy: dict,
    coverage: dict,            # ZihuiKisui leaves
    insured_customer: dict | None,  # if insured ≠ customer, the other YeshutLakoach
    mbt_person: dict | None,
    valuation_date: date | None,
    agency_name: str = "",
    payment_frequency_label: str = "",
) -> list:
    """Return a list of cells in COLUMNS_INSURANCE_COVERAGES order."""
    dob = _fmt_date(customer.get("TAARICH-LEYDA"))
    age = _compute_age(dob, valuation_date)
    email = customer.get("E-MAIL") or (mbt_person or {}).get("email")
    phone = customer.get("MISPAR-CELLULARI") or (mbt_person or {}).get("mobile")

    # Insured identification — may be a different person than the customer
    insured_id_raw = coverage.get("MISPAR-ZIHUY-LAKOACH")  # lives in PirteiMevutach
    insured_id_int = _id_number_int(insured_id_raw)
    customer_id = _strip_zeros(customer.get("MISPAR-ZIHUY-LAKOACH") or "")
    # Reference leaves "שם מבוטח" blank when the insured IS the primary customer;
    # it's filled only when a different person is insured.
    if insured_customer and _strip_zeros(insured_id_raw or "") != customer_id:
        insured_name = f"{insured_customer.get('SHEM-PRATI','')} {insured_customer.get('SHEM-MISHPACHA','')}".strip()
    else:
        insured_name = ""

    start = _fmt_date(coverage.get("TAARICH-TCHILAT-KISUY"))
    end = _fmt_date(coverage.get("TAARICH-TOM-KISUY"))
    period_years = (end.year - start.year) if (start and end) else None

    premium = _pick_coverage_premium(coverage)
    sum_insured = (_to_float(coverage.get("SCHUM-BITUAH-LEMAVET"))
                   or _to_float(coverage.get("SCHUM-KISUI")))

    # Same `מוצר` bucket-label normalization as the insurance-products sheet —
    # see _bucket_product_label. SHEM-TOCHNIT (e.g. "מגדל קשת לפרט") is the
    # raw Migdal policy name; the report rolls it up to "מגדל - חיים" etc.
    cov_sug_mutzar = (
        _lookup(SUG_MUTZAR_LABELS, policy.get("SUG-MUTZAR"), fallback="")
        or _lookup(SUG_MUTZAR_LABELS, "1")
    )
    return [
        _normalize_insurer(insurer_name),
        cov_sug_mutzar,
        _bucket_product_label(cov_sug_mutzar),
        policy.get("MISPAR-POLISA-O-HESHBON") or "",
        customer.get("SHEM-PRATI") or "",
        customer.get("SHEM-MISHPACHA") or "",
        _id_number_int(customer.get("MISPAR-ZIHUY-LAKOACH")),
        _format_phone(phone),
        email or "",
        dob,
        age,
        _lookup(MIN_LABELS, customer.get("MIN")),
        agency_name,  # מת"ל
        policy.get("MPR-MEFITZ-BE-YATZRAN") or "",
        "",  # תיאור מספר סוכן — blank in reference
        _lookup(SUG_KISUI_LABELS, coverage.get("SUG-KISUI-ETZEL-YATZRAN")),
        coverage.get("SHEM-KISUI-YATZRAN") or "",
        _lookup(SUG_MEVUTACH_LABELS, coverage.get("SUG-MEVUTACH")),
        insured_name,
        insured_id_int,
        _coverage_period_label(start, end),
        start,
        end,
        payment_frequency_label,
        round(premium, 2) if premium else 0.0,
        round(sum_insured, 2) if sum_insured else 0.0,
        _to_float(coverage.get("KOD-NISPACH-KISUY")) or coverage.get("KOD-NISPACH-KISUY") or "",
        _to_float(coverage.get("ACHUZ-TOSEFET-REFUIT")) or "",
        _to_float(coverage.get("ACHUZ-TOSEFET-MIKTZUIT")) or "",
        _fmt_date(policy.get("TAARICH-NECHONUT")),
    ]


# ── Workbook assembly ────────────────────────────────────────────────────

_HEADER_FONT = Font(bold=True, color="FFFFFF")
_HEADER_FILL = PatternFill(start_color="305496", end_color="305496", fill_type="solid")
_HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _write_sheet(wb: Workbook, title: str, columns: list[str], rows: list[list]):
    ws = wb.create_sheet(title=title)
    ws.sheet_view.rightToLeft = True
    # Header
    for i, col in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=i, value=col)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = _HEADER_ALIGN
    # Data
    for r_idx, row in enumerate(rows, start=2):
        for c_idx, value in enumerate(row, start=1):
            cell = ws.cell(row=r_idx, column=c_idx, value=value)
            if isinstance(value, (int, float)) and columns[c_idx - 1] in (
                'סה"כ פרמיה', "פרמיה", "סכום ביטוח", "צבירה בניהול",
                "הפקדה בניהול", "פרמיה בניהול",
            ):
                cell.number_format = "#,##0.00"
            elif isinstance(value, (date, datetime)):
                cell.number_format = "dd/mm/yyyy"
    # Column widths — simple heuristic
    for i, col in enumerate(columns, start=1):
        ws.column_dimensions[get_column_letter(i)].width = max(14, min(40, len(col) + 6))
    ws.freeze_panes = "A2"


def _build_summary_rows(
    insurance_rows: list[list],
    agent_number: str | int | None = None,
    savings_rows: list[list] | None = None,
) -> tuple[list[list], list[list]]:
    """Aggregate insurance + savings detail rows into the two summary sheets.

    Returns (summary_by_insurer, summary_by_product). Insurance rows feed the
    `פרמיה בניהול` column; savings rows feed `צבירה בניהול`. ``savings_rows``
    defaults to empty (the original Migdal-only behaviour).
    """
    savings_rows = savings_rows or []

    # Column indices in COLUMNS_INSURANCE_PRODUCTS
    INS_COL = COLUMNS_INSURANCE_PRODUCTS.index("יצרן")
    ID_COL = COLUMNS_INSURANCE_PRODUCTS.index("מספר ת.ז")
    PREM_COL = COLUMNS_INSURANCE_PRODUCTS.index('סה"כ פרמיה')
    TYPE_COL = COLUMNS_INSURANCE_PRODUCTS.index("סוג מוצר")
    PROD_COL = COLUMNS_INSURANCE_PRODUCTS.index("מוצר")
    AGENT_COL = COLUMNS_INSURANCE_PRODUCTS.index("מספר סוכן")

    # Column indices in COLUMNS_SAVINGS_PRODUCTS (sheet 3)
    S_INS_COL = COLUMNS_SAVINGS_PRODUCTS.index("יצרן")
    S_ID_COL = COLUMNS_SAVINGS_PRODUCTS.index("מספר ת.ז")
    S_TYPE_COL = COLUMNS_SAVINGS_PRODUCTS.index("סוג מוצר")
    S_PROD_COL = COLUMNS_SAVINGS_PRODUCTS.index("מוצר")
    S_AGENT_COL = COLUMNS_SAVINGS_PRODUCTS.index("מספר סוכן")
    S_ACCUM_COL = COLUMNS_SAVINGS_PRODUCTS.index("צבירה")

    # Per-insurer (premium from insurance rows, accumulation from savings rows)
    by_insurer: dict[str, dict] = defaultdict(lambda: {
        "customers": set(), "products": 0, "premium": 0.0, "accum": 0.0, "agent": agent_number,
    })
    for row in insurance_rows:
        b = by_insurer[row[INS_COL] or ""]
        if row[ID_COL]:
            b["customers"].add(row[ID_COL])
        b["products"] += 1
        b["premium"] += float(row[PREM_COL] or 0)
        if b["agent"] is None and row[AGENT_COL]:
            b["agent"] = row[AGENT_COL]
    for row in savings_rows:
        b = by_insurer[row[S_INS_COL] or ""]
        if row[S_ID_COL]:
            b["customers"].add(row[S_ID_COL])
        b["products"] += 1
        b["accum"] += float(row[S_ACCUM_COL] or 0)
        if b["agent"] is None and row[S_AGENT_COL]:
            b["agent"] = row[S_AGENT_COL]

    sum_ins = []
    for name, v in sorted(by_insurer.items()):
        sum_ins.append([
            name,
            v["agent"] or "",
            len(v["customers"]),
            v["products"],
            round(v["accum"], 2),    # צבירה בניהול
            0.0,                     # הפקדה בניהול — deposit not tracked yet
            round(v["premium"], 2),
        ])

    # Per (insurer, type, product)
    by_product: dict[tuple, dict] = defaultdict(lambda: {
        "customers": set(), "products": 0, "premium": 0.0, "accum": 0.0, "agent": agent_number,
    })
    for row in insurance_rows:
        key = (row[INS_COL] or "", row[TYPE_COL] or "", row[PROD_COL] or "")
        b = by_product[key]
        if row[ID_COL]:
            b["customers"].add(row[ID_COL])
        b["products"] += 1
        b["premium"] += float(row[PREM_COL] or 0)
        if b["agent"] is None and row[AGENT_COL]:
            b["agent"] = row[AGENT_COL]
    for row in savings_rows:
        key = (row[S_INS_COL] or "", row[S_TYPE_COL] or "", row[S_PROD_COL] or "")
        b = by_product[key]
        if row[S_ID_COL]:
            b["customers"].add(row[S_ID_COL])
        b["products"] += 1
        b["accum"] += float(row[S_ACCUM_COL] or 0)
        if b["agent"] is None and row[S_AGENT_COL]:
            b["agent"] = row[S_AGENT_COL]

    sum_prod = []
    for key, v in sorted(by_product.items()):
        ins, typ, prod = key
        sum_prod.append([
            ins, typ, prod,
            v["agent"] or "",
            len(v["customers"]),
            v["products"],
            round(v["accum"], 2), 0.0,
            round(v["premium"], 2),
        ])

    return sum_ins, sum_prod


def build_workbook(
    insurance_rows: list[list],
    coverage_rows: list[list],
    agent_number: str | int | None = None,
    savings_rows: list[list] | None = None,
    investment_rows: list[list] | None = None,
) -> Workbook:
    """Assemble the full 6-sheet workbook.

    ``savings_rows`` (sheet 3, מוצרי חיסכון) and ``investment_rows`` (sheet 4,
    מסלולי השקעה) are optional — default ``None`` keeps the original Migdal
    behaviour of writing those sheets with headers only. The "run all portals"
    aggregator passes savings rows so accumulation/gemel products land on
    sheet 3 with their צבירה values."""
    savings_rows = savings_rows or []
    investment_rows = investment_rows or []
    wb = Workbook()
    # Remove the default sheet created by openpyxl
    wb.remove(wb.active)

    summary_ins, summary_prod = _build_summary_rows(insurance_rows, agent_number, savings_rows)

    # Sheet order matches the reference file
    _write_sheet(wb, "דוח מסכם לפי יצרן", COLUMNS_SUMMARY_BY_INSURER, summary_ins)
    _write_sheet(wb, "דוח מסכם לפי מוצר", COLUMNS_SUMMARY_BY_PRODUCT, summary_prod)
    _write_sheet(wb, "מוצרי חיסכון", COLUMNS_SAVINGS_PRODUCTS, savings_rows)
    _write_sheet(wb, "מסלולי השקעה", COLUMNS_INVESTMENT_TRACKS, investment_rows)
    _write_sheet(wb, "מוצרי ביטוח", COLUMNS_INSURANCE_PRODUCTS, insurance_rows)
    _write_sheet(wb, "מוצרי ביטוח (כיסויים)", COLUMNS_INSURANCE_COVERAGES, coverage_rows)

    return wb
