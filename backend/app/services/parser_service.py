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
    CLAL_LIFE_NIFRAIM_COLUMNS,
    CLAL_HEALTH_NIFRAIM_COLUMNS,
    MIGDAL_NIFRAIM_COLUMNS,
    AYALON_NIFRAIM_COLUMNS,
    VOLUME_REPORT_COLUMNS,
    VOLUME_RATES_COLUMNS,
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
    CLAL_LIFE_NIFRAIM_SIGNATURE,
    CLAL_HEALTH_NIFRAIM_SIGNATURE,
    MIGDAL_NIFRAIM_SIGNATURE,
    AYALON_NIFRAIM_SIGNATURE,
    VOLUME_REPORT_SIGNATURE,
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
    if col_set & VOLUME_REPORT_SIGNATURE:
        return "volume_report"
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
    if col_set & CLAL_LIFE_NIFRAIM_SIGNATURE:
        return "clal_life_nifraim"
    if col_set & CLAL_HEALTH_NIFRAIM_SIGNATURE:
        return "clal_health_nifraim"
    if col_set & AYALON_NIFRAIM_SIGNATURE:
        return "ayalon_nifraim"
    if col_set & MIGDAL_NIFRAIM_SIGNATURE:
        return "migdal_nifraim"
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
    else:
        try:
            if msoffcrypto.OfficeFile(io.BytesIO(file_bytes)).is_encrypted():
                raise ValueError("הקובץ מוצפן — סמן את האפשרות 'קובץ מוצפן' והזן סיסמה")
        except ValueError:
            raise
        except Exception:
            pass

    ext = filename.rsplit(".", 1)[-1].lower()
    engine = "openpyxl" if ext == "xlsx" else "xlrd"
    buf = io.BytesIO(raw)

    # Try to detect named sheets for production files
    # Read ALL relevant sheets (מוצרי ביטוח + מוצרי חיסכון) and concatenate
    # מסלולי השקעה is read separately and merged by (id_number, fund_policy_number)
    df = None
    track_lookup = {}  # (id_number, fund_policy_number) → track name
    if ext == "xlsx":
        xls = pd.ExcelFile(buf, engine=engine)
        # Strip whitespace from sheet names for matching
        sheet_name_map = {s.strip(): s for s in xls.sheet_names}
        production_sheets = ["מוצרי ביטוח", "מוצרי חיסכון"]
        found_sheets = [sheet_name_map[s] for s in production_sheets if s in sheet_name_map]
        if found_sheets:
            dfs = []
            for sheet_name in found_sheets:
                sheet_df = pd.read_excel(xls, sheet_name=sheet_name)
                dfs.append(sheet_df)
            df = pd.concat(dfs, ignore_index=True)
            # Build track lookup from מסלולי השקעה sheet
            track_sheet_key = "מסלולי השקעה"
            if track_sheet_key in sheet_name_map:
                track_df = pd.read_excel(xls, sheet_name=sheet_name_map[track_sheet_key])
                track_df.columns = [str(c).strip() for c in track_df.columns]
                id_col = next((c for c in track_df.columns if c in ("מספר ת.ז", "ת.ז", "ת.ז.")), None)
                acct_col = next((c for c in track_df.columns if c in ("מס' חשבון/פוליסה", "מספר חשבון/פוליסה")), None)
                track_col = next((c for c in track_df.columns if c in ("שם מסלול",)), None)
                if id_col and acct_col and track_col:
                    for _, trow in track_df.iterrows():
                        tid = trow.get(id_col)
                        tacct = trow.get(acct_col)
                        tname = trow.get(track_col)
                        if pd.notna(tid) and pd.notna(tacct) and pd.notna(tname):
                            tid_str = str(tid).strip()
                            if tid_str.endswith(".0"):
                                tid_str = tid_str[:-2]
                            tacct_str = str(tacct).strip()
                            if tacct_str.endswith(".0"):
                                tacct_str = tacct_str[:-2]
                            track_lookup[(tid_str, tacct_str)] = str(tname).strip()
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

    if file_format == "volume_report":
        return _parse_volume_report(df, file_bytes=raw, engine=engine)

    # If sheet 0 didn't match volume_report, check other sheets (multi-sheet volume files)
    if file_format == "unknown" and ext == "xlsx":
        try:
            buf.seek(0)
            xls = pd.ExcelFile(buf, engine=engine)
            if len(xls.sheet_names) > 1:
                for sheet_idx, sname in enumerate(xls.sheet_names[1:], 1):
                    try:
                        sdf = pd.read_excel(xls, sheet_name=sname)
                        sdf = sdf.dropna(how="all").reset_index(drop=True)
                        sdf.columns = [str(c).strip() for c in sdf.columns]
                        fmt = detect_format(sdf.columns.tolist())
                        if fmt == "unknown":
                            for ri in range(min(10, len(sdf))):
                                rv = [str(v).strip() if pd.notna(v) else "" for v in sdf.iloc[ri]]
                                rs = set(rv)
                                if rs & HEADER_SCAN_KEYWORDS:
                                    sdf.columns = [v if v else f"col_{i}" for i, v in enumerate(rv)]
                                    sdf = sdf.iloc[ri + 1:].reset_index(drop=True)
                                    fmt = detect_format(sdf.columns.tolist())
                                    break
                        if fmt == "volume_report":
                            return _parse_volume_report(sdf, file_bytes=raw, engine=engine,
                                                        standard_sheet_idx=sheet_idx)
                    except Exception:
                        continue
        except Exception:
            pass

    if file_format == "agent_tracking":
        return _parse_agent_tracking(df)
    elif file_format == "company_report":
        return _parse_company_report(df)
    elif file_format == "production":
        return _parse_production(df, track_lookup=track_lookup)
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
    elif file_format == "clal_life_nifraim":
        return _parse_clal_life_nifraim(df)
    elif file_format == "clal_health_nifraim":
        return _parse_clal_health_nifraim(df)
    elif file_format == "migdal_nifraim":
        return _parse_migdal_nifraim(df)
    elif file_format == "ayalon_nifraim":
        return _parse_ayalon_nifraim(df)
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


