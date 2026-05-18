"""Sheet-by-sheet column lists for the production xlsx.

Column order must match the SaaS-generated reference file exactly — the
Nifraim `_parse_production` parser keys off column headers.
"""

# --- Sheet 5: מוצרי ביטוח ---
# One row per HeshbonOPolisa (policy).
COLUMNS_INSURANCE_PRODUCTS: list[str] = [
    "יצרן",
    "סוג מוצר",
    "מוצר",
    "מס' חשבון/פוליסה",
    "סוכנות",
    "שם פרטי לקוח",
    "שם משפחה לקוח",
    "מספר ת.ז",
    "סלולרי לקוח",
    'דוא"ל לקוח',
    "תאריך לידה",
    "גיל",
    "מגדר",
    "יישוב",
    "סיווג לקוח",
    'סה"כ פרמיה',
    "סטטוס מוצר",
    "תאריך עדכון סטטוס",
    "תאריך הצטרפות למוצר",
    "מזהה מעסיק",
    "שם מעסיק",
    "מספר סוכן",
    "תיאור מספר סוכן",
    "מיופה כוח אחרון",
    'מת"ל',
    "נכון ליום",
]


# --- Sheet 6: מוצרי ביטוח (כיסויים) ---
# One row per ZihuiKisui (rider) inside each HeshbonOPolisa.
COLUMNS_INSURANCE_COVERAGES: list[str] = [
    "יצרן",
    "סוג מוצר",
    "מוצר",
    "מס' חשבון/פוליסה",
    "שם פרטי לקוח",
    "שם משפחה לקוח",
    "מספר ת.ז",
    "סלולרי לקוח",
    'דוא"ל לקוח',
    "תאריך לידה",
    "גיל",
    "מגדר",
    'מת"ל',
    "מספר סוכן",
    "תיאור מספר סוכן",
    "סוג כיסוי",
    "שם כיסוי",
    "סוג מבוטח",
    "שם מבוטח",
    "מזהה מבוטח",
    "תקופת כיסוי",
    "תאריך תחילת כיסוי",
    "תאריך תום כיסוי",
    "תדירות תשלום",
    "פרמיה",
    "סכום ביטוח",
    "קוד נספח כיסוי",
    "תוספת רפואית (%)",
    "תוספת מקצועית (%)",
    "נכון ליום",
]


# --- Sheet 1: דוח מסכם לפי יצרן ---
COLUMNS_SUMMARY_BY_INSURER: list[str] = [
    "יצרן",
    "מספר סוכן",
    "כמות לקוחות",
    "כמות מוצרים בניהול",
    "צבירה בניהול",
    "הפקדה בניהול",
    "פרמיה בניהול",
]


# --- Sheet 2: דוח מסכם לפי מוצר ---
COLUMNS_SUMMARY_BY_PRODUCT: list[str] = [
    "יצרן",
    "סוג מוצר",
    "מוצר",
    "מספר סוכן",
    "כמות לקוחות למוצר",
    "כמות מוצרים בניהול",
    "צבירה בניהול",
    "הפקדה בניהול",
    "פרמיה בניהול",
]


# Lookups: Mimshak code → Hebrew label. Derived from reference SaaS xlsx.

# The reference xlsx spells the insurer with an extra ל (לביטוח).
# The DAT uses the shorter form (לבטוח). Normalize to match the reference.
INSURER_NAME_OVERRIDES: dict[str, str] = {
    'מגדל חברה לבטוח בע"מ': 'מגדל חברה לביטוח בע"מ',
}

SUG_MUTZAR_LABELS: dict[str, str] = {
    "1": "ביטוח חיים",
    "2": "ביטוח בריאות",
    "3": "ביטוח סיעוד",
    "4": "ביטוח כללי",
    "5": "ביטוח נסיעות",
}

# Policy status: code 7 = פעיל confirmed from Migdal reference rows.
STATUS_POLISA_LABELS: dict[str, str] = {
    "1": "פעיל",
    "2": "מוקפא",
    "3": "מבוטל",
    "4": "פרוץ",
    "5": "סילוק",
    "6": "ממתין",
    "7": "פעיל",
    "8": "ממתין לחיתום",
    "9": "לא פעיל",
}

SUG_TEUDA_LABELS: dict[str, str] = {
    "1": "ת.ז.",
    "2": "דרכון",
}

MIN_LABELS: dict[str, str] = {
    "1": "זכר",
    "2": "נקבה",
}

# Insured role on coverage: "ראשי" confirmed for code 1 from reference.
SUG_MEVUTACH_LABELS: dict[str, str] = {
    "1": "ראשי",
    "2": "בן/בת זוג",
    "3": "ילד",
    "4": "הורה",
}

# Payment frequency label from `TADIRUT-TASHLUM` under `NetuneiGvia`.
# `5` was observed to correspond to "חודשית" in the reference file.
TADIRUT_TASHLUM_LABELS: dict[str, str] = {
    "1": "שנתית",
    "2": "חצי שנתית",
    "3": "רבעונית",
    "4": "דו-חודשית",
    "5": "חודשית",
    "6": "חד פעמית",
}

# Coverage-type (`SUG-KISUI-ETZEL-YATZRAN`) → Hebrew label from reference.
# Code 1 = "ביטוח חיים למקרה מוות" (death benefit life insurance).
SUG_KISUI_LABELS: dict[str, str] = {
    "1": "ביטוח חיים למקרה מוות",
    "2": "אובדן כושר עבודה",
    "3": "נכות מתאונה",
    "4": "מחלות קשות",
    "5": "סיעוד",
    "6": "בריאות",
    "8": "ביטוח חיים למקרה מוות",
}

# Coverage period type — inferred from `TAARICH-TOM-KISUY` presence vs. flag.
# If end date is set and in the future, "תקופה מוגדרת"; else "תקופה פתוחה".
COV_PERIOD_DEFINED = "תקופה מוגדרת"
COV_PERIOD_OPEN = "תקופה פתוחה"
