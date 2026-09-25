"""Clearinghouse code → human-readable label lookups.

Two tables today (more come with later interfaces):
    - PROVIDER_CODE_TO_COMPANY: insurer numeric code → Hebrew `receiving_company`
      label. CRITICAL: values must match existing `ClientRecord.receiving_company`
      strings used elsewhere in the app (`migdal`, `הראל` etc.) — otherwise the
      company-breakdown UI would split a single insurer across two labels.
    - PRODUCT_TYPE_CODE_TO_LABEL: cross-insurer product-type code → Hebrew label.

PROVIDER_CODE_TO_COMPANY is real and sourced (see below). The product-type
table is still a stub.
"""

from __future__ import annotations


# ─── יצרנים — the institutional bodies, keyed by their ח.פ ────────────────
# On the wire a יצרן IS its ח.פ: `KOD-MEZAHE-YATZRAN` is "מספר ח.פ או ח.צ (עד 9
# ספרות)" per the Events v007 field spec. There is no separate Swiftness code
# table to vendor — the ח.פ is the code.
#
# SOURCE — every value below was read, not remembered, from the Capital Market
# Authority's own datasets on data.gov.il (fetched 2026-09-25, periods ≥ 2025-01):
#   גמל-נט   a30dcbea-a1d2-482c-ae29-8f781f5025fb  MANAGING_CORPORATION_LEGAL_ID
#   פנסיה-נט 6d47d6b5-cb08-488b-b333-f1e717b1e1bd  MANAGING_CORPORATION_LEGAL_ID
#   ביטוח-נט c6c62cc7-fe02-4b18-8f3e-813abfbb4647  PARENT_COMPANY_LEGAL_ID
# Cross-checked against the Swiftness vendor CONSLT samples, which carry
# 512267592 (הראל פנסיה וגמל), 513026484 (הפניקס פנסיה וגמל), 520004896 (מגדל
# חברה לביטוח) and 570009449 (עוצ"מ) — all four agree.
#
# One brand is often TWO bodies: the פנסיה-וגמל manager and the insurance
# company (ביטוח מנהלים). A production report is per body, so an agent's full
# book at הראל is two 2000 requests, not one. Only the bodies agents here
# actually work with are listed; add others from the same datasets, never
# from memory — a wrong ח.פ asks a real insurer for someone else's book.
PROVIDER_CODE_TO_COMPANY: dict[str, str] = {
    # פנסיה וגמל (גמל-נט / פנסיה-נט)
    "514956465": "מור גמל ופנסיה בע\"מ",
    "512065202": "מיטב גמל ופנסיה בע\"מ",
    "513611509": "ילין לפידות ניהול קופות גמל בע\"מ",
    "511880460": "אנליסט קופות גמל בע\"מ",
    "513173393": "אלטשולר שחם גמל ופנסיה בע\"מ",
    "512267592": "הראל פנסיה וגמל בע\"מ",
    "513026484": "הפניקס פנסיה וגמל בע\"מ",
    "512244146": "כלל פנסיה וגמל בע\"מ",
    "512237744": "מגדל מקפת קרנות פנסיה וקופות גמל בע\"מ",
    "512245812": "מנורה מבטחים פנסיה וגמל בע\"מ",
    "513621110": "אינפיניטי השתלמות, גמל ופנסיה בע\"מ",
    "517085874": "איילון קופות גמל בע\"מ",
    "570009449": "עוצ\"מ - אגודה שיתופית לניהול קופות גמל בע\"מ",
    # חברות ביטוח (ביטוח-נט)
    "520004078": "הראל חברה לביטוח בע\"מ",
    "520023185": "הפניקס חברה לביטוח בע\"מ",
    "520024647": "כלל חברה לביטוח בע\"מ",
    "520004896": "מגדל חברה לביטוח בע\"מ",
    "520042540": "מנורה מבטחים חברה לביטוח בע\"מ",
    "520030677": "איילון חברה לביטוח בע\"מ",
    "520042177": "הכשרה חברה לביטוח בע\"מ",
}


# Names our own records use for a body, when they differ from its legal name.
# אקסלנס was merged into הפניקס פנסיה וגמל (same ח.פ in גמל-נט today).
# Only UNAMBIGUOUS names: a bare "הפניקס" / "הראל" / "מגדל" / "כלל" / "מנורה" is
# either the insurance company or the pension-and-gemel company, so it is left
# unmapped (the agent picks it by hand) rather than guessed.
_COMPANY_ALIASES: dict[str, str] = {
    "הפניקס אקסלנס פנסיה וגמל בע\"מ": "513026484",
    "הפניקס גמל": "513026484",
    "מנורה מבטחים ביטוח בע\"מ": "520042540",
    "הראל גמל": "512267592",
    "הראל מגוון": "512267592",          # מגוון = הראל's pension fund
    "מור": "514956465",
    "מיטב דש": "512065202",
    "ילין לפידות": "513611509",
    "אלטשולר": "513173393",
    "הכשרה": "520042177",
}


def _norm_name(name: str) -> str:
    return " ".join((name or "").replace("״", '"').replace("''", '"').split())


def provider_code_for_company(name: str | None) -> str | None:
    """Map a `receiving_company` label from the agent's records to a body's ח.פ.
    Exact (normalised) match only — a fuzzy guess would ask the wrong insurer."""
    n = _norm_name(name or "")
    if not n:
        return None
    for code, legal in PROVIDER_CODE_TO_COMPANY.items():
        if _norm_name(legal) == n:
            return code
    return _COMPANY_ALIASES.get(n)


def is_known_provider(code: str | None) -> bool:
    """True only for a ח.פ in the sourced table above. A production-report
    request refuses anything else rather than send an unverified ID."""
    return bool(code) and str(code).strip() in PROVIDER_CODE_TO_COMPANY


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