def _parse_production(df: pd.DataFrame, track_lookup: dict | None = None) -> dict:
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

        # Merge track from מסלולי השקעה lookup
        if track_lookup and record.get("id_number") and record.get("fund_policy_number"):
            fpn = str(record["fund_policy_number"]).strip()
            if fpn.endswith(".0"):
                fpn = fpn[:-2]
            track_val = track_lookup.get((record["id_number"], fpn))
            if track_val:
                record["track"] = track_val

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


def _parse_clal_life_nifraim(df: pd.DataFrame) -> dict:
    """Parse Clal Life commission report (כלל חיים)."""
    records = []

    for _, row in df.iterrows():
        record = {}

        for heb_col, eng_field in CLAL_LIFE_NIFRAIM_COLUMNS.items():
            if heb_col in df.columns:
                val = row.get(heb_col)
                if eng_field in ("total_premium", "commission_paid",
                                 "commission_before_fee", "management_fee_amount"):
                    record[eng_field] = parse_numeric(val)
                elif eng_field in ("sign_date", "processing_date"):
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

        record["receiving_company"] = "כלל"
        record["reconciliation_status"] = "no_data"

        # Skip rows without id_number (metadata/totals rows)
        if record.get("id_number") and record["id_number"] not in ("nan", "None", ""):
            records.append(record)

    return {
        "format": "clal_life_nifraim",
        "company_source": "כלל",
        "records": records,
    }


def _parse_clal_health_nifraim(df: pd.DataFrame) -> dict:
    """Parse Clal Health commission report (כלל בריאות)."""
    records = []

    for _, row in df.iterrows():
        record = {}

        for heb_col, eng_field in CLAL_HEALTH_NIFRAIM_COLUMNS.items():
            if heb_col in df.columns:
                val = row.get(heb_col)
                if eng_field in ("total_premium", "commission_paid",
                                 "commission_before_fee", "management_fee_amount"):
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

        record["receiving_company"] = "כלל"
        record["reconciliation_status"] = "no_data"

        # Skip rows without id_number (metadata/totals rows)
        if record.get("id_number") and record["id_number"] not in ("nan", "None", ""):
            records.append(record)

    return {
        "format": "clal_health_nifraim",
        "company_source": "כלל",
        "records": records,
    }


