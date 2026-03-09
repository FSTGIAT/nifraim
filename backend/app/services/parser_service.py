import io
import tempfile
from datetime import datetime

import msoffcrypto
import pandas as pd

from app.utils.hebrew_mappings import (
    AGENT_TRACKING_COLUMNS,
    COMPANY_REPORT_COLUMNS,
    PRODUCTION_FILE_COLUMNS,
    NIFRAIM_REPORT_COLUMNS,
    HACHSHARA_NIFRAIM_COLUMNS,
    MENORA_COLUMNS,
    ALTSHULER_COLUMNS,
    PHOENIX_INSURANCE_NIFRAIM_COLUMNS,
    HAREL_NIFRAIM_COLUMNS,
    AGENT_TRACKING_SIGNATURE,
    COMPANY_REPORT_SIGNATURE,
    PHOENIX_COMMISSION_SIGNATURE,
    PRODUCTION_FILE_SIGNATURE,
    NIFRAIM_REPORT_SIGNATURE,
    HACHSHARA_NIFRAIM_SIGNATURE,
    MENORA_SIGNATURE,
    ALTSHULER_SIGNATURE,
    PHOENIX_INSURANCE_NIFRAIM_SIGNATURE,
    HAREL_NIFRAIM_SIGNATURE,
    HEADER_SCAN_KEYWORDS,
    CANCELLATION_KEYWORDS,
)


def decrypt_xls(file_bytes: bytes, password: str) -> bytes:
    """Decrypt a password-protected xls/xlsx file."""
    infile = io.BytesIO(file_bytes)
    outfile = io.BytesIO()
    office_file = msoffcrypto.OfficeFile(infile)
    office_file.load_key(password=password)
    office_file.decrypt(outfile)
    outfile.seek(0)
    return outfile.read()


def detect_format(columns: list[str]) -> str:
    """Detect file format based on column headers."""
    col_set = set(columns)
    # Check new formats first (more specific signatures)
    if col_set & PRODUCTION_FILE_SIGNATURE:
        return "production"
    if col_set & NIFRAIM_REPORT_SIGNATURE:
        return "nifraim"
    if col_set & HACHSHARA_NIFRAIM_SIGNATURE:
        return "hachshara_nifraim"
    if col_set & MENORA_SIGNATURE:
        return "menora"
    if col_set & ALTSHULER_SIGNATURE:
        return "altshuler"
    if col_set & HAREL_NIFRAIM_SIGNATURE:
        return "harel_nifraim"
    if col_set & PHOENIX_INSURANCE_NIFRAIM_SIGNATURE:
        return "phoenix_insurance_nifraim"
    if col_set & PHOENIX_COMMISSION_SIGNATURE:
        return "company_report"
    if col_set & AGENT_TRACKING_SIGNATURE:
        return "agent_tracking"
    if col_set & COMPANY_REPORT_SIGNATURE:
        return "company_report"
    return "unknown"


def parse_numeric(value) -> float | None:
    """Parse a numeric value from potentially messy Excel data."""
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("₪", "").replace(" ", "")
    if not text or text == "-":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_date(value):
    """Parse a date value from Excel data. Returns a date object or None."""
    from datetime import date as date_type
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date_type):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value or value == "-":
            return None
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S", "%m/%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None


def check_cancellation(raw_text: str | None) -> bool:
    """Check if raw text contains cancellation keywords."""
    if not raw_text:
        return False
    text = str(raw_text).strip()
    return any(kw in text for kw in CANCELLATION_KEYWORDS)


def determine_status(record: dict) -> str:
    """Determine reconciliation status for a record."""
    # Check cancellation in raw actual text
    if check_cancellation(record.get("actual_raw")):
        return "cancelled"

    expected = record.get("expected_amount")
    actual = record.get("actual_amount")

    # Agent tracking format: compare expected vs actual
    if expected is not None and actual is not None:
        if abs(expected - actual) < 0.01:
            return "paid_match"
        return "paid_mismatch"

    if expected is not None and actual is None:
        return "unpaid"

    # Company report format: compare commission_paid vs commission_expected
    paid = record.get("commission_paid")
    expected_comm = record.get("commission_expected")
    if paid is not None and expected_comm is not None:
        if abs(paid - expected_comm) < 1.0:
            return "paid_match"
        return "paid_mismatch"

    return "no_data"


