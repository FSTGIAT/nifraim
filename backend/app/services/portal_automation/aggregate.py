"""Aggregate the per-company files downloaded during a "run all portals" batch
into the two canonical merged files:

  • production → ONE 6-sheet xlsx in the reference schema (build_workbook)
  • נפרעים     → ONE unified commission xlsx (COLUMNS_UNIFIED_NIFRAIM)

Both are built from the already-parsed ClientRecord dicts (every portal's
download is parsed to the same normalized fields), so a single mapper covers
all insurers. The production output re-parses via the existing
`_parse_production`; the נפרעים output via the new `unified_nifraim` parser.
"""

from __future__ import annotations

import io
from datetime import date, datetime

from app.services.rate_select import (
    accumulation_based,
    entity_kind,
    pure_risk_insurance,
    savings_product_type,
)
from app.services.mimshak.column_maps import (
    COLUMNS_INSURANCE_PRODUCTS,
    COLUMNS_SAVINGS_PRODUCTS,
)
from app.services.mimshak.xlsx_writer import (
    build_workbook,
    _id_number_int,
    _format_phone,
)
from app.utils.hebrew_mappings import COLUMNS_UNIFIED_NIFRAIM
from app.utils.company_norm import canonical_company


# ── helpers ──────────────────────────────────────────────────────────────

def _f(v) -> float:
    """Best-effort float; '' / None / junk → 0.0."""
    if v in (None, ""):
        return 0.0
    try:
        return float(str(v).replace(",", ""))
    except (ValueError, TypeError):
        return 0.0


def _d(v):
    """Pass dates through; everything else stays as-is (the sheet writer only
    special-cases date/datetime, so non-dates render verbatim)."""
    if isinstance(v, (date, datetime)):
        return v
    return v or ""


def classify_record(rec: dict) -> str:
    """'savings' for accumulation/gemel products, else 'insurance'.

    Reuses `accumulation_based` (gemel/השתלמות/חיסכון = savings; pension &
    pure-risk = insurance), plus an accumulation-without-premium heuristic.

    A KNOWN pure-risk product type beats that heuristic. The heuristic exists
    for rows whose product type is empty/unrecognised; letting it also override
    an explicit בריאות/חיים/סיעודי/משכנתא put every Phoenix MU life row on the
    savings sheet under the PENSION legal entity, because that parser stores an
    accumulation and deliberately leaves premium None (it refuses to fabricate a
    premium from an unverified column — see phoenix_mu.py). "No premium" is a
    statement about the source file, not evidence the policy is a savings one.
    """
    accum = _f(rec.get("accumulation"))
    premium = _f(rec.get("total_premium"))
    product_type = rec.get("product_type")
    if accumulation_based(product_type, accum):
        return "savings"
    # A known product type decides the sheet on its own — BOTH directions. A
    # גמל/השתלמות row whose accumulation column arrived empty is still savings
    # (14 Harel rows were filed as insurance under the INSURANCE legal entity
    # for exactly this reason), and a בריאות/חיים row carrying an accumulation
    # is still insurance. Amounts only break the tie when the type is unknown.
    if savings_product_type(product_type):
        return "savings"
    if pure_risk_insurance(product_type):
        return "insurance"
    if accum > 0 and premium <= 0:
        return "savings"
    return "insurance"


# ── production rows ──────────────────────────────────────────────────────

def _row(columns: list[str], values: dict) -> list:
    """Emit a cell list in `columns` order; unmapped columns → ''."""
    return [values.get(col, "") for col in columns]


def record_to_insurance_product_row(rec: dict, agent_number=None, as_of=None) -> list:
    """Map a ClientRecord dict → a sheet-5 (מוצרי ביטוח) row.

    `יצרן` is canonicalized to the reference's full legal INSURANCE-entity name
    so portal short-names (הפניקס, מנורה, …) don't fragment the merged file.
    """
    vals = {
        "יצרן": canonical_company(rec.get("receiving_company"), "insurance"),
        "סוג מוצר": rec.get("product_type") or "",
        "מוצר": rec.get("product") or "",
        "מס' חשבון/פוליסה": rec.get("fund_policy_number") or "",
        "שם פרטי לקוח": rec.get("first_name") or "",
        "שם משפחה לקוח": rec.get("last_name") or "",
        "מספר ת.ז": _id_number_int(rec.get("id_number")),
        "סלולרי לקוח": _format_phone(rec.get("client_phone")),
        'דוא"ל לקוח': rec.get("client_email") or "",
        'סה"כ פרמיה': round(_f(rec.get("total_premium")), 2),
        "סטטוס מוצר": rec.get("product_status") or "",
        "תאריך הצטרפות למוצר": _d(rec.get("sign_date")),
        "מזהה מעסיק": rec.get("employer_id") or "",
        "שם מעסיק": rec.get("employer_name") or "",
        "מספר סוכן": agent_number or "",
        "נכון ליום": _d(as_of),
        # Source-portal account carried per-row (Harel stores it in lead_source).
        "מספר חשבון": rec.get("lead_source") or "",
    }
    return _row(COLUMNS_INSURANCE_PRODUCTS, vals)