def _parse_migdal_nifraim(df: pd.DataFrame) -> dict:
    """Parse Migdal commission report (מגדל)."""
    records = []

    for _, row in df.iterrows():
        record = {}

        for heb_col, eng_field in MIGDAL_NIFRAIM_COLUMNS.items():
            if heb_col in df.columns:
                val = row.get(heb_col)
                if eng_field in ("total_premium", "commission_paid",
                                 "management_fee_amount", "commission_before_fee"):
                    record[eng_field] = parse_numeric(val)
                elif eng_field in ("sign_date", "processing_date"):
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

        record["receiving_company"] = "מגדל"
        record["reconciliation_status"] = "no_data"

        # Skip rows without id_number (metadata/totals rows)
        if record.get("id_number") and record["id_number"] not in ("nan", "None", ""):
            records.append(record)

    return {
        "format": "migdal_nifraim",
        "company_source": "מגדל",
        "records": records,
    }


def _parse_ayalon_nifraim(df: pd.DataFrame) -> dict:
    """Parse Ayalon commission report (איילון)."""
    records = []

    for _, row in df.iterrows():
        record = {}

        for heb_col, eng_field in AYALON_NIFRAIM_COLUMNS.items():
            if heb_col in df.columns:
                val = row.get(heb_col)
                if eng_field in ("total_premium", "commission_paid",
                                 "management_fee_amount", "balance"):
                    record[eng_field] = parse_numeric(val)
                elif eng_field in ("sign_date", "processing_date"):
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

        record["receiving_company"] = "איילון"
        record["reconciliation_status"] = "no_data"

        # Skip rows without id_number (metadata/totals rows)
        if record.get("id_number") and record["id_number"] not in ("nan", "None", ""):
            records.append(record)

    return {
        "format": "ayalon_nifraim",
        "company_source": "איילון",
        "records": records,
    }


def _parse_volume_report(df: pd.DataFrame, file_bytes: bytes = None, engine: str = "openpyxl",
                         standard_sheet_idx: int = 0) -> dict:
    """Parse volume report (דוח היקפים).

    The standard sheet has the אקסלנס format with רמת גורם.
    Additional sheets may contain other companies (הראל, מור, מנורה, etc.)
    with different column layouts — parsed separately.
    Returns in-memory data (NOT inserted into client_records).
    """
    # Parse the standard sheet
    clients, agency_rates, summary_info = _parse_volume_sheet_standard(df)

    # Parse all other sheets from the same file
    if file_bytes:
        try:
            buf = io.BytesIO(file_bytes)
            xls = pd.ExcelFile(buf, engine=engine)
            for idx, sheet_name in enumerate(xls.sheet_names):
                if idx == standard_sheet_idx:
                    continue  # skip the standard-format sheet
                try:
                    sheet_df = pd.read_excel(xls, sheet_name=sheet_name)
                    sheet_df = sheet_df.dropna(how="all").reset_index(drop=True)
                    extra_clients = _parse_volume_sheet_other(sheet_df, sheet_name)
                    clients.extend(extra_clients)
                except Exception:
                    pass  # skip unparseable sheets
        except Exception:
            pass

    total_deposits = sum(c.get("deposit_amount") or 0 for c in clients)
    total_production_after_cancel = sum(c.get("production_after_cancel") or 0 for c in clients)

    return {
        "format": "volume_report",
        "company_source": None,
        "records": [],  # Not inserted into DB
        "volume_data": {
            "summary": {
                "agent_name": summary_info.get("agent_name"),
                "total_deposits": round(total_deposits, 2),
                "total_production_after_cancel": round(total_production_after_cancel, 2),
                "client_count": len(clients),
                "unique_clients": len(set(c.get("id_number", "") for c in clients)),
            },
            "clients": clients,
            "agency_rates": agency_rates,
        },
    }