def parse_excel(file_bytes: bytes, filename: str, password: str | None = None) -> dict:
    """
    Parse an Excel file and return structured records.
    Returns: {"format": str, "company_source": str, "records": list[dict]}
    """
    raw = file_bytes
    if password:
        raw = decrypt_xls(file_bytes, password)

    ext = filename.rsplit(".", 1)[-1].lower()
    engine = "openpyxl" if ext == "xlsx" else "xlrd"
    buf = io.BytesIO(raw)

    # Try to detect named sheets for production files
    # Read ALL relevant sheets (מוצרי ביטוח + מוצרי חיסכון) and concatenate
    df = None
    if ext == "xlsx":
        xls = pd.ExcelFile(buf, engine=engine)
        # Strip whitespace from sheet names for matching
        sheet_name_map = {s.strip(): s for s in xls.sheet_names}
        production_sheets = ["מוצרי ביטוח", "מוצרי חיסכון", "מסלולי השקעה"]
        found_sheets = [sheet_name_map[s] for s in production_sheets if s in sheet_name_map]
        if found_sheets:
            dfs = []
            for sheet_name in found_sheets:
                sheet_df = pd.read_excel(xls, sheet_name=sheet_name)
                dfs.append(sheet_df)
            df = pd.concat(dfs, ignore_index=True)
        else:
            # Use openpyxl read_only mode to find actual row count first,
            # avoiding loading 1M+ empty rows into memory
            import openpyxl
            buf.seek(0)
            wb = openpyxl.load_workbook(buf, read_only=True, data_only=True)
            ws = wb.worksheets[0]
            # Count non-empty rows (stop after 50k consecutive empty rows)
            max_row = 0
            empty_streak = 0
            for i, row in enumerate(ws.iter_rows(min_row=1, values_only=True), 1):
                if any(v is not None for v in row):
                    max_row = i
                    empty_streak = 0
                else:
                    empty_streak += 1
                    if empty_streak > 100:
                        break
            wb.close()
            buf.seek(0)
            nrows = max(max_row + 1, 10)  # read at least 10 rows
            df = pd.read_excel(buf, engine=engine, sheet_name=0, nrows=nrows)
    else:
        df = pd.read_excel(buf, engine=engine)

    # Drop completely empty rows
    df = df.dropna(how="all").reset_index(drop=True)

    # Clean column names
    df.columns = [str(c).strip() for c in df.columns]

    # If all columns are "Unnamed: X", the real headers are in row 0
    if all(c.startswith("Unnamed") for c in df.columns):
        new_headers = [str(v).strip() if pd.notna(v) else f"col_{i}" for i, v in enumerate(df.iloc[0])]
        df.columns = new_headers
        df = df.iloc[1:].reset_index(drop=True)

    # If format still unknown, scan first 15 rows for buried headers
    # (some files have title/metadata rows before the actual column headers)
    file_format = detect_format(df.columns.tolist())
    if file_format == "unknown":
        for row_idx in range(min(15, len(df))):
            row_vals = [str(v).strip() if pd.notna(v) else "" for v in df.iloc[row_idx]]
            row_set = set(row_vals)
            if row_set & HEADER_SCAN_KEYWORDS:
                # Found the real header row — reassign columns and trim
                df.columns = [v if v else f"col_{i}" for i, v in enumerate(row_vals)]
                df = df.iloc[row_idx + 1:].reset_index(drop=True)
                file_format = detect_format(df.columns.tolist())
                break

    if file_format == "agent_tracking":
        return _parse_agent_tracking(df)
    elif file_format == "company_report":
        return _parse_company_report(df)
    elif file_format == "production":
        return _parse_production(df)
    elif file_format == "nifraim":
        return _parse_nifraim(df)
    elif file_format == "hachshara_nifraim":
        return _parse_hachshara_nifraim(df)
    elif file_format == "menora":
        return _parse_menora(df)
    elif file_format == "altshuler":
        return _parse_altshuler(df)
    elif file_format == "harel_nifraim":
        return _parse_harel_nifraim(df)
    elif file_format == "phoenix_insurance_nifraim":
        return _parse_phoenix_insurance_nifraim(df)
    else:
        # Try to parse as generic — map whatever columns we can
        return _parse_generic(df)


