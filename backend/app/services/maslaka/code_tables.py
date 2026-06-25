"""Clearinghouse code → human-readable label lookups.

Two tables today (more come with later interfaces):
    - PROVIDER_CODE_TO_COMPANY: insurer numeric code → Hebrew `receiving_company`
      label. CRITICAL: values must match existing `ClientRecord.receiving_company`
      strings used elsewhere in the app (`migdal`, `הראל` etc.) — otherwise the
      company-breakdown UI would split a single insurer across two labels.
    - PRODUCT_TYPE_CODE_TO_LABEL: cross-insurer product-type code → Hebrew label.

Both are stubs today. When the Swiftness XSDs land, fill them in from the
clearinghouse's code list (usually appendix tables in the interface PDFs).
"""

from __future__ import annotations


# TODO(XSD): replace these placeholder codes with the real Swiftness "טבלת יצרנים"
# values once we have the schemas. Codes below are PLACEHOLDERS — they match
# the test fixture in backend/tests/fixtures/maslaka/holdings_v009.xml so
# iteration-1 verification produces clean Hebrew company labels. Labels must
# match `ClientRecord.receiving_company` values used elsewhere in the app, so
# the company-breakdown UI joins cleanly when holdings + production overlap.
PROVIDER_CODE_TO_COMPANY: dict[str, str] = {
    "521000123": "מגדל חברה לביטוח בע\"מ",       # placeholder — confirm against XSD
    "520000456": "כלל חברה לביטוח בע\"מ",        # placeholder
    "520000789": "מנורה מבטחים ביטוח בע\"מ",     # placeholder
    "520012345": "הפניקס חברה לביטוח בע\"מ",     # placeholder
    "520067890": "הראל חברה לביטוח בע\"מ",       # placeholder
}


def label_for_provider(code: str | None) -> str | None:
    """Map a clearinghouse provider code to its Hebrew company name.

    Returns None if the code isn't mapped — callers should either fall back
    to the raw code or use 'אחר'. We never invent a label."""
    if not code:
        return None
    return PROVIDER_CODE_TO_COMPANY.get(str(code).strip())


# TODO(XSD): replace these placeholders with the real Swiftness "טבלת סוגי מוצר"
# values once we have the schemas.
PRODUCT_TYPE_CODE_TO_LABEL: dict[str, str] = {
    "01": "ביטוח חיים",            # placeholder
    "02": "ביטוח בריאות",          # placeholder
    "03": "ביטוח חיים משכנתא",     # placeholder
    "10": "קרן השתלמות",          # placeholder
    "20": "קופת גמל",              # placeholder
    "30": "פנסיה",                # placeholder
}


def label_for_product_type(code: str | None) -> str | None:
    if not code:
        return None
    return PRODUCT_TYPE_CODE_TO_LABEL.get(str(code).strip())
