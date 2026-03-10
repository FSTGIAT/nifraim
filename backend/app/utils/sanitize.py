from datetime import date, datetime

import pandas as pd

# Max lengths matching the DB schema
MAX_LENGTHS = {
    "id_number": 20, "first_name": 100, "last_name": 100, "recruitment_type": 50,
    "product": 100, "fund_policy_number": 50, "employment_status": 20, "is_active": 20,
    "receiving_company": 100, "track": 100, "transferring_fund": 100, "transferring_body": 100,
    "lead_source": 100, "agent_number": 20, "reconciliation_status": 20,
    "product_type": 100, "product_status": 20, "fund_type": 100, "fund_number": 50,
    "processing_date": 20,
    "client_phone": 30,
    "client_email": 100,
    "employer_name": 100,
    "employer_id": 20,
}

DATE_FIELDS = {"sign_date", "transfer_date", "rights_assignment_date"}


def sanitize_record(rec: dict) -> dict:
    """Truncate strings and convert dates for DB insertion."""
    out = {}
    for k, v in rec.items():
        if v is None:
            out[k] = None
            continue
        # Handle pandas Timestamps
        if k in DATE_FIELDS:
            if pd.isna(v):
                out[k] = None
            elif isinstance(v, pd.Timestamp):
                out[k] = v.date()
            elif isinstance(v, datetime):
                out[k] = v.date()
            elif isinstance(v, date):
                out[k] = v
            else:
                out[k] = None
            continue
        # Convert date objects in string fields (e.g. processing_date is VARCHAR)
        if k in MAX_LENGTHS and isinstance(v, (date, datetime)):
            out[k] = v.strftime("%Y-%m-%d") if not isinstance(v, pd.Timestamp) else str(v.date())
            continue
        # Truncate strings
        if k in MAX_LENGTHS and isinstance(v, str):
            out[k] = v[:MAX_LENGTHS[k]]
        else:
            out[k] = v
    return out
