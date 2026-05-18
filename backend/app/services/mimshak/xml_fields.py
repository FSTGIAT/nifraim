"""Known Mimshak XML element name → (english, meaning, target ClientRecord column).

Used by `parse_dat.py` to render the field-coverage report. Incomplete by design:
any element *not* in this map is listed in the report as "unmapped" so the user
can see what we don't yet understand.

`target_column` is None when we don't want to / can't store the field on
ClientRecord as-is (rich data — beneficiaries, fund allocations, etc.).
"""

# element_name -> (english_label, meaning_he, target_clientrecord_column_or_None)
XML_FIELD_MAP: dict[str, tuple[str, str, str | None]] = {
    # --- File header (ignored for records) ---
    "SUG-MIMSHAK": ("Mimshak type", "סוג ממשק", None),
    "MISPAR-GIRSAT-XML": ("XML version", "מספר גרסת XML", None),
    "TAARICH-BITZUA": ("Execution timestamp", "תאריך ביצוע", None),
    "KOD-SHOLEACH": ("Sender code", "קוד שולח", None),
    "SHEM-SHOLEACH": ("Sender name", "שם שולח", None),
    "MEZAHE-HAAVARA": ("Transfer identifier", "מזהה העברה", None),
    "MISPAR-HAKOVETZ": ("File number", "מספר הקובץ", None),

    # --- Insurer (YeshutYatzran) ---
    "KOD-MEZAHE-YATZRAN": ("Insurer code", "קוד מזהה יצרן", None),
    "SHEM-YATZRAN": ("Insurer name", "שם יצרן", "receiving_company"),

    # --- Customer identification ---
    "MISPAR-ZIHUY-LAKOACH": ("Customer national ID", "מספר זהות לקוח", "id_number"),
    "SUG-MEZAHE-LAKOACH": ("Customer ID type", "סוג מזהה לקוח", None),
    "SHEM-PRATI": ("First name", "שם פרטי", "first_name"),
    "SHEM-MISHPACHA": ("Last name", "שם משפחה", "last_name"),
    "MIN": ("Gender", "מין", None),  # 1=M, 2=F
    "TAARICH-LEYDA": ("Date of birth", "תאריך לידה", None),
    "MATZAV-MISHPACHTI": ("Marital status", "מצב משפחתי", None),

    # --- Customer contact ---
    "ERETZ": ("Country", "ארץ", None),
    "SHEM-YISHUV": ("City name", "שם יישוב", None),
    "SEMEL-YESHUV": ("City code", "סמל יישוב", None),
    "SHEM-RECHOV": ("Street", "שם רחוב", None),
    "MISPAR-BAIT": ("House number", "מספר בית", None),
    "MISPAR-KNISA": ("Entrance number", "מספר כניסה", None),
    "MISPAR-DIRA": ("Apartment number", "מספר דירה", None),
    "MIKUD": ("Zip code", "מיקוד", None),
    "TA-DOAR": ("PO Box", "ת.ד.", None),
    "MISPAR-TELEPHONE-KAVI": ("Landline phone", "מספר טלפון קווי", None),
    "MISPAR-CELLULARI": ("Mobile phone", "מספר סלולרי", "client_phone"),
    "MISPAR-FAX": ("Fax", "מספר פקס", None),
    "E-MAIL": ("Email", "דוא\"ל", "client_email"),

    # --- Product / account ---
    "SUG-MUTZAR": ("Product type", "סוג מוצר", "product_type"),
    "SHEM-TOCHNIT": ("Plan name", "שם תוכנית", "product"),
    "MISPAR-POLISA-O-HESHBON": ("Policy/account number", "מספר פוליסה או חשבון", "fund_policy_number"),
    "STATUS-POLISA-O-CHESHBON": ("Policy status code", "סטטוס פוליסה/חשבון", "product_status"),
    "TAARICH-HITZTARFUT-RISHON": ("First enrollment date", "תאריך הצטרפות ראשון", "sign_date"),
    "TAARICH-IDKUN-STATUS": ("Status update date", "תאריך עדכון סטטוס", None),
    "TAARICH-NECHONUT": ("Valuation date", "תאריך נכונות", None),
    "ASMACHTA-MEKORIT": ("Origin reference", "אסמכתא מקורית", None),
    "KIDOD-ACHID": ("Unified identifier", "קידוד אחיד", None),

    # --- Premium & money ---
    "SCHUM-BITUACH": ("Insurance amount / premium", "סכום ביטוח", "total_premium"),
    "SCHUM-HAFKADA-SHESHULAM": ("Deposit paid", "סכום הפקדה ששולם", None),
    "DMEI-BITUAH-LETASHLUM-BAPOAL": ("Insurance premium due", "דמי ביטוח לתשלום בפועל", None),
    "ERECH-PIDYON-SOF-SHANA": ("Year-end surrender value", "ערך פדיון סוף שנה", None),
    "ERECH-MESOLAK-SOF-SHANA": ("Year-end market value", "ערך מסולק סוף שנה", "accumulation"),
    "ERECH-HANACHA-BEKISUI": ("Value at coverage", "ערך הנחה בכיסוי", None),

    # --- Fees ---
    "DMEI-NIHUL-ACHERIM": ("Accrued mgmt fee (NIS)", "דמי ניהול אחרים", "management_fee_amount"),
    "DMEI-NIHUL-ACHIDIM": ("Uniform mgmt fee %", "דמי ניהול אחידים", "management_fee"),
    "GOVA-DMEI-NIHUL-NIKBA-AL-PI-HOTZAOT-BAPOAL": ("Actual mgmt fee charged", "גובה דמי ניהול שנגבה", None),
    "SACHAR-BERAMAT-HAFKADA": ("Fee charged on deposit", "שכר ברמת הפקדה", None),

    # --- Yield ---
    "SHEUR-TSUA-NETO": ("Net yield %", "שיעור תשואה נטו", None),
    "SHEUR-TSUA-BRUTO-CHS-1": ("Gross yield % (calc 1)", "שיעור תשואה ברוטו חישוב 1", None),
    "REVACH-HEFSED-BENIKOI-HOZAHOT": ("P/L after deductions", "רווח/הפסד בניכוי הוצאות", None),
    "SIMAN-REVACH-HEFSED": ("P/L sign indicator", "סימן רווח/הפסד", None),
    "ACHUZ-TSUA-BATACHAZIT": ("Yield % attributed to insurance", "אחוז תשואה בתחזית", None),

    # --- Beneficiaries / fund allocation ---
    "MISPAR-ZIHUY-MUTAV": ("Beneficiary ID", "מספר זהות מוטב", None),
    "SHEM-PRATI-MUTAV": ("Beneficiary first name", "שם פרטי מוטב", None),
    "SHEM-MISHPACHA-MUTAV": ("Beneficiary last name", "שם משפחה מוטב", None),
    "TAARICH-LEIDA-MUTAV": ("Beneficiary DOB", "תאריך לידה מוטב", None),
    "ACHUZ-MUTAV": ("Beneficiary/fund percentage", "אחוז מוטב", None),
    "HAGDARAT-MUTAV": ("Beneficiary role/fund name", "הגדרת מוטב", None),
    "SUG-ZIKA": ("Relationship type", "סוג זיקה", None),
    "KOD-ZIHUY-MUTAV": ("Fund ID code", "קוד זיהוי מוטב", None),
    "ACHUZ-HAFKADA-LEHASHKAA": ("Deposit allocation % to fund", "אחוז הפקדה להשקעה", None),
    "ACHOZ-HATAVA": ("Holding percentage", "אחוז הטבה", None),

    # --- Coverage / rider ---
    "KOD-SUG-TOSEFET": ("Rider type code", "קוד סוג תוספת", None),
    "SHEM-KISUI-YATZRAN": ("Coverage name (insurer label)", "שם כיסוי יצרן", None),
    "SUG-KISUI-ETZEL-YATZRAN": ("Coverage type code", "סוג כיסוי אצל יצרן", None),

    # --- Deposits / contributions ---
    "TAARICH-ERECH-HAFKADA": ("Deposit value date", "תאריך ערך הפקדה", None),
    "KOD-SUG-HAFKADA": ("Deposit type code", "קוד סוג הפקדה", None),

    # --- Indicators / flags ---
    "KAYAM-CHOV-O-PIGUR": ("Has outstanding debt / arrears", "קיים חוב או פיגור", None),
    "KAYAM-MEYUPE-KOACH": ("Has power of attorney", "קיים מיופה כוח", None),
    "KAYAM-RETZEF-PITZUIM-KITZBA": ("Has scheduled pension sequence", "קיים רצף פיצויים קצבה", None),
    "IND-SCHUM-BITUAH-KOLEL-CHISACHON": ("Premium includes savings (ind.)", "אינד: סכום ביטוח כולל חיסכון", None),
    "BITUL-KIZUZ-MEMSHALTI": ("Gov fee discount (Y/N)", "ביטול קיזוז ממשלתי", None),
    "KNAS-MESHICHA-NIUD": ("Early withdrawal penalty", "קנס משיכה ניוד", None),
    "ACHUZ-HAKTZAA-LE-CHISACHON": ("Savings allocation %", "אחוז הקצאה לחיסכון", None),
}


# Columns on ClientRecord currently written by at least one Excel parser.
# Used to classify report rows.
CLIENT_RECORD_COLUMNS: set[str] = {
    "id_number", "first_name", "last_name",
    "sign_date", "recruitment_type",
    "product", "product_type", "fund_policy_number",
    "employment_status", "is_active", "receiving_company",
    "track", "transferring_fund", "transferring_body",
    "total_premium", "accumulation", "product_status",
    "fund_type", "fund_number", "month_end_balance",
    "annual_commission_pct", "monthly_commission_pct",
    "commission_before_fee", "commission_paid", "commission_expected",
    "expected_amount", "actual_amount", "expected_raw", "actual_raw",
    "amount_difference",
    "transfer_date", "management_fee", "management_fee_amount",
    "lead_source", "agent_number", "rights_assignment_date",
    "general_notes", "processing_date",
    "balance",
    "client_phone", "client_email",
    "employer_name", "employer_id",
    "reconciliation_status",
}