def _parse_volume_sheet_standard(df: pd.DataFrame) -> tuple:
    """Parse the standard אקסלנס-format volume sheet (with רמת גורם column)."""
    summary_info = {}

    # Check if headers are still buried (not yet reassigned by parse_excel)
    if "רמת גורם" not in df.columns and "תפוקה לאחר ביטולי שנה א" not in df.columns:
        for row_idx in range(min(10, len(df))):
            row_vals = [str(v).strip() if pd.notna(v) else "" for v in df.iloc[row_idx]]
            if "רמת גורם" in row_vals or "תפוקה לאחר ביטולי שנה א" in row_vals:
                for sum_idx in range(row_idx):
                    sum_vals = [str(v).strip() if pd.notna(v) else "" for v in df.iloc[sum_idx]]
                    for v in sum_vals:
                        if v and v not in ("nan", "None", "") and len(v) > 2:
                            if any('\u0590' <= ch <= '\u05FF' for ch in v):
                                summary_info["agent_name"] = v
                                break
                    if summary_info.get("agent_name"):
                        break
                df.columns = [v if v else f"col_{i}" for i, v in enumerate(row_vals)]
                df = df.iloc[row_idx + 1:].reset_index(drop=True)
                break

    all_rows = []
    agency_rates = {}

    for _, row in df.iterrows():
        record = {}

        for heb_col, eng_field in VOLUME_REPORT_COLUMNS.items():
            if heb_col in df.columns:
                val = row.get(heb_col)
                if eng_field in ("deposit_amount", "production_after_cancel",
                                 "rate_per_million", "final_entitlement"):
                    record[eng_field] = parse_numeric(val)
                elif eng_field == "transfer_date":
                    record[eng_field] = parse_date(val)
                else:
                    record[eng_field] = str(val).strip() if val is not None and not (isinstance(val, float) and pd.isna(val)) else None

        # Clean id_number
        if record.get("id_number"):
            id_str = str(record["id_number"])
            if id_str.endswith(".0"):
                id_str = id_str[:-2]
            id_str = id_str.lstrip('0') or '0'
            record["id_number"] = id_str

        # Clean fund_policy_number
        if record.get("fund_policy_number"):
            fpn = str(record["fund_policy_number"])
            if fpn.endswith(".0"):
                fpn = fpn[:-2]
            record["fund_policy_number"] = fpn

        factor_level = record.get("factor_level", "")

        # Extract agency-level rate_per_million
        if factor_level and "סוכנות" in factor_level:
            company = record.get("product_type") or record.get("product") or ""
            rpm = record.get("rate_per_million")
            if company and rpm:
                agency_rates[company] = rpm

        # Keep agent-level rows for client data.
        # Prefer "סוכן" (agent) rows; if none exist, fall back to "סוכנות" (agency) rows.
        # Note: ן (nun sofit) ≠ נ (nun), so "סוכן" is NOT a substring of "סוכנות".
        is_agent = factor_level and "סוכן" in factor_level
        is_agency = factor_level and "סוכנות" in factor_level
        if is_agent or is_agency:
            full_name = record.pop("full_name", None)
            if full_name and isinstance(full_name, str) and full_name not in ("nan", "None"):
                parts = full_name.strip().split(maxsplit=1)
                record["first_name"] = parts[0] if parts else None
                record["last_name"] = parts[1] if len(parts) > 1 else None
                record["full_name"] = full_name.strip()
            else:
                record["full_name"] = None

            if record.get("id_number") and record["id_number"] not in ("nan", "None", ""):
                record["_is_agent"] = is_agent
                all_rows.append(record)

    # If we have agent-level rows, use only those. Otherwise use all (agency) rows.
    has_agent_rows = any(r.get("_is_agent") for r in all_rows)
    if has_agent_rows:
        clients = [r for r in all_rows if r.get("_is_agent")]
    else:
        clients = all_rows
    # Clean up internal flag
    for c in clients:
        c.pop("_is_agent", None)

    # Fallback: extract agent name from data
    if not summary_info.get("agent_name") and clients:
        agent_name_col = "שם סוכן מוכר"
        if agent_name_col in df.columns and len(df) > 0:
            for _, row in df.iterrows():
                fl = str(row.get("רמת גורם", "")).strip()
                if "סוכן" in fl and "סוכנות" not in fl:
                    val = row.get(agent_name_col)
                    if pd.notna(val) and str(val).strip():
                        summary_info["agent_name"] = str(val).strip()
                        break

    return clients, agency_rates, summary_info