def record_to_savings_row(rec: dict, agent_number=None, as_of=None) -> list:
    """Map a ClientRecord dict → a sheet-3 (מוצרי חיסכון) row.

    The `צבירה` column MUST carry accumulation — `_parse_production` keys off it.
    `יצרן` is canonicalized to the reference's full legal SAVINGS-entity name.
    """
    vals = {
        # entity_kind, NOT the sheet: ביטוח מנהלים / פוליסת חיסכון / מגוון live
        # on THIS sheet but are issued by the insurance entity (verified against
        # the reference portfolio). Passing "savings" here filed them under
        # 'הראל פנסיה וגמל בע"מ' instead of 'הראל חברה לביטוח בע"מ'.
        "יצרן": canonical_company(
            rec.get("receiving_company"),
            entity_kind(rec.get("product_type"), "savings"),
        ),
        "סוג מוצר": rec.get("product_type") or "",
        "מוצר": rec.get("product") or "",
        "מס' חשבון/פוליסה": rec.get("fund_policy_number") or "",
        "שם פרטי לקוח": rec.get("first_name") or "",
        "שם משפחה לקוח": rec.get("last_name") or "",
        "מספר ת.ז": _id_number_int(rec.get("id_number")),
        "סלולרי לקוח": _format_phone(rec.get("client_phone")),
        'דוא"ל לקוח': rec.get("client_email") or "",
        "סטטוס מוצר": rec.get("product_status") or "",
        "תאריך הצטרפות למוצר": _d(rec.get("sign_date")),
        "מזהה מעסיק": rec.get("employer_id") or "",
        "שם מעסיק": rec.get("employer_name") or "",
        "צבירה": round(_f(rec.get("accumulation")), 2),
        "מספר סוכן": agent_number or "",
        "נכון ליום": _d(as_of),
        # Source-portal account carried per-row (Harel stores it in lead_source).
        "מספר חשבון": rec.get("lead_source") or "",
    }
    return _row(COLUMNS_SAVINGS_PRODUCTS, vals)


def build_unified_workbook_bytes(records: list[dict], agent_number=None, as_of=None) -> bytes:
    """Build ONE 6-sheet production xlsx from all batch production records.

    Insurance/premium products → sheet 5; accumulation/gemel → sheet 3.
    Coverages (sheet 6) stay empty — they are a Migdal-only nicety not consumed
    downstream. `as_of` (a date) populates the `נכון ליום` valuation column on
    every row. Returns xlsx bytes ready for `ingest_file_bytes`.
    """
    insurance_rows: list[list] = []
    savings_rows: list[list] = []
    for rec in records:
        if classify_record(rec) == "savings":
            savings_rows.append(record_to_savings_row(rec, agent_number, as_of))
        else:
            insurance_rows.append(record_to_insurance_product_row(rec, agent_number, as_of))

    wb = build_workbook(
        insurance_rows,
        coverage_rows=[],
        agent_number=agent_number,
        savings_rows=savings_rows,
    )
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ── נפרעים rows ──────────────────────────────────────────────────────────

# Category tokens written into the קטגוריה column.
NIFRAIM_CATEGORY_GEMEL = "גמל"
NIFRAIM_CATEGORY_INSURANCE = "ביטוח"

_GEMEL_KW = ("גמל", "השתלמות", "תגמולים", "פנסיה", "חיסכון", "קופ")