def _parse_agent_tracking(df: pd.DataFrame) -> dict:
    """Parse agent tracking format (Excellence xlsx)."""
    records = []
    company_source = None

    for _, row in df.iterrows():
        record = {}

        for heb_col, eng_field in AGENT_TRACKING_COLUMNS.items():
            if heb_col in df.columns:
                val = row.get(heb_col)
                if eng_field in ("expected_amount", "actual_amount", "management_fee"):
                    record[eng_field] = parse_numeric(val)
                elif eng_field in ("sign_date", "transfer_date", "rights_assignment_date"):
                    record[eng_field] = parse_date(val)
                else:
                    record[eng_field] = str(val).strip() if val is not None and not (isinstance(val, float) and pd.isna(val)) else None

        # Clean id_number — remove .0 artifacts
        if record.get("id_number"):
            record["id_number"] = str(record["id_number"]).replace(".0", "").strip()

        # Clean fund_policy_number — remove .0 artifacts
        if record.get("fund_policy_number"):
            record["fund_policy_number"] = str(record["fund_policy_number"]).replace(".0", "").strip()

        # Store raw values
        for heb_col in ("סכום העברה צפוי", "סכום העברה בפועל"):
            if heb_col in df.columns:
                raw_val = row.get(heb_col)
                field = "expected_raw" if "צפוי" in heb_col else "actual_raw"
                record[field] = str(raw_val) if raw_val is not None and not (isinstance(raw_val, float) and pd.isna(raw_val)) else None

        # Calculate difference
        if record.get("expected_amount") is not None and record.get("actual_amount") is not None:
            record["amount_difference"] = record["actual_amount"] - record["expected_amount"]

        record["reconciliation_status"] = determine_status(record)
        records.append(record)

    # Detect most common company
    from collections import Counter
    companies = Counter(
        r["receiving_company"] for r in records
        if r.get("receiving_company") and r["receiving_company"] not in ("nan", "None")
    )
    company_source = companies.most_common(1)[0][0] if companies else None

    return {
        "format": "agent_tracking",
        "company_source": company_source,
        "records": records,
    }


def _parse_company_report(df: pd.DataFrame) -> dict:
    """Parse company commission report format (Phoenix xls/xlsx)."""
    records = []

    # Detect company source from product names or column content
    company_source = None

    for _, row in df.iterrows():
        record = {}

        for heb_col, eng_field in COMPANY_REPORT_COLUMNS.items():
            if heb_col in df.columns:
                val = row.get(heb_col)
                if eng_field in ("balance", "commission_paid", "management_fee"):
                    record[eng_field] = parse_numeric(val)
                elif eng_field == "sign_date":
                    record[eng_field] = parse_date(val)
                else:
                    record[eng_field] = str(val).strip() if val is not None and not (isinstance(val, float) and pd.isna(val)) else None

        # Split full_name into first/last if present
        full_name = record.pop("full_name", None)
        if full_name and isinstance(full_name, str):
            parts = full_name.strip().split(maxsplit=1)
            record["first_name"] = parts[0] if parts else None
            record["last_name"] = parts[1] if len(parts) > 1 else None

        # Clean id_number — remove .0 artifacts
        if record.get("id_number"):
            id_str = str(record["id_number"])
            if id_str.endswith(".0"):
                id_str = id_str[:-2]
            record["id_number"] = id_str

        record["reconciliation_status"] = determine_status(record)

        # Skip rows without id_number (metadata/totals rows)
        if record.get("id_number") and record["id_number"] not in ("nan", "None", ""):
            records.append(record)

    # Detect company source from product names
    from collections import Counter
    product_names = [r.get("product", "") or "" for r in records]
    for name in product_names:
        if "פניקס" in name or "הפניקס" in name:
            company_source = "הפניקס"
            break
        if "מור" in name:
            company_source = "מור"
            break
        if "מיטב" in name:
            company_source = "מיטב"
            break

    if not company_source:
        # Fallback: check all product names
        all_text = " ".join(product_names)
        if "פניקס" in all_text:
            company_source = "הפניקס"
        else:
            company_source = "פניקס"  # Default for this format

    # Set receiving_company on all records
    for r in records:
        r["receiving_company"] = company_source

    return {
        "format": "company_report",
        "company_source": company_source,
        "records": records,
    }


