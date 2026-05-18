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

from column_maps import (
    COLUMNS_INSURANCE_PRODUCTS,
    COLUMNS_INSURANCE_COVERAGES,
    COLUMNS_SUMMARY_BY_INSURER,
    COLUMNS_SUMMARY_BY_PRODUCT,
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

    return [
        _normalize_insurer(insurer_name),
        _lookup(SUG_MUTZAR_LABELS, policy.get("SUG-MUTZAR"), fallback="") or _lookup(SUG_MUTZAR_LABELS, "1"),
        policy.get("SHEM-TOCHNIT") or "",
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

    return [
        _normalize_insurer(insurer_name),
        _lookup(SUG_MUTZAR_LABELS, policy.get("SUG-MUTZAR"), fallback="") or _lookup(SUG_MUTZAR_LABELS, "1"),
        policy.get("SHEM-TOCHNIT") or "",
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
) -> tuple[list[list], list[list]]:
    """Aggregate insurance detail rows into the two summary sheets.

    Returns (summary_by_insurer, summary_by_product). Currently covers only
    the insurance half — `צבירה`/`הפקדה` columns stay 0 until savings DAT
    lands in Phase 1b.
    """
    # Column indices in COLUMNS_INSURANCE_PRODUCTS
    INS_COL = COLUMNS_INSURANCE_PRODUCTS.index("יצרן")
    ID_COL = COLUMNS_INSURANCE_PRODUCTS.index("מספר ת.ז")
    PREM_COL = COLUMNS_INSURANCE_PRODUCTS.index('סה"כ פרמיה')
    TYPE_COL = COLUMNS_INSURANCE_PRODUCTS.index("סוג מוצר")
    PROD_COL = COLUMNS_INSURANCE_PRODUCTS.index("מוצר")
    AGENT_COL = COLUMNS_INSURANCE_PRODUCTS.index("מספר סוכן")

    # Per-insurer
    by_insurer: dict[str, dict] = defaultdict(lambda: {
        "customers": set(), "products": 0, "premium": 0.0, "agent": agent_number,
    })
    for row in insurance_rows:
        k = row[INS_COL] or ""
        b = by_insurer[k]
        if row[ID_COL]:
            b["customers"].add(row[ID_COL])
        b["products"] += 1
        b["premium"] += float(row[PREM_COL] or 0)
        if b["agent"] is None and row[AGENT_COL]:
            b["agent"] = row[AGENT_COL]

    sum_ins = []
    for name, v in sorted(by_insurer.items()):
        sum_ins.append([
            name,
            v["agent"] or "",
            len(v["customers"]),
            v["products"],
            0.0,                 # צבירה בניהול — savings only
            0.0,                 # הפקדה בניהול — savings only
            round(v["premium"], 2),
        ])

    # Per (insurer, type, product)
    by_product: dict[tuple, dict] = defaultdict(lambda: {
        "customers": set(), "products": 0, "premium": 0.0, "agent": agent_number,
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

    sum_prod = []
    for key, v in sorted(by_product.items()):
        ins, typ, prod = key
        sum_prod.append([
            ins, typ, prod,
            v["agent"] or "",
            len(v["customers"]),
            v["products"],
            0.0, 0.0,
            round(v["premium"], 2),
        ])

    return sum_ins, sum_prod


def build_workbook(
    insurance_rows: list[list],
    coverage_rows: list[list],
    agent_number: str | int | None = None,
) -> Workbook:
    """Assemble the full 6-sheet workbook. Sheets 3 + 4 (savings) are written
    with headers only — Phase 1b will fill them."""
    wb = Workbook()
    # Remove the default sheet created by openpyxl
    wb.remove(wb.active)

    summary_ins, summary_prod = _build_summary_rows(insurance_rows, agent_number)

    # Sheet order matches the reference file
    _write_sheet(wb, "דוח מסכם לפי יצרן", COLUMNS_SUMMARY_BY_INSURER, summary_ins)
    _write_sheet(wb, "דוח מסכם לפי מוצר", COLUMNS_SUMMARY_BY_PRODUCT, summary_prod)
    # Empty placeholders (headers only) for savings sheets — filled in Phase 1b
    _write_sheet(wb, "מוצרי חיסכון", [
        "יצרן", "סוג מוצר", "מוצר", "מס' מ\"ה", "מס' חשבון/פוליסה", "סוכנות",
        "שם פרטי לקוח", "שם משפחה לקוח", "מספר ת.ז", "סלולרי לקוח", 'דוא"ל לקוח',
        "תאריך לידה", "גיל", "מגדר", "יישוב", "סיווג לקוח", "סטטוס מוצר",
        "תאריך עדכון סטטוס", "תאריך הצטרפות למוצר", "מעמד", "מזהה מעסיק",
        "שם מעסיק", "צבירה", "שכר למוצר", "שיעור תגמולים עובד",
        "שיעור תגמולים מעסיק", "שיעור הפרשה לפיצויים", "הפקדה אחרונה",
        "תאריך הפקדה אחרונה", "דמי ניהול מהפקדה", "דמי ניהול מצבירה",
        "מקדם מובטח לפרישה", "מסלול ביטוח (פנסיה)", "מספר סוכן",
        "תיאור מספר סוכן", "מיופה כוח אחרון", 'מת"ל', "נכון ליום", "קידוד אחיד",
    ], [])
    _write_sheet(wb, "מסלולי השקעה", [
        "יצרן", "סוג מוצר", "מוצר", "מס' מ\"ה", "מס' חשבון/פוליסה",
        "שם פרטי לקוח", "שם משפחה לקוח", "מספר ת.ז", "סלולרי לקוח",
        'דוא"ל לקוח', "סטטוס מוצר", "תאריך עדכון סטטוס",
        "תאריך הצטרפות למוצר", "מעמד", "מזהה מעסיק", "שם מעסיק",
        "צבירה במוצר", "מספר סוכן", "תיאור מספר סוכן", 'מת"ל', "נכון ליום",
        "שם מסלול", "קוד מסלול", "צבירה במסלול", "תשואה חודש דווח",
        "תשואה מצטברת (מתחילת שנה)", "תשואה מצטברת (36 חודשים)",
        "תשואה מצטברת (60 חודשים)", "תשואה שנתית ממוצעת (36 חודשים)",
        "תשואה שנתית ממוצעת (60 חודשים)", "חודש דווח תשואות",
    ], [])
    _write_sheet(wb, "מוצרי ביטוח", COLUMNS_INSURANCE_PRODUCTS, insurance_rows)
    _write_sheet(wb, "מוצרי ביטוח (כיסויים)", COLUMNS_INSURANCE_COVERAGES, coverage_rows)

    return wb
