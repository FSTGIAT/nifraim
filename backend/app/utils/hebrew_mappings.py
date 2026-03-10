# Column mappings for Agent Tracking File (Excellence xlsx format)
AGENT_TRACKING_COLUMNS = {
    "תאריך חתימה": "sign_date",
    "שם פרטי": "first_name",
    "שם משפחה": "last_name",
    "ת.ז": "id_number",
    "ת.ז.": "id_number",
    "תעודת זהות": "id_number",
    "סוג גיוס": "recruitment_type",
    "מוצר": "product",
    "מספר קופה/פוליסה": "fund_policy_number",
    "מעמד": "employment_status",
    "פעיל": "is_active",
    "פעיל/לא פעיל": "is_active",
    "גוף מקבל": "receiving_company",
    "חברה מקבלת": "receiving_company",
    "מסלול": "track",
    "קופה מעבירה": "transferring_fund",
    "גוף מעביר": "transferring_body",
    "סכום העברה צפוי": "expected_amount",
    "סכום העברה בפועל": "actual_amount",
    "תאריך העברה": "transfer_date",
    "ת. ערך העברת הכספים": "transfer_date",
    "דמי ניהול": "management_fee",
    "מקור ליד": "lead_source",
    "מקור הליד": "lead_source",
    "מספר סוכן": "agent_number",
    "על איזה מספר הוחתם": "agent_number",
    "תאריך המחאת זכויות": "rights_assignment_date",
    "תאריך המחאת זכויות / מינוי סוכן למספר שלי": "rights_assignment_date",
    "הערות": "general_notes",
    "הערות כלליות": "general_notes",
}

# Column mappings for Company Commission Report (Phoenix xls format)
COMPANY_REPORT_COLUMNS = {
    "תעודת זהות": "id_number",
    "ת.ז": "id_number",
    "ת.ז.": "id_number",
    "תז העמית": "id_number",
    "שם העמית": "full_name",
    "שם לקוח": "full_name",
    "שם": "full_name",
    "יתרת סוף חודש": "balance",
    "יתרה": "balance",
    "צבירה": "balance",
    "עמלת סוכן": "commission_paid",
    "עמלה": "commission_paid",
    'עמלה לתשלום כולל מע"מ': "commission_paid",
    "דמי ניהול החודש": "management_fee",
    "דמי ניהול": "management_fee",
    "מספר חשבון": "fund_policy_number",
    "מספר קופה": "fund_policy_number",
    "מס' קופה": "fund_policy_number",
    "מוצר": "product",
    "שם מוצר": "product",
    "שם קופה": "product",
    "מספר סוכן": "agent_number",
    "סטטוס": "is_active",
    "מעמד": "employment_status",
    "שיעור דמי ניהול": "management_fee",
    "מספר עמית": "fund_policy_number",
    "תאריך הצטרפות": "sign_date",
    "סוג עמית": "employment_status",
}

# Column mappings for Production File (קובץ פרודוקציה)
PRODUCTION_FILE_COLUMNS = {
    "מספר ת.ז": "id_number",
    "שם פרטי לקוח": "first_name",
    "שם משפחה לקוח": "last_name",
    "יצרן": "receiving_company",
    "סוג מוצר": "product_type",
    "מוצר": "product",
    "מס' חשבון/פוליסה": "fund_policy_number",
    'סה"כ פרמיה': "total_premium",
    "צבירה": "accumulation",
    "סטטוס מוצר": "product_status",
    "תאריך הצטרפות למוצר": "sign_date",
    "תאריך הצטרפות": "sign_date",
    "סלולרי לקוח": "client_phone",
    'דוא"ל לקוח': "client_email",
    "שם מעסיק": "employer_name",
    "מזהה מעסיק": "employer_id",
    # מסלולי השקעה sheet columns
    "שם מסלול": "track",
    "צבירה במסלול": "accumulation",
    "צבירה במוצר": "accumulation",
}