def _parse_production(df: pd.DataFrame) -> dict:
    """Parse production file (קובץ פרודוקציה)."""
    records = []

    for _, row in df.iterrows():
        record = {}

        for heb_col, eng_field in PRODUCTION_FILE_COLUMNS.items():
            if heb_col in df.columns:
                val = row.get(heb_col)
                if eng_field in ("total_premium", "accumulation"):
                    record[eng_field] = parse_numeric(val)
                elif eng_field == "sign_date":
                    record[eng_field] = parse_date(val)
                else:
                    record[eng_field] = str(val).strip() if val is not None and not (isinstance(val, float) and pd.isna(val)) else None

        # Clean id_number
        if record.get("id_number"):
            id_str = str(record["id_number"])
            if id_str.endswith(".0"):
                id_str = id_str[:-2]
            record["id_number"] = id_str

        # Map product_status to is_active
        ps = record.get("product_status", "")
        record["is_active"] = "פעיל" if ps == "פעיל" else ("לא פעיל" if ps else None)

        record["reconciliation_status"] = "no_data"
        records.append(record)

    # Detect most common company
    from collections import Counter
    companies = Counter(
        r["receiving_company"] for r in records
        if r.get("receiving_company") and r["receiving_company"] not in ("nan", "None")
    )
    company_source = companies.most_common(1)[0][0] if companies else None

    return {
        "format": "production",
        "company_source": company_source,
        "records": records,
    }


def _parse_nifraim(df: pd.DataFrame) -> dict:
    """Parse commission report (דוח נפרעים)."""
    records = []

    for _, row in df.iterrows():
        record = {}

        for heb_col, eng_field in NIFRAIM_REPORT_COLUMNS.items():
            if heb_col in df.columns:
                val = row.get(heb_col)
                if eng_field in ("month_end_balance", "annual_commission_pct",
                                 "monthly_commission_pct", "commission_before_fee"):
                    record[eng_field] = parse_numeric(val)
                elif eng_field == "sign_date":
                    record[eng_field] = parse_date(val)
                else:
                    record[eng_field] = str(val).strip() if val is not None and not (isinstance(val, float) and pd.isna(val)) else None

        # Clean id_number
        if record.get("id_number"):
            id_str = str(record["id_number"])
            if id_str.endswith(".0"):
                id_str = id_str[:-2]
            record["id_number"] = id_str

        # Cross-compatibility: map to existing fields for unified display
        record["commission_paid"] = record.get("commission_before_fee")
        record["balance"] = record.get("month_end_balance")
        record["product"] = record.get("fund_type")

        record["receiving_company"] = "מור"
        record["reconciliation_status"] = "no_data"
        records.append(record)

    return {
        "format": "nifraim",
        "company_source": "מור",
        "records": records,
    }


def _parse_hachshara_nifraim(df: pd.DataFrame) -> dict:
    """Parse Hachshara commission report (נפרעים הכשרה)."""
    records = []

    for _, row in df.iterrows():
        record = {}

        for heb_col, eng_field in HACHSHARA_NIFRAIM_COLUMNS.items():
            if heb_col in df.columns:
                val = row.get(heb_col)
                if eng_field in ("balance", "management_fee", "management_fee_amount",
                                 "commission_paid", "commission_before_fee"):
                    record[eng_field] = parse_numeric(val)
                elif eng_field == "sign_date":
                    record[eng_field] = parse_date(val)
                else:
                    record[eng_field] = str(val).strip() if val is not None and not (isinstance(val, float) and pd.isna(val)) else None

        # Split full_name into first/last if present
        full_name = record.pop("full_name", None)
        if full_name and isinstance(full_name, str):
            parts = full_name.strip().split(maxsplit=1)
            record["first_name"] = parts[0] if parts else None
            record["last_name"] = parts[1] if len(parts) > 1 else None

        # Clean id_number — remove .0 artifacts
        if record.get("id_number"):
            id_str = str(record["id_number"])
            if id_str.endswith(".0"):
                id_str = id_str[:-2]
            record["id_number"] = id_str

        # Cross-compatibility: map to existing fields for unified display
        record["product"] = record.get("fund_type")
        record["month_end_balance"] = record.get("balance")

        record["receiving_company"] = "הכשרה"
        record["reconciliation_status"] = "no_data"

        # Skip rows without id_number (metadata/totals rows)
        if record.get("id_number") and record["id_number"] not in ("nan", "None", ""):
            records.append(record)

    return {
        "format": "hachshara_nifraim",
        "company_source": "הכשרה",
        "records": records,
    }