def _parse_volume_sheet_other(df: pd.DataFrame, sheet_name: str) -> list:
    """Parse a non-standard volume sheet (הראל, מור, מנורה, ילין, etc.).

    Each company has different column names. We detect and map them generically.
    The sheet_name is used as the company/product_type.
    """
    # Find header row: scan first 10 rows for a row with ID-like column
    id_col_names = {"ת.ז עמית", "ת.ז. עמית", "תז עמית", "זהות לקוח", "מס.זהות",
                     "מספר זהות", "ת.ז לקוח", "תז לקוח", "ת.ז מבוטח"}
    name_col_names = {"שם עמית", "שם לקוח", "שם מבוטח"}
    deposit_col_names = {"סכום פעולה ב-₪", "סכום תנועת הפקדה", "סכום הפקדה",
                         "סכום העברה בפועל", "פרמיה לתגמול חודשי", "פרמיה לא לתגמול חודשי",
                         "נטו", "סהכ תפוקה לתגמול", "הפקדה חד פעמית",
                         "פרמיה נמדדת", "סהכ פרמיה לתגמול",
                         "תנועות העברה פנימה לפי תאריך הצת",
                         "תנועות העברה פנימה לפי תאריך הצטרפות"}

    header_idx = None
    for i in range(min(10, len(df))):
        row_vals = set(str(v).strip() if pd.notna(v) else "" for v in df.iloc[i])
        if row_vals & id_col_names:
            header_idx = i
            break

    if header_idx is None:
        return []

    # Reassign columns
    row_vals = [str(v).strip() if pd.notna(v) else f"col_{j}" for j, v in enumerate(df.iloc[header_idx])]
    df.columns = row_vals
    df = df.iloc[header_idx + 1:].reset_index(drop=True)

    # Find the actual column names in this sheet
    col_set = set(df.columns)
    id_col = next((c for c in id_col_names if c in col_set), None)
    name_col = next((c for c in name_col_names if c in col_set), None)
    deposit_col = next((c for c in deposit_col_names if c in col_set), None)
    product_col = next((c for c in ("סוג מוצר", "סוג קופה", "שם מוצר", "סוג קופה מעבירה") if c in col_set), None)

    if not id_col:
        return []

    clients = []
    for _, row in df.iterrows():
        idn = row.get(id_col)
        if pd.isna(idn):
            continue
        id_str = str(idn).strip()
        if id_str.endswith(".0"):
            id_str = id_str[:-2]
        id_str = id_str.lstrip('0') or '0'
        if not id_str or id_str in ("nan", "None", ""):
            continue

        name = str(row.get(name_col, "")).strip() if name_col else None
        if name in ("nan", "None"):
            name = None

        deposit = parse_numeric(row.get(deposit_col)) if deposit_col else 0

        product = str(row.get(product_col, "")).strip() if product_col else None
        if product in ("nan", "None", ""):
            product = None

        record = {
            "id_number": id_str,
            "full_name": name,
            "first_name": name.split()[0] if name and " " in name else name,
            "last_name": name.split(maxsplit=1)[1] if name and " " in name else None,
            "product_type": sheet_name,  # Use sheet name as company
            "product": product,
            "deposit_amount": deposit,
            "production_after_cancel": deposit,  # best estimate: deposit ≈ production
        }
        clients.append(record)

    return clients


def parse_volume_rates(file_bytes: bytes, filename: str, password: str | None = None) -> list[dict]:
    """Parse volume commission rates from Excel file."""
    raw = file_bytes
    if password:
        raw = decrypt_xls(file_bytes, password)

    ext = filename.rsplit(".", 1)[-1].lower()
    engine = "openpyxl" if ext == "xlsx" else "xlrd"
    buf = io.BytesIO(raw)
    df = pd.read_excel(buf, engine=engine)

    df = df.dropna(how="all").reset_index(drop=True)
    df.columns = [str(c).strip() for c in df.columns]

    # If all columns are "Unnamed", reassign from row 0
    if all(c.startswith("Unnamed") for c in df.columns):
        new_headers = [str(v).strip() if pd.notna(v) else f"col_{i}" for i, v in enumerate(df.iloc[0])]
        df.columns = new_headers
        df = df.iloc[1:].reset_index(drop=True)

    rates = []
    for _, row in df.iterrows():
        record = {}
        for heb_col, eng_field in VOLUME_RATES_COLUMNS.items():
            if heb_col in df.columns:
                val = row.get(heb_col)
                if eng_field in ("nifraim_rate", "volume_rate_per_million",
                                 "pension_accumulation", "changed_percent",
                                 "conversion_to_annuity"):
                    num = parse_numeric(val)
                    # changed_percent in Excel is already a whole percentage (e.g. 13 = 13%)
                    # Convert to decimal fraction for storage (13 → 0.13)
                    if eng_field == "changed_percent" and num is not None and num > 1:
                        num = num / 100
                    record[eng_field] = num
                else:
                    record[eng_field] = str(val).strip() if val is not None and not (isinstance(val, float) and pd.isna(val)) else None

        # Skip rows without company_name
        if record.get("company_name") and record["company_name"] not in ("nan", "None", ""):
            rates.append(record)

    return rates


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