# Column mappings for Commission Report (דוח נפרעים — Mor)
NIFRAIM_REPORT_COLUMNS = {
    "זהות": "id_number",
    "שם פרטי": "first_name",
    "שם משפחה": "last_name",
    "חשבון": "fund_policy_number",
    "סוג קופה": "fund_type",
    'מספר מ"ה קופה': "fund_number",
    "יתרה לסוף חודש בזמן חישוב עמלות": "month_end_balance",
    "אחוז עמלה שנתית נטו": "annual_commission_pct",
    "אחוז עמלה חודשי": "monthly_commission_pct",
    "עמלה ללא ניכוי דמי סליקה": "commission_before_fee",
    "מס' סוכן": "agent_number",
    "ת. פתיחת חשבון": "sign_date",
}

# Column mappings for Hachshara Commission Report (נפרעים הכשרה)
HACHSHARA_NIFRAIM_COLUMNS = {
    "ת.ז מבוטח": "id_number",
    "שם מבוטח": "full_name",
    "מספר פוליסה": "fund_policy_number",
    "תחילת ביטוח": "sign_date",
    "יתרת צבירה": "balance",
    "אחוז דמי ניהול": "management_fee",
    "סכום דמי ניהול": "management_fee_amount",
    "סכום עמלה סוכן": "commission_paid",
    "סכום עמלה סוכן ללא מעמ": "commission_before_fee",
    "סוג מוצר": "fund_type",
    "מספר סוכן": "agent_number",
    "תאריך עיבוד": "processing_date",
}

# Column mappings for Menora Commission Reports (all variants: financial, insurance, health)
MENORA_COLUMNS = {
    # Common fields across all Menora variants
    "מספר ת.ז מבוטח/עמית": "id_number",
    "שם מבוטח/עמית": "full_name",
    "מספר פוליסה": "fund_policy_number",
    "מספר תיק": "fund_number",
    "שם מוצר": "product",
    "מספר סוכן": "agent_number",
    "חודש עיבוד": "processing_date",
    "תאריך הסכם": "sign_date",
    # Financial variant (מנורה פיננסי)
    "צבירה": "balance",
    "אחוז דמי ניהול מצבירה בפועל": "management_fee",
    "סוכן-סה'כ עמלה": "commission_paid",
    # Insurance variant (מנורה ביטוח)
    "פרמיה ברוטו": "total_premium",
    "סוכן-פרמיה נטו": "commission_before_fee",
    "סוכן-סכום עמלה": "commission_paid",
    # Health variant (מנורה בריאות)
    "פרמיה ששולמה": "total_premium",
    "פרמיה לעמלה": "commission_expected",
}

# Column mappings for Altshuler Commission Report (אלטשולר שחם)
ALTSHULER_COLUMNS = {
    "מס. ת.ז": "id_number",
    "שם עמית": "full_name",
    "מספר חשבון": "fund_policy_number",
    "שם קופה": "product",
    "מספר סוכן": "agent_number",
    "ערך קופה (₪)": "balance",
    'ד.נ סוכן סה"כ': "commission_paid",
    "דמי ניהול מצבירה לחודש": "management_fee_amount",
    "% דמי ניהול מצבירה": "management_fee",
    "תאריך הצטרפות": "sign_date",
    "מספר קופה": "fund_number",
}

# Column mappings for Phoenix Insurance Commission Report (נפרעים הפניקס ביטוח)
PHOENIX_INSURANCE_NIFRAIM_COLUMNS = {
    "תז המבוטח": "id_number",
    "שם המבוטח": "full_name",
    "מס' פוליסה": "fund_policy_number",
    "ענף": "fund_type",
    "סוג פוליסה": "product",
    "צבירה": "balance",
    "פרמיה": "total_premium",
    'סה"כ לתשלום': "commission_paid",
    "תאריך התחלה": "sign_date",
    "חודש עיבוד": "processing_date",
    "סוכן מקבל עמלה": "agent_number",
}

# Column mappings for Harel Commission Report (הראל דוח עמלות)
HAREL_NIFRAIM_COLUMNS = {
    "ת.ז": "id_number",
    "שם מבוטח": "full_name",
    "מספר פוליסה": "fund_policy_number",
    "ענף": "fund_type",
    "סוג פוליסה": "product",
    "פרמיה": "total_premium",
    "עמלה": "commission_paid",
    "דמי גביה": "management_fee_amount",
    "סכום תשלום": "commission_before_fee",
    "חודש עיבוד": "processing_date",
    "חודש תפוקה": "sign_date",
    "מספר סוכן": "agent_number",
    "מעסיק": "employer_name",
    "מספר מעסיק": "employer_id",
}