def _parse_menora(df: pd.DataFrame) -> dict:
    """Parse Menora commission reports (financial, insurance, health variants)."""
    records = []

    for _, row in df.iterrows():
        record = {}

        for heb_col, eng_field in MENORA_COLUMNS.items():
            if heb_col in df.columns:
                val = row.get(heb_col)
                if eng_field in ("balance", "management_fee", "management_fee_amount",
                                 "commission_paid", "commission_before_fee",
                                 "total_premium", "commission_expected"):
                    record[eng_field] = parse_numeric(val)
                elif eng_field == "sign_date":
                    record[eng_field] = parse_date(val)
                else:
                    record[eng_field] = str(val).strip() if val is not None and not (isinstance(val, float) and pd.isna(val)) else None

        # Split full_name into first/last if present
        full_name = record.pop("full_name", None)
        if full_name and isinstance(full_name, str):
            parts = full_name.strip().split(maxsplit=1)
            record["first_name"] = parts[0] if parts else None
            record["last_name"] = parts[1] if len(parts) > 1 else None

        # Clean id_number — remove .0 artifacts
        if record.get("id_number"):
            id_str = str(record["id_number"])
            if id_str.endswith(".0"):
                id_str = id_str[:-2]
            record["id_number"] = id_str

        # If fund_policy_number is "0" or empty, use fund_number (מספר תיק) instead
        fpn = record.get("fund_policy_number")
        if not fpn or fpn in ("0", "0.0", "nan", "None", ""):
            fn = record.get("fund_number")
            if fn and fn not in ("0", "0.0", "nan", "None", ""):
                record["fund_policy_number"] = fn

        # Cross-compatibility: map balance for unified display
        if record.get("balance"):
            record["month_end_balance"] = record["balance"]

        record["receiving_company"] = "מנורה"
        record["reconciliation_status"] = "no_data"

        # Skip rows without id_number (metadata/totals rows)
        if record.get("id_number") and record["id_number"] not in ("nan", "None", ""):
            records.append(record)

    return {
        "format": "menora",
        "company_source": "מנורה",
        "records": records,
    }


def _parse_altshuler(df: pd.DataFrame) -> dict:
    """Parse Altshuler Shaham commission report."""
    records = []

    for _, row in df.iterrows():
        record = {}

        for heb_col, eng_field in ALTSHULER_COLUMNS.items():
            if heb_col in df.columns:
                val = row.get(heb_col)
                if eng_field in ("balance", "commission_paid",
                                 "management_fee_amount", "management_fee"):
                    record[eng_field] = parse_numeric(val)
                elif eng_field == "sign_date":
                    record[eng_field] = parse_date(val)
                else:
                    record[eng_field] = str(val).strip() if val is not None and not (isinstance(val, float) and pd.isna(val)) else None

        # Split full_name into first/last if present
        full_name = record.pop("full_name", None)
        if full_name and isinstance(full_name, str):
            parts = full_name.strip().split(maxsplit=1)
            record["first_name"] = parts[0] if parts else None
            record["last_name"] = parts[1] if len(parts) > 1 else None

        # Clean id_number — remove .0 artifacts
        if record.get("id_number"):
            id_str = str(record["id_number"])
            if id_str.endswith(".0"):
                id_str = id_str[:-2]
            record["id_number"] = id_str

        # Clean agent_number — remove .0 artifacts
        if record.get("agent_number"):
            an = str(record["agent_number"])
            if an.endswith(".0"):
                an = an[:-2]
            record["agent_number"] = an

        # Cross-compatibility: map balance for unified display
        if record.get("balance"):
            record["month_end_balance"] = record["balance"]

        record["receiving_company"] = "אלטשולר"
        record["reconciliation_status"] = "no_data"

        # Skip rows without id_number (metadata/totals rows)
        if record.get("id_number") and record["id_number"] not in ("nan", "None", ""):
            records.append(record)

    return {
        "format": "altshuler",
        "company_source": "אלטשולר",
        "records": records,
    }