def commission_category_token(rec: dict) -> str:
    """'גמל' / 'ביטוח' for the קטגוריה column, from product/fund_type keywords
    plus an accumulation fallback. Pension is treated as gemel-family here for
    file labelling; the comparison engine still excludes pension on its own.

    Delegates the known-type decision to the SAME `savings_product_type` /
    `pure_risk_insurance` helpers `classify_record` (production side) uses,
    checked in the same order (known type first, amount heuristic last) —
    a bare `_GEMEL_KW` keyword list previously drifted from `_ACCUM_TOKENS`
    (missing 'מנהלים') and disagreed with `pure_risk_insurance` entirely (no
    override for חיים/בריאות/סיעודי/משכנתא/ריסק/תאונ before the amount
    heuristic). That let a commission row and its matching production row for
    the SAME product land under different company legal entities (savings vs
    insurance) in the merged batch files, breaking production↔נפרעים pairing."""
    text = f"{rec.get('fund_type') or ''} {rec.get('product') or ''}"
    if any(kw in text for kw in _GEMEL_KW) or savings_product_type(text):
        return NIFRAIM_CATEGORY_GEMEL
    if pure_risk_insurance(text):
        return NIFRAIM_CATEGORY_INSURANCE
    # Gemel records carry a balance/accumulation but no premium.
    # Use balance as a fallback for parsers that store the AUM in 'balance'
    # rather than 'accumulation' (e.g. Hachshara, Altshuler, Phoenix gemel).
    accum = _f(rec.get("accumulation") or rec.get("balance"))
    if accum > 0 and _f(rec.get("total_premium")) <= 0:
        return NIFRAIM_CATEGORY_GEMEL
    return NIFRAIM_CATEGORY_INSURANCE


def _commission_nifraim_row(rec: dict, period_label: str = "") -> list:
    # Canonicalize יצרן to the same legal-entity names the production merge uses
    # so the production↔נפרעים compare pairs by company instead of fragmenting.
    kind = "savings" if commission_category_token(rec) == NIFRAIM_CATEGORY_GEMEL else "insurance"
    raw_company = rec.get("receiving_company") or rec.get("company_source")
    vals = {
        "מספר ת.ז": _id_number_int(rec.get("id_number")),
        "שם פרטי": rec.get("first_name") or "",
        "שם משפחה": rec.get("last_name") or "",
        "יצרן": canonical_company(raw_company, kind),
        "קטגוריה": commission_category_token(rec),
        "סוג מוצר": rec.get("fund_type") or "",
        "מוצר": rec.get("product") or "",
        "מס' פוליסה/חשבון": rec.get("fund_policy_number") or "",
        "פרמיה": round(_f(rec.get("total_premium")), 2),
        "צבירה": round(_f(rec.get("accumulation") or rec.get("balance")), 2),
        "עמלה ששולמה": round(_f(rec.get("commission_paid")), 2),
        'עמלה לפני מע"מ': round(_f(rec.get("commission_before_fee")), 2),
        "סכום בפועל": round(_f(rec.get("actual_amount")), 2),
        "שיעור עמלה שנתי": rec.get("annual_commission_pct") or "",
        "שיעור עמלה חודשי": rec.get("monthly_commission_pct") or "",
        "חודש": period_label or "",
        # Source-portal account carried per-row (Harel stores it in lead_source).
        "מספר חשבון": rec.get("lead_source") or "",
    }
    return _row(COLUMNS_UNIFIED_NIFRAIM, vals)


def build_unified_nifraim_bytes(comm_records: list[dict], period_label: str = "") -> bytes:
    """Build ONE unified נפרעים xlsx from all batch commission records.

    Single sheet in COLUMNS_UNIFIED_NIFRAIM order with an explicit קטגוריה
    column. Re-parses via the `unified_nifraim` format. Returns xlsx bytes.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "נפרעים מאוחד"
    ws.sheet_view.rightToLeft = True

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="305496", end_color="305496", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for i, col in enumerate(COLUMNS_UNIFIED_NIFRAIM, start=1):
        c = ws.cell(row=1, column=i, value=col)
        c.font = header_font
        c.fill = header_fill
        c.alignment = header_align
        ws.column_dimensions[get_column_letter(i)].width = max(14, min(40, len(col) + 6))

    for r_idx, rec in enumerate(comm_records, start=2):
        for c_idx, value in enumerate(_commission_nifraim_row(rec, period_label), start=1):
            ws.cell(row=r_idx, column=c_idx, value=value)
    ws.freeze_panes = "A2"

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