# Column mappings for Clal Life Commission Report (כלל חיים)
CLAL_LIFE_NIFRAIM_COLUMNS = {
    "ת.ז/מזהה מבוטח ראשי": "id_number",
    "שם מבוטח ראשי": "full_name",
    "מספר פוליסה": "fund_policy_number",
    "סטטוס פוליסה": "is_active",
    "תאריך תחילת ביטוח של הפוליסה": "sign_date",
    "תאריך עיבוד": "processing_date",
    "סך פרמיה": "total_premium",
    'סה"כ עמלה': "commission_paid",
    "סך עמלה מפרמיה": "commission_before_fee",
    "סך עמלה מצבירה": "management_fee_amount",
    "מס' סוכן מקבל עמלה": "agent_number",
    "שם מעסיק בפוליסה": "employer_name",
}

# Column mappings for Clal Health Commission Report (כלל בריאות)
CLAL_HEALTH_NIFRAIM_COLUMNS = {
    "זיהוי מבוטח": "id_number",
    "שם מבוטח": "full_name",
    "מספר פוליסה": "fund_policy_number",
    "סטטוס פוליסה": "is_active",
    "תאריך תחילה": "sign_date",
    "תקבול בפועל": "total_premium",
    'סה"כ לתשלום': "commission_paid",
    "תשלום עמלה בפועל - נפרעים": "commission_before_fee",
    "תשלום עמלה בפועל - ניהול": "management_fee_amount",
    "מספר סוכן עמלה": "agent_number",
}

# Column mappings for Migdal Commission Report (מגדל)
MIGDAL_NIFRAIM_COLUMNS = {
    "ת.ז מבוטח": "id_number",
    "שם מבוטח": "full_name",
    "מספר פוליסה": "fund_policy_number",
    "סוג פוליסה": "product",
    "חודש תחילת ביטוח": "sign_date",
    "תאריך תשלום": "processing_date",
    "פרמיה משולמת": "total_premium",
    "עמלה": "commission_paid",
    "דמי גביה": "management_fee_amount",
    'סה"כ': "commission_before_fee",
    "מספר מקבל עמלה": "agent_number",
    "שם מפעל": "employer_name",
}

# Column mappings for Ayalon Commission Report (איילון)
AYALON_NIFRAIM_COLUMNS = {
    "ת.ז מבוטח": "id_number",
    "שם מלא מבוטח": "full_name",
    "מספר פוליסה": "fund_policy_number",
    "תיאור מוצר": "product",
    "תאריך תחילת ביטוח": "sign_date",
    "תאריך נכונות": "processing_date",
    "פרמיה נפרעת": "total_premium",
    "סך עמלת סוכן": "commission_paid",
    "סך דמי צבירה": "management_fee_amount",
    "סכום צבירה": "balance",
    "מספר סוכן": "agent_number",
    "שם מפעל": "employer_name",
    "מספר מפעל": "employer_id",
}

# Keywords that indicate a cancelled transfer in raw text
CANCELLATION_KEYWORDS = [
    "בוטל",
    "בוטלה",
    "ביטול",
    "לא בוצע",
    "נדחה",
    "סירוב",
    "חזרה",
]