def _parse_harel_nifraim(df: pd.DataFrame) -> dict:
    """Parse Harel commission report (הראל דוח עמלות)."""
    records = []

    for _, row in df.iterrows():
        record = {}

        for heb_col, eng_field in HAREL_NIFRAIM_COLUMNS.items():
            if heb_col in df.columns:
                val = row.get(heb_col)
                if eng_field in ("total_premium", "commission_paid",
                                 "management_fee_amount", "commission_before_fee"):
                    record[eng_field] = parse_numeric(val)
                elif eng_field == "sign_date":
                    record[eng_field] = parse_date(val)
                else:
                    record[eng_field] = str(val).strip() if val is not None and not (isinstance(val, float) and pd.isna(val)) else None

        # Split full_name into first/last if present
        full_name = record.pop("full_name", None)
        if full_name and isinstance(full_name, str):
            parts = full_name.strip().split(maxsplit=1)
            record["first_name"] = parts[0] if parts else None
            record["last_name"] = parts[1] if len(parts) > 1 else None

        # Clean id_number — remove .0 artifacts
        if record.get("id_number"):
            id_str = str(record["id_number"])
            if id_str.endswith(".0"):
                id_str = id_str[:-2]
            record["id_number"] = id_str

        # Clean fund_policy_number — remove .0 artifacts
        if record.get("fund_policy_number"):
            fpn = str(record["fund_policy_number"])
            if fpn.endswith(".0"):
                fpn = fpn[:-2]
            record["fund_policy_number"] = fpn

        # Clean agent_number — remove .0 artifacts
        if record.get("agent_number"):
            an = str(record["agent_number"])
            if an.endswith(".0"):
                an = an[:-2]
            record["agent_number"] = an

        # Map fund_type (ענף) to product if product is empty
        if not record.get("product") or record["product"] in ("nan", "None", ""):
            record["product"] = record.get("fund_type")

        record["receiving_company"] = "הראל"
        record["reconciliation_status"] = "no_data"

        # Skip rows without id_number (metadata/totals rows)
        if record.get("id_number") and record["id_number"] not in ("nan", "None", ""):
            records.append(record)

    return {
        "format": "harel_nifraim",
        "company_source": "הראל",
        "records": records,
    }


def _parse_phoenix_insurance_nifraim(df: pd.DataFrame) -> dict:
    """Parse Phoenix Insurance commission report (נפרעים הפניקס ביטוח)."""
    records = []

    for _, row in df.iterrows():
        record = {}

        for heb_col, eng_field in PHOENIX_INSURANCE_NIFRAIM_COLUMNS.items():
            if heb_col in df.columns:
                val = row.get(heb_col)
                if eng_field in ("balance", "total_premium", "commission_paid"):
                    record[eng_field] = parse_numeric(val)
                elif eng_field == "sign_date":
                    record[eng_field] = parse_date(val)
                else:
                    record[eng_field] = str(val).strip() if val is not None and not (isinstance(val, float) and pd.isna(val)) else None

        # Split full_name into first/last if present
        full_name = record.pop("full_name", None)
        if full_name and isinstance(full_name, str):
            parts = full_name.strip().split(maxsplit=1)
            record["first_name"] = parts[0] if parts else None
            record["last_name"] = parts[1] if len(parts) > 1 else None

        # Clean id_number — remove .0 artifacts
        if record.get("id_number"):
            id_str = str(record["id_number"])
            if id_str.endswith(".0"):
                id_str = id_str[:-2]
            record["id_number"] = id_str

        # Clean fund_policy_number — remove .0 artifacts
        if record.get("fund_policy_number"):
            fpn = str(record["fund_policy_number"])
            if fpn.endswith(".0"):
                fpn = fpn[:-2]
            record["fund_policy_number"] = fpn

        # Clean agent_number — remove .0 artifacts
        if record.get("agent_number"):
            an = str(record["agent_number"])
            if an.endswith(".0"):
                an = an[:-2]
            record["agent_number"] = an

        # Cross-compatibility: map balance for unified display
        if record.get("balance"):
            record["month_end_balance"] = record["balance"]

        # Map fund_type (ענף) to product if product is empty
        if not record.get("product") or record["product"] in ("nan", "None", ""):
            record["product"] = record.get("fund_type")

        record["receiving_company"] = "הפניקס"
        record["reconciliation_status"] = "no_data"

        # Skip rows without id_number (footer totals/disclaimers)
        if record.get("id_number") and record["id_number"] not in ("nan", "None", ""):
            records.append(record)

    return {
        "format": "phoenix_insurance_nifraim",
        "company_source": "הפניקס",
        "records": records,
    }


def _parse_generic(df: pd.DataFrame) -> dict:
    """Fallback parser — try to map whatever columns match."""
    all_mappings = {**AGENT_TRACKING_COLUMNS, **COMPANY_REPORT_COLUMNS}
    records = []

    for _, row in df.iterrows():
        record = {}
        for heb_col, eng_field in all_mappings.items():
            if heb_col in df.columns:
                val = row.get(heb_col)
                record[eng_field] = str(val).strip() if val is not None and not (isinstance(val, float) and pd.isna(val)) else None
        record["reconciliation_status"] = "no_data"
        records.append(record)

    return {
        "format": "unknown",
        "company_source": None,
        "records": records,
    }