# Signature columns to detect file format
AGENT_TRACKING_SIGNATURE = {"סכום העברה צפוי", "סכום העברה בפועל"}
COMPANY_REPORT_SIGNATURE = {"יתרת סוף חודש", "עמלת סוכן"}
PHOENIX_COMMISSION_SIGNATURE = {"תז העמית", 'עמלה לתשלום כולל מע"מ'}
PRODUCTION_FILE_SIGNATURE = {'סה"כ פרמיה', "סטטוס מוצר", "יצרן"}
NIFRAIM_REPORT_SIGNATURE = {"עמלה ללא ניכוי דמי סליקה", "אחוז עמלה שנתית נטו"}
HACHSHARA_NIFRAIM_SIGNATURE = {"סכום עמלה סוכן ללא מעמ", "יתרת צבירה"}
MENORA_SIGNATURE = {"מספר ת.ז מבוטח/עמית", "שם סוג עמלה"}
ALTSHULER_SIGNATURE = {'ד.נ סוכן סה"כ', "ערך קופה (₪)"}
PHOENIX_INSURANCE_NIFRAIM_SIGNATURE = {"תז המבוטח", 'סה"כ לתשלום'}
HAREL_NIFRAIM_SIGNATURE = {"סכום תשלום", 'אופי חו"ז'}
CLAL_LIFE_NIFRAIM_SIGNATURE = {"ת.ז/מזהה מבוטח ראשי", "סך עמלה מפרמיה"}
CLAL_HEALTH_NIFRAIM_SIGNATURE = {"זיהוי מבוטח", "תשלום עמלה בפועל - נפרעים"}
MIGDAL_NIFRAIM_SIGNATURE = {"פרמיה משולמת", "ת.ז מבוטח"}
AYALON_NIFRAIM_SIGNATURE = {"פרמיה נפרעת", "סך עמלת סוכן"}

# Known header keywords for scanning buried headers
HEADER_SCAN_KEYWORDS = {"תז העמית", "שם העמית", "תעודת זהות", "זהות", "שם פרטי",
                        "עמלת סוכן", "יתרת סוף חודש", 'עמלה לתשלום כולל מע"מ',
                        "עמלה ללא ניכוי דמי סליקה", "אחוז עמלה שנתית נטו",
                        "ת.ז מבוטח", "סכום עמלה סוכן ללא מעמ",
                        "מספר ת.ז מבוטח/עמית", "תז המבוטח",
                        "ת.ז/מזהה מבוטח ראשי", "זיהוי מבוטח", "פרמיה משולמת",
                        "פרמיה נפרעת"}

# Default commission rates from the rate table image
DEFAULT_COMMISSION_RATES = [
    {"company_name": "יצח", "rate": 0.004, "payment_frequency": "חודשי", "paid_to": "עיתים", "company_email": None},
    {"company_name": "פניקס פוליסות", "rate": 0.0034, "payment_frequency": "חודשי", "paid_to": "עיתים", "company_email": None},
    {"company_name": "פניקס גמל והשתלמות", "rate": 0.0045, "payment_frequency": "חודשי", "paid_to": "עיתים", "company_email": None},
    {"company_name": "הראל מגוון", "rate": 0.005, "payment_frequency": None, "paid_to": None, "company_email": None},
    {"company_name": "ילין גמל", "rate": 0.003, "payment_frequency": "חודשי", "paid_to": "עיתים", "company_email": None},
    {"company_name": "מיטב דש", "rate": 0.003, "payment_frequency": "רבעוני", "paid_to": "עיתים", "company_email": None},
    {"company_name": "מור גמל", "rate": 0.003, "payment_frequency": "שנתי", "paid_to": "ידנים", "company_email": "amalotgp@more.co.il"},
    {"company_name": "אנליסט", "rate": 0.004, "payment_frequency": "שנתי", "paid_to": "ידנים", "company_email": None},
    {"company_name": "מגדל קשת", "rate": 0.003, "payment_frequency": "חודשי", "paid_to": "סוכן", "company_email": None},
    {"company_name": "הכשרה", "rate": 0.005, "payment_frequency": "רבעוני", "paid_to": "סוכן", "company_email": None},
    {"company_name": "אלטשולר", "rate": 0.003, "payment_frequency": "שנתי", "paid_to": "ידנים", "company_email": None},
    {"company_name": "אקסלנס ניהול תיקים", "rate": 0.0045, "payment_frequency": "שנתי", "paid_to": "ידנים", "company_email": None},
    {"company_name": "מור ניהול תיקים", "rate": 0.005, "payment_frequency": "חודשי", "paid_to": "עיתים", "company_email": "amalotgp@more.co.il"},
    {"company_name": "מיטב דש ניהול תיקים", "rate": 0.004, "payment_frequency": "חודשי", "paid_to": "עיתים", "company_email": None},
]

# Hebrew status labels
STATUS_LABELS = {
    "paid_match": "שולם - תואם",
    "paid_mismatch": "שולם - חריגה",
    "unpaid": "לא שולם",
    "cancelled": "בוטל",
    "no_data": "אין נתונים",
}
