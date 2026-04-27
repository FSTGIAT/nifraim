# Mimshak DAT / MBT field-coverage report

**Source file:** `201000512237744HOLDNGINP009202604141624556378.DAT`  

**Sample stats:** 5 customers · 6 policies · 9 coverages · 20 beneficiaries · 10 fund allocations


## Section A · XML element map

All XML leaf elements encountered, in descending frequency. `target` is the `ClientRecord` column we'd write into (or `—` if it's richer than the flat schema can represent).

| # seen | Element | English | Meaning (He) | → ClientRecord |
|-------:|---------|---------|--------------|----------------|
| 21 | `SUG-HAFRASHA` | (unmapped) | — | — |
| 21 | `TCHILAT-TKUFA` | (unmapped) | — | — |
| 21 | `TOM-TKUFA` | (unmapped) | — | — |
| 17 | `ERETZ` | Country | ארץ | — |
| 17 | `SHEM-YISHUV` | City name | שם יישוב | — |
| 17 | `SEMEL-YESHUV` | City code | סמל יישוב | — |
| 17 | `SHEM-RECHOV` | Street | שם רחוב | — |
| 17 | `MISPAR-BAIT` | House number | מספר בית | — |
| 17 | `MISPAR-KNISA` | Entrance number | מספר כניסה | — |
| 17 | `MISPAR-DIRA` | Apartment number | מספר דירה | — |
| 17 | `MIKUD` | Zip code | מיקוד | — |
| 17 | `TA-DOAR` | PO Box | ת.ד. | — |
| 16 | `MISPAR-TELEPHONE-KAVI` | Landline phone | מספר טלפון קווי | — |
| 16 | `MISPAR-CELLULARI` | Mobile phone | מספר סלולרי | client_phone |
| 16 | `MISPAR-FAX` | Fax | מספר פקס | — |
| 16 | `E-MAIL` | Email | דוא"ל | client_email |
| 16 | `HEAROT` | (unmapped) | — | — |
| 15 | `MISPAR-KISUI-BE-YATZRAN` | (unmapped) | — | — |
| 15 | `SCHUM-BITUACH` | Insurance amount / premium | סכום ביטוח | total_premium |
| 15 | `DMEI-NIHUL-ACHERIM` | Accrued mgmt fee (NIS) | דמי ניהול אחרים | management_fee_amount |
| 15 | `SUG-ZIHUY-MUTAV` | (unmapped) | — | — |
| 15 | `KOD-ZIHUY-MUTAV` | Fund ID code | קוד זיהוי מוטב | — |
| 15 | `MISPAR-ZIHUY-MUTAV` | Beneficiary ID | מספר זהות מוטב | — |
| 15 | `SHEM-PRATI-MUTAV` | Beneficiary first name | שם פרטי מוטב | — |
| 15 | `SHEM-MISHPACHA-MUTAV` | Beneficiary last name | שם משפחה מוטב | — |
| 15 | `TAARICH-LEIDA-MUTAV` | Beneficiary DOB | תאריך לידה מוטב | — |
| 15 | `SUG-ZIKA` | Relationship type | סוג זיקה | — |
| 15 | `ACHUZ-MUTAV` | Beneficiary/fund percentage | אחוז מוטב | — |
| 15 | `HAGDARAT-MUTAV` | Beneficiary role/fund name | הגדרת מוטב | — |
| 15 | `MAHUT-MUTAV` | (unmapped) | — | — |
| 15 | `PREMIA-ZFOYA` | (unmapped) | — | — |
| 15 | `TAARICH-ERECH-HAFKADA` | Deposit value date | תאריך ערך הפקדה | — |
| 15 | `KOD-SUG-HAFKADA` | Deposit type code | קוד סוג הפקדה | — |
| 15 | `SUG-MAFKID` | (unmapped) | — | — |
| 15 | `SACHAR-BERAMAT-HAFKADA` | Fee charged on deposit | שכר ברמת הפקדה | — |
| 15 | `SCHUM-HAFKADA-SHESHULAM` | Deposit paid | סכום הפקדה ששולם | — |
| 15 | `CHODESH-SACHAR` | (unmapped) | — | — |
| 14 | `MISPAR-ZIHUY-LAKOACH` | Customer national ID | מספר זהות לקוח | id_number |
| 13 | `KOD-SUG-HAFRASHA` | (unmapped) | — | — |
| 13 | `SHEUR-DMEI-NIHUL-HAFKADA` | (unmapped) | — | — |
| 13 | `ZMAN-PERAON` | (unmapped) | — | — |
| 13 | `KOD-MEZAHE-KOPA-MAAVIRA` | (unmapped) | — | — |
| 13 | `SHEM-KOPA-MAAVIRA` | (unmapped) | — | — |
| 13 | `MOED-KOVEA-NIUD` | (unmapped) | — | — |
| 12 | `SUG-TOCHNIT-O-CHESHBON` | (unmapped) | — | — |
| 12 | `MISPAR-ZIHUY` | (unmapped) | — | — |
| 11 | `SHEM-PRATI` | First name | שם פרטי | first_name |
| 11 | `SHEM-MISHPACHA` | Last name | שם משפחה | last_name |
| 11 | `MISPAR-SHLUCHA` | (unmapped) | — | — |
| 11 | `MPR-MAASIK-BE-YATZRAN` | (unmapped) | — | — |
| 9 | `SHEM-KISUI-YATZRAN` | Coverage name (insurer label) | שם כיסוי יצרן | — |
| 9 | `SUG-KISUI-ETZEL-YATZRAN` | Coverage type code | סוג כיסוי אצל יצרן | — |
| 9 | `MISPAR-POLISA-O-HESHBON-NEGDI` | (unmapped) | — | — |
| 9 | `SUG-TEUDA` | (unmapped) | — | — |
| 9 | `KOD-MIUTZAR-LAKISUY` | (unmapped) | — | — |
| 9 | `SUG-MEVUTACH` | (unmapped) | — | — |
| 9 | `SUG-KISUY-BITOCHI` | (unmapped) | — | — |
| 9 | `TAARICH-TCHILAT-KISUY` | (unmapped) | — | — |
| 9 | `TAARICH-TOM-KISUY` | (unmapped) | — | — |
| 9 | `KOD-NISPACH-KISUY` | (unmapped) | — | — |
| 9 | `SUG-ISUK` | (unmapped) | — | — |
| 9 | `KOLEL-PRENZISA` | (unmapped) | — | — |
| 9 | `KOLEL-SIUD` | (unmapped) | — | — |
| 9 | `KITZBA-ZMUDA-LAMADAD` | (unmapped) | — | — |
| 9 | `NACHUT-MITPATAHAT` | (unmapped) | — | — |
| 9 | `BITUL-KIZUZ-MEMSHALTI` | Gov fee discount (Y/N) | ביטול קיזוז ממשלתי | — |
| 9 | `TAARICH-HAFSAKAT-TASHLUM` | (unmapped) | — | — |
| 9 | `ACHUZ-ME-SCM-BTH-YESODI` | (unmapped) | — | — |
| 9 | `ACHUZ-MESACHAR` | (unmapped) | — | — |
| 9 | `OFEN-TASHLUM-SCHUM-BITUACH` | (unmapped) | — | — |
| 9 | `TIKRAT-GAG-HATAM-LE-O-K-A` | (unmapped) | — | — |
| 9 | `ACHUZ-HAGDALAT-GAG-HATAM-O-K-A` | (unmapped) | — | — |
| 9 | `SCHUM-SHEUR` | (unmapped) | — | — |
| 9 | `SCHUM-BITUH-KAVOA-MISHTANE` | (unmapped) | — | — |
| 9 | `SHEUR-BITUH-KAVOA-MISHTANE` | (unmapped) | — | — |
| 9 | `MESHALEM-HAKISUY` | (unmapped) | — | — |
| 9 | `KOD-ISHUN` | (unmapped) | — | — |
| 9 | `IND-CHITUM` | (unmapped) | — | — |
| 9 | `TAARICH-CHITUM` | (unmapped) | — | — |
| 9 | `HACHRAGA` | (unmapped) | — | — |
| 9 | `SUG-HACHRAGA` | (unmapped) | — | — |
| 9 | `TKUFAT-ACHSHARA` | (unmapped) | — | — |
| 9 | `TKUFAT-HAMTANA-CHODASHIM` | (unmapped) | — | — |
| 9 | `HANACHA` | (unmapped) | — | — |
| 9 | `HATNAYA-LAHANACHA-DMEI-BITUAH` | (unmapped) | — | — |
| 9 | `DMEI-BITUAH-LETASHLUM-BAPOAL` | Insurance premium due | דמי ביטוח לתשלום בפועל | — |
| 9 | `SUG-HANACHA-KISUY` | (unmapped) | — | — |
| 9 | `SHIUR-HANACHA-BEKISUI` | (unmapped) | — | — |
| 9 | `ERECH-HANACHA-BEKISUI` | Value at coverage | ערך הנחה בכיסוי | — |
| 9 | `HANACHA-MEDUREGET` | (unmapped) | — | — |
| 9 | `TNAEI-HANACHA` | (unmapped) | — | — |
| 9 | `MOED-SIUM-TKUFAT-HANACHA` | (unmapped) | — | — |
| 9 | `TADIRUT-SHINUY-DMEI-HABITUAH-BESHANIM` | (unmapped) | — | — |
| 9 | `TAARICH-IDKUN-HABA-SHEL-DMEI-HABITUAH` | (unmapped) | — | — |
| 9 | `TOSEFET-TAARIF` | (unmapped) | — | — |
| 9 | `KOD-SUG-TOSEFET` | Rider type code | קוד סוג תוספת | — |
| 9 | `SHEUR-TOSEFET` | (unmapped) | — | — |
| 9 | `PROMIL-TOSEFET` | (unmapped) | — | — |
| 9 | `TAARICH-TOM-TOSEFET` | (unmapped) | — | — |
| 9 | `TACHVIVIM-O-ISUKIM` | (unmapped) | — | — |
| 9 | `KOD-MIKTZOA` | (unmapped) | — | — |
| 9 | `TCHUM-ISUK-CHADASH` | (unmapped) | — | — |
| 8 | `GOVA-DMEI-NIHUL-NIKBA-AL-PI-HOTZAOT-BAPOAL` | Actual mgmt fee charged | גובה דמי ניהול שנגבה | — |
| 8 | `SUG-HOTZAA` | (unmapped) | — | — |
| 8 | `KOD-MASLUL-DMEI-NIHUL` | (unmapped) | — | — |
| 8 | `MEAFYENEI-MASLUL-DMEI-NIHUL` | (unmapped) | — | — |
| 8 | `SHEUR-DMEI-NIHUL` | (unmapped) | — | — |
| 8 | `TAARICH-IDKUN-SHEUR-DNHL` | (unmapped) | — | — |
| 8 | `DMEI-NIHUL-ACHIDIM` | Uniform mgmt fee % | דמי ניהול אחידים | management_fee |
| 8 | `KOD-MASLUL-HASHKAA-BAAL-DMEI-NIHUL-YECHUDIIM` | (unmapped) | — | — |
| 8 | `OFEN-HAFRASHA` | (unmapped) | — | — |
| 8 | `SCHUM-MAX-DNHL-HAFKADA` | (unmapped) | — | — |
| 8 | `SACH-DMEI-NIHUL-MASLUL` | (unmapped) | — | — |
| 8 | `KENAS-MESHICHAT-KESAFIM` | (unmapped) | — | — |
| 8 | `KAYEMET-HATAVA` | (unmapped) | — | — |
| 8 | `SUG-HATAVA` | (unmapped) | — | — |
| 8 | `ACHOZ-HATAVA` | Holding percentage | אחוז הטבה | — |
| 8 | `TAARICH-SIUM-HATAVA` | (unmapped) | — | — |
| 8 | `KOD-TECHULAT-SHICHVA` | (unmapped) | — | — |
| 8 | `TIKRAT-HAFKADA-MUTEVET` | (unmapped) | — | — |
| 8 | `REKIV-ITRA-LETKUFA` | (unmapped) | — | — |
| 8 | `SUG-ITRA-LETKUFA` | (unmapped) | — | — |
| 8 | `SACH-ITRA-LESHICHVA-BESHACH` | (unmapped) | — | — |
| 7 | `KOD-SUG-MASLUL` | (unmapped) | — | — |
| 7 | `ACHUZ-HAFKADA-LEHASHKAA` | Deposit allocation % to fund | אחוז הפקדה להשקעה | — |
| 7 | `SCHUM-TZVIRA-BAMASLUL` | (unmapped) | — | — |
| 7 | `SHEM-MASLUL-HASHKAA` | (unmapped) | — | — |
| 7 | `SHEUR-DMEI-NIHUL-HISACHON` | (unmapped) | — | — |
| 7 | `SHEUR-DMEI-NIHUL-HAFKADA-MIVNE` | (unmapped) | — | — |
| 7 | `SHEUR-DMEI-NIHUL-HISACHON-MIVNE` | (unmapped) | — | — |
| 7 | `TSUA-NETO` | (unmapped) | — | — |
| 7 | `KOD-MASLUL-HASHKAA` | (unmapped) | — | — |
| 7 | `SHIUR-ALUT-SHNATIT-ZPUIA-LMSLUL-HASHKAH` | (unmapped) | — | — |
| 7 | `KOD-SUG-PEULA` | (unmapped) | — | — |
| 7 | `RACHIV-NIMSHACH-NUYAD` | (unmapped) | — | — |
| 7 | `SCHOOM-MESHICHA-NIUD` | (unmapped) | — | — |
| 7 | `TAARICH-BIZOA` | (unmapped) | — | — |
| 7 | `TAARICH-ERECH` | (unmapped) | — | — |
| 7 | `KNAS-MESHICHA-NIUD` | Early withdrawal penalty | קנס משיכה ניוד | — |
| 7 | `KOD-MEZAHE-KOPA-MEKABELET` | (unmapped) | — | — |
| 7 | `SHEM-KOPA-MEKABELET` | (unmapped) | — | — |
| 7 | `ILAT-HAAVARA` | (unmapped) | — | — |
| 7 | `MOED-KOVEA` | (unmapped) | — | — |
| 6 | `KOD-MEZAHE-METAFEL` | (unmapped) | — | — |
| 6 | `KOD-MEZAHE-YATZRAN` | Insurer code | קוד מזהה יצרן | — |
| 6 | `ASMACHTA-MEKORIT` | Origin reference | אסמכתא מקורית | — |
| 6 | `MISPAR-POLISA-O-HESHBON` | Policy/account number | מספר פוליסה או חשבון | fund_policy_number |
| 6 | `SHEM-TOCHNIT` | Plan name | שם תוכנית | product |
| 6 | `KIDOD-ACHID` | Unified identifier | קידוד אחיד | — |
| 6 | `MPR-MEFITZ-BE-YATZRAN` | (unmapped) | — | — |
| 6 | `TAARICH-NECHONUT` | Valuation date | תאריך נכונות | — |
| 6 | `TAARICH-HITZTARFUT-MUTZAR` | (unmapped) | — | — |
| 6 | `TAARICH-HITZTARFUT-RISHON` | First enrollment date | תאריך הצטרפות ראשון | sign_date |
| 6 | `SUG-KEREN-PENSIA` | (unmapped) | — | — |
| 6 | `PENSIA-VATIKA-O-HADASHA` | (unmapped) | — | — |
| 6 | `TAARICH-IDKUN-STATUS` | Status update date | תאריך עדכון סטטוס | — |
| 6 | `STATUS-POLISA-O-CHESHBON` | Policy status code | סטטוס פוליסה/חשבון | product_status |
| 6 | `MEVUTACH` | (unmapped) | — | — |
| 6 | `TAARICH-TCHILA-RISK-ZMANI` | (unmapped) | — | — |
| 6 | `TOM-TOKEF-RISK-ZMANI` | (unmapped) | — | — |
| 6 | `SUG-POLISA` | (unmapped) | — | — |
| 6 | `MADAD-BASIS` | (unmapped) | — | — |
| 6 | `AZMADA-LEALVAHA` | (unmapped) | — | — |
| 6 | `TAARICH-ACHRON-MOTAV-MUVET` | (unmapped) | — | — |
| 6 | `KOLEL-ZAKAUT-AGACH` | (unmapped) | — | — |
| 6 | `SHIOR-AGACH-MEUADOT` | (unmapped) | — | — |
| 6 | `TAARICH-CIUM-AVTACHT-TESOA` | (unmapped) | — | — |
| 6 | `MISPAR-GIMLAOT` | (unmapped) | — | — |
| 6 | `TIKUN-190` | (unmapped) | — | — |
| 6 | `KAYAM-KISUY-HIZONI` | (unmapped) | — | — |
| 6 | `KISUY-ISHY-KVOZATI` | (unmapped) | — | — |
| 6 | `KOD-ZIHUY-LAKOACH` | (unmapped) | — | — |
| 6 | `NetuneiSheerim` | (unmapped) | — | — |
| 6 | `MASLUL-BITUACH-BAKEREN-PENSIA` | (unmapped) | — | — |
| 6 | `SHEM-MASLUL-HABITUAH` | (unmapped) | — | — |
| 6 | `HUTAL-SHIABUD` | (unmapped) | — | — |
| 6 | `HUTAL-IKUL` | (unmapped) | — | — |
| 6 | `YESH-HALVAA-BAMUTZAR` | (unmapped) | — | — |
| 6 | `RAMAT-HALVAA` | (unmapped) | — | — |
| 6 | `MISDAR-SIDURI-SHEL-HAHALVAA` | (unmapped) | — | — |
| 6 | `SCHUM-HALVAA` | (unmapped) | — | — |
| 6 | `TAARICH-KABALAT-HALVAA` | (unmapped) | — | — |
| 6 | `TAARICH-SIYUM-HALVAA` | (unmapped) | — | — |
| 6 | `YITRAT-HALVAA` | (unmapped) | — | — |
| 6 | `TKUFAT-HALVAA` | (unmapped) | — | — |
| 6 | `RIBIT` | (unmapped) | — | — |
| 6 | `SUG-RIBIT` | (unmapped) | — | — |
| 6 | `SUG-HATZNMADA` | (unmapped) | — | — |
| 6 | `TADIRUT-HECHZER-HALVAA` | (unmapped) | — | — |
| 6 | `SUG-HECHZER` | (unmapped) | — | — |
| 6 | `SCHUM-HECHZER-TKUFATI` | (unmapped) | — | — |
| 6 | `YESH-TVIA` | (unmapped) | — | — |
| 6 | `MISPAR-TVIA-BE-YATZRAN` | (unmapped) | — | — |
| 6 | `SHEM-KISUI-BE-YATZRAN` | (unmapped) | — | — |
| 6 | `SUG-HATVIAA` | (unmapped) | — | — |
| 6 | `OFEN-TASHLUM` | (unmapped) | — | — |
| 6 | `KOD-STATUS-TVIAA` | (unmapped) | — | — |
| 6 | `TAARICH-STATUS-TVIA` | (unmapped) | — | — |
| 6 | `TAARICH-TECHILAT-TASHLUM` | (unmapped) | — | — |
| 6 | `ACHUZ-MEUSHAR-O-K-A-SHICHRUR` | (unmapped) | — | — |
| 6 | `SCHUM-TVIA-MEUSHAR` | (unmapped) | — | — |
| 6 | `ACHUZ-NECHUT` | (unmapped) | — | — |
| 6 | `KAYAM-KISUY-BITUCHI-COLECTIVI-LEAMITIM` | (unmapped) | — | — |
| 6 | `SHEM-MEVATACHAT` | (unmapped) | — | — |
| 6 | `TAARICH-TCHILAT-HABITUACH` | (unmapped) | — | — |
| 6 | `TAARICH-TOM-TKUFAT-HABITUAH` | (unmapped) | — | — |
| 6 | `KOD-SUG-MUTZAR-BITUACH` | (unmapped) | — | — |
| 6 | `ALUT-KISUI` | (unmapped) | — | — |
| 6 | `MESHALEM-DMEI-HABITUAH` | (unmapped) | — | — |
| 6 | `TADIRUT-HATSHLUM` | (unmapped) | — | — |
| 6 | `HAIM-NECHTAM-TOFES-HITZTARFUT` | (unmapped) | — | — |
| 6 | `GIL-PRISHA` | (unmapped) | — | — |
| 6 | `TOTAL-CHISACHON-MITZTABER-TZAFUY` | (unmapped) | — | — |
| 6 | `TZVIRAT-CHISACHON-CHAZUYA-LELO-PREMIYOT` | (unmapped) | — | — |
| 6 | `MEKADEM-MOVTACH-LEPRISHA` | (unmapped) | — | — |
| 6 | `MEKADEM-HAVTACHST-TOCHELET` | (unmapped) | — | — |
| 6 | `MEKADEM-HAVTACHST-TOCHELETPRISHA` | (unmapped) | — | — |
| 6 | `SHEM-MASLOL` | (unmapped) | — | — |
| 6 | `MEKADEM-HAVTACHAT-TSUA` | (unmapped) | — | — |
| 6 | `MEKADEM-HAVTACHAT-TSUATKUFA` | (unmapped) | — | — |
| 6 | `TKUFAT-HAGBALA-BESHANIM` | (unmapped) | — | — |
| 6 | `TOCHELET-MASHPIA-KITZBA` | (unmapped) | — | — |
| 6 | `TSUA-MASHPIA-KITZBA` | (unmapped) | — | — |
| 6 | `SHEUR-PNS-ZIKNA-TZFUYA` | (unmapped) | — | — |
| 6 | `SUG-KUPA` | (unmapped) | — | — |
| 6 | `SCHUM-KITZVAT-ZIKNA` | (unmapped) | — | — |
| 6 | `KITZVAT-HODSHIT-TZFUYA` | (unmapped) | — | — |
| 6 | `ACHUZ-TSUA-BATACHAZIT` | Yield % attributed to insurance | אחוז תשואה בתחזית | — |
| 6 | `TOTAL-ITRA-TZFUYA-MECHUSHAV-LEHON-IM-PREMIOT` | (unmapped) | — | — |
| 6 | `TZVIRAT-CHISACHON-TZFUYA-LEHON-LELO-PREMIYOT` | (unmapped) | — | — |
| 6 | `TOTAL-SCHUM-MTZBR-TZAFUY-LEGIL-PRISHA-MECHUSHAV-LEKITZBA-IM-PREMIYOT` | (unmapped) | — | — |
| 6 | `TOTAL-SCHUM-MITZVTABER-TZFUY-LEGIL-PRISHA-MECHUSHAV-HAMEYOAD-LEKITZBA-LELO-PREMIYOT` | (unmapped) | — | — |
| 6 | `SHEUR-TSUA-NETO` | Net yield % | שיעור תשואה נטו | — |
| 6 | `SHEUR-TSUA-BRUTO-CHS-1` | Gross yield % (calc 1) | שיעור תשואה ברוטו חישוב 1 | — |
| 6 | `SHEUR-TSUA-MOVTACHAT-MEYOADOT` | (unmapped) | — | — |
| 6 | `REVACH-HEFSED-BENIKOI-HOZAHOT` | P/L after deductions | רווח/הפסד בניכוי הוצאות | — |
| 6 | `SIMAN-REVACH-HEFSED` | P/L sign indicator | סימן רווח/הפסד | — |
| 6 | `ACHUZ-TSUA-BRUTO-CHS-2` | (unmapped) | — | — |
| 6 | `ACHUZ-TSUA-MUVTAHT` | (unmapped) | — | — |
| 6 | `STATUS-MAASIK` | (unmapped) | — | — |
| 6 | `SUG-BAAL-HAPOLISA-SHE-EINO-HAMEVUTACH` | (unmapped) | — | — |
| 6 | `MISPAR-BAAL-POLISA-SHEEINO-MEVUTAH` | (unmapped) | — | — |
| 6 | `SHEM-BAAL-POLISA-SHEEINO-MEVUTAH` | (unmapped) | — | — |
| 6 | `KOD-CHISHUV-SACHAR-POLISA-O-HESHBON` | (unmapped) | — | — |
| 6 | `SACHAR-POLISA` | (unmapped) | — | — |
| 6 | `KOD-OFEN-HATZMADA` | (unmapped) | — | — |
| 6 | `TAARICH-MASKORET` | (unmapped) | — | — |
| 6 | `ZAKAUT-LELO-TNAI` | (unmapped) | — | — |
| 6 | `SEIF-14` | (unmapped) | — | — |
| 6 | `TAARICH-TCHILAT-TASHLUM` | (unmapped) | — | — |
| 6 | `SUG-HAMAFKID` | (unmapped) | — | — |
| 6 | `ACHUZ-HAFRASHA` | (unmapped) | — | — |
| 6 | `SCHUM-HAFRASHA` | (unmapped) | — | — |
| 6 | `TAARICH-MADAD` | (unmapped) | — | — |
| 6 | `SHEM-MESHALEM` | (unmapped) | — | — |
| 6 | `SUG-TEUDA-MESHALEM` | (unmapped) | — | — |
| 6 | `MISPAR-ZIHUY-MESHALEM` | (unmapped) | — | — |
| 6 | `KOD-EMTZAEI-TASHLUM` | (unmapped) | — | — |
| 6 | `TADIRUT-TASHLUM` | (unmapped) | — | — |
| 6 | `CHODESH-YECHUS` | (unmapped) | — | — |
| 6 | `YOM-GVIYA-BECHODESH` | (unmapped) | — | — |
| 6 | `OFEN-HATZMADAT-GVIA` | (unmapped) | — | — |
| 6 | `ACHUZ-TAT-SHNATIYOT` | (unmapped) | — | — |
| 6 | `TOTAL-HAFKADOT-OVED-TAGMULIM-SHANA-NOCHECHIT` | (unmapped) | — | — |
| 6 | `TOTAL-HAFKADOT-MAAVID-TAGMULIM-SHANA-NOCHECHIT` | (unmapped) | — | — |
| 6 | `TOTAL-HAFKADOT-PITZUIM-SHANA-NOCHECHIT` | (unmapped) | — | — |
| 6 | `KAYAM-CHOV-O-PIGUR` | Has outstanding debt / arrears | קיים חוב או פיגור | — |
| 6 | `TAARICH-TECHILAT-PIGUR` | (unmapped) | — | — |
| 6 | `TAARICH-TECHILAT-PIGUR-NOCHECHI` | (unmapped) | — | — |
| 6 | `MISPAR-CHODSHEI-PIGUR` | (unmapped) | — | — |
| 6 | `SUG-HOV` | (unmapped) | — | — |
| 6 | `TOTAL-CHOVOT-O-PIGURIM` | (unmapped) | — | — |
| 6 | `KSAFIM-LO-MESHUYACHIM-MAASIK` | (unmapped) | — | — |
| 6 | `TOTAL-DMEI-NIHUL-HAFKADA` | (unmapped) | — | — |
| 6 | `SHEUR-DMEI-NIHUL-TZVIRA` | (unmapped) | — | — |
| 6 | `TOTAL-DMEI-NIHUL-TZVIRA` | (unmapped) | — | — |
| 6 | `SACH-DMEI-NIHUL-ACHERIM` | (unmapped) | — | — |
| 6 | `HOTZOT-NIHUL-ASHKAOT` | (unmapped) | — | — |
| 6 | `TOTAL-DMEI-NIHUL-POLISA-O-HESHBON` | (unmapped) | — | — |
| 6 | `DEMI-AAVARAT-MASLOL` | (unmapped) | — | — |
| 6 | `DMEI-NIUL-MENAEL-TIKIM` | (unmapped) | — | — |
| 6 | `MEMOTZA-SHEUR-DMEI-NIHUL-HAFKADA` | (unmapped) | — | — |
| 6 | `MEMOTZA-TOTAL-DMEI-NIHUL-HAFKADA` | (unmapped) | — | — |
| 6 | `OFEN-GEVIAT-DMEI-BITUACH` | (unmapped) | — | — |
| 6 | `SACH-DMEI-BITUAH-SHENIGBOO` | (unmapped) | — | — |
| 6 | `YITRAT-SOF-SHANA` | (unmapped) | — | — |
| 6 | `ERECH-PIDYON-SOF-SHANA` | Year-end surrender value | ערך פדיון סוף שנה | — |
| 6 | `ERECH-MESOLAK-SOF-SHANA` | Year-end market value | ערך מסולק סוף שנה | accumulation |
| 6 | `YISKON-YITRAT-KESAFIM` | (unmapped) | — | — |
| 6 | `TAARICH-ERECH-TZVIROT` | (unmapped) | — | — |
| 6 | `KOD-SUG-ITRA` | (unmapped) | — | — |
| 6 | `TOTAL-CHISACHON-MTZBR` | (unmapped) | — | — |
| 6 | `TOTAL-ERKEI-PIDION` | (unmapped) | — | — |
| 6 | `TZVIRAT-PITZUIM-PTURIM-MAAVIDIM-KODMIM` | (unmapped) | — | — |
| 6 | `ERECH-PIDION-PITZUIM-LEKITZBA-MAAVIDIM-KODMIM` | (unmapped) | — | — |
| 6 | `TZVIRAT-PITZUIM-MAAVIDIM-KODMIM-BERETZEF-KITZBA` | (unmapped) | — | — |
| 6 | `TZVIRAT-PITZUIM-MAAVIDIM-KODMIM-BERETZEF-ZECHUYOT` | (unmapped) | — | — |
| 6 | `TZVIRAT-PITZUIM-31-12-1999-LEKITZBA` | (unmapped) | — | — |
| 6 | `ERECH-PIDION-PITZUIM-MAASIK-NOCHECHI` | (unmapped) | — | — |
| 6 | `ERECH-PIDION-MARKIV-PITZUIM-LEMAS-NOCHECHI` | (unmapped) | — | — |
| 6 | `ERECH-PIDION-PITZUIM-MAAVIDIM-KODMIM-RETZEF-ZEHUYUT` | (unmapped) | — | — |
| 6 | `ERECH-PIDION-PITZUIM-LEHON-MAAVIDIM-KODMIM` | (unmapped) | — | — |
| 6 | `YITRAT-PITZUIM-LELO-HITCHASHBENOT` | (unmapped) | — | — |
| 6 | `KAYAM-RETZEF-PITZUIM-KITZBA` | Has scheduled pension sequence | קיים רצף פיצויים קצבה | — |
| 6 | `KAYAM-RETZEF-ZECHUYOT-PITZUIM` | (unmapped) | — | — |
| 6 | `KAYAM-MEYUPE-KOACH` | Has power of attorney | קיים מיופה כוח | — |
| 6 | `SUG-ZIHUY` | (unmapped) | — | — |
| 6 | `MEYOPE-ZIHUY` | (unmapped) | — | — |
| 6 | `HARSHAA-LEBITZUAE-PEULA` | (unmapped) | — | — |
| 6 | `TAARICH-MINUY-SOCHEN` | (unmapped) | — | — |
| 6 | `SHEM-MEYUPE-KOACH` | (unmapped) | — | — |
| 6 | `TAARICH-TOM-TOKEF-YEPUI-KOACH` | (unmapped) | — | — |
| 6 | `KOD-MUTZAR-LEFI-KIDUD-ACHID-LAYESODI` | (unmapped) | — | — |
| 6 | `SUG-HATZMADA-SCHUM-BITUAH` | (unmapped) | — | — |
| 6 | `SUG-HATZMADA-DMEI-BITUAH` | (unmapped) | — | — |
| 6 | `SUG-MASLUL-LEBITUAH` | (unmapped) | — | — |
| 6 | `IND-SCHUM-BITUAH-KOLEL-CHISACHON` | Premium includes savings (ind.) | אינד: סכום ביטוח כולל חיסכון | — |
| 6 | `SCHUM-BITUACH-LEMASLUL` | (unmapped) | — | — |
| 6 | `MISPAR-MASKOROT` | (unmapped) | — | — |
| 6 | `ACHUZ-HAKTZAA-LE-CHISACHON` | Savings allocation % | אחוז הקצאה לחיסכון | — |
| 6 | `TIKRAT-GAG-HATAM-LEMIKRE-MAVET` | (unmapped) | — | — |
| 6 | `SCHUM-BITUAH-LEMAVET` | (unmapped) | — | — |
| 6 | `SHEUR-BITUH-ZFOY` | (unmapped) | — | — |
| 6 | `SCHUM-BITUH-ZFOY` | (unmapped) | — | — |
| 5 | `KOD-NIMAAN` | (unmapped) | — | — |
| 5 | `SUG-MEZAHE-NIMAAN` | (unmapped) | — | — |
| 5 | `MISPAR-ZIHUI-NIMAAN` | (unmapped) | — | — |
| 5 | `MISPAR-ZIHUI-ETZEL-YATZRAN-NIMAAN` | (unmapped) | — | — |
| 5 | `SUG-MUTZAR` | Product type | סוג מוצר | product_type |
| 5 | `SHEM-KOVETZ-MEKORI` | (unmapped) | — | — |
| 5 | `MISPAR-SHURA-MEKORI` | (unmapped) | — | — |
| 5 | `RESERVA-MISLAKA` | (unmapped) | — | — |
| 5 | `MISPAR-MISLAKA` | (unmapped) | — | — |
| 5 | `STATUS-RESHOMA` | (unmapped) | — | — |
| 5 | `MISPAR-SHORA` | (unmapped) | — | — |
| 5 | `TOTAL-ZEHUT-PER-MONTH` | (unmapped) | — | — |
| 5 | `TOTAL-MUTZARIM-PER-MONTH` | (unmapped) | — | — |
| 5 | `SUG-MEZAHE-MAASIK` | (unmapped) | — | — |
| 5 | `MISPAR-MEZAHE-MAASIK` | (unmapped) | — | — |
| 5 | `MISPAR-TIK-NIKUIIM` | (unmapped) | — | — |
| 5 | `SHEM-MAASIK` | (unmapped) | — | — |
| 5 | `SUG-MEZAHE-LAKOACH` | Customer ID type | סוג מזהה לקוח | — |
| 5 | `SHEM-MISHPACHA-KODEM` | (unmapped) | — | — |
| 5 | `MIN` | Gender | מין | — |
| 5 | `TAARICH-LEYDA` | Date of birth | תאריך לידה | — |
| 5 | `PTIRA` | (unmapped) | — | — |
| 5 | `TAARICH-PTIRA` | (unmapped) | — | — |
| 5 | `MATZAV-MISHPACHTI` | Marital status | מצב משפחתי | — |
| 5 | `MISPAR-YELADIM` | (unmapped) | — | — |
| 4 | `PirteiHafkadaAchrona` | (unmapped) | — | — |
| 2 | `TAARICH-HAFKADA-ACHARON` | (unmapped) | — | — |
| 2 | `TOTAL-HAFKADA` | (unmapped) | — | — |
| 2 | `HAFKADA-LEHISCHON-A` | (unmapped) | — | — |
| 2 | `HAFKADA-LEHISCHON-B` | (unmapped) | — | — |
| 2 | `SUG-HAFKADA` | (unmapped) | — | — |
| 2 | `TOTAL-HAFKADA-ACHRONA` | (unmapped) | — | — |
| 1 | `SUG-MIMSHAK` | Mimshak type | סוג ממשק | — |
| 1 | `MISPAR-GIRSAT-XML` | XML version | מספר גרסת XML | — |
| 1 | `TAARICH-BITZUA` | Execution timestamp | תאריך ביצוע | — |
| 1 | `KOD-SVIVAT-AVODA` | (unmapped) | — | — |
| 1 | `KIVUN-MIMSHAK-XML` | (unmapped) | — | — |
| 1 | `KOD-SHOLEACH` | Sender code | קוד שולח | — |
| 1 | `SHEM-SHOLEACH` | Sender name | שם שולח | — |
| 1 | `SHEM-METAFEL` | (unmapped) | — | — |
| 1 | `MEZAHE-HAAVARA` | Transfer identifier | מזהה העברה | — |
| 1 | `MISPAR-HAKOVETZ` | File number | מספר הקובץ | — |
| 1 | `SHEM-YATZRAN` | Insurer name | שם יצרן | receiving_company |
| 1 | `MEZAHE-LAKOACH-MISLAKA` | (unmapped) | — | — |
| 1 | `KAMUT-YATZRANIM` | (unmapped) | — | — |
| 1 | `KAMUT-METAFELIM` | (unmapped) | — | — |
| 1 | `KAMUT-MUTZARIM` | (unmapped) | — | — |
| 1 | `KAMUT-YESHUYOT-MAASIK` | (unmapped) | — | — |
| 1 | `KAMUT-YESHUYOT-MEFITZ` | (unmapped) | — | — |
| 1 | `MISPAR-YESHUYUT-LAKOACH-BAKOVETZ` | (unmapped) | — | — |
| 1 | `KAMUT-POLISOT` | (unmapped) | — | — |

## Section B · Data present in DAT but NOT in any current Excel parser

Elements mapped to `ClientRecord` columns that `record.py` does have — but also rich structures (per-policy beneficiaries, fund allocations, yield history) that the flat schema cannot hold.

### Rich structures (need child tables or JSON column)

- Per-policy **beneficiaries** — name, DOB, national ID, % share, relationship code
- Per-policy **fund allocations** — fund code, name, deposit %, holding %
- Per-policy **deposit history** — `PerutHafkadotMetchilatShana`
- Per-policy **loans** — `Halvaa` block (amount, rate, status)
- Per-coverage **rider lifecycle** — start/end dates, insurer label, type code
- Per-coverage **premium history** — `hitpatchutpremia`

### Flat fields not in any Excel parser today

- `SHEM-YISHUV` — City name (שם יישוב)
- `SHEM-RECHOV` — Street (שם רחוב)
- `MIKUD` — Zip code (מיקוד)
- `MIN` — Gender (מין)
- `TAARICH-LEYDA` — Date of birth (תאריך לידה)
- `MATZAV-MISHPACHTI` — Marital status (מצב משפחתי)
- `TAARICH-NECHONUT` — Valuation date (תאריך נכונות)
- `TAARICH-IDKUN-STATUS` — Status update date (תאריך עדכון סטטוס)
- `SHEUR-TSUA-NETO` — Net yield % (שיעור תשואה נטו)
- `SHEUR-TSUA-BRUTO-CHS-1` — Gross yield % (calc 1) (שיעור תשואה ברוטו חישוב 1)
- `REVACH-HEFSED-BENIKOI-HOZAHOT` — P/L after deductions (רווח/הפסד בניכוי הוצאות)
- `SIMAN-REVACH-HEFSED` — P/L sign indicator (סימן רווח/הפסד)
- `KAYAM-CHOV-O-PIGUR` — Has outstanding debt / arrears (קיים חוב או פיגור)
- `GOVA-DMEI-NIHUL-NIKBA-AL-PI-HOTZAOT-BAPOAL` — Actual mgmt fee charged (גובה דמי ניהול שנגבה)
- `ERECH-PIDYON-SOF-SHANA` — Year-end surrender value (ערך פדיון סוף שנה)
- `KAYAM-MEYUPE-KOACH` — Has power of attorney (קיים מיופה כוח)
- `IND-SCHUM-BITUAH-KOLEL-CHISACHON` — Premium includes savings (ind.) (אינד: סכום ביטוח כולל חיסכון)
- `BITUL-KIZUZ-MEMSHALTI` — Gov fee discount (Y/N) (ביטול קיזוז ממשלתי)
- `SACHAR-BERAMAT-HAFKADA` — Fee charged on deposit (שכר ברמת הפקדה)

### Unmapped XML elements

Elements we encountered in the sample but haven't yet catalogued in `xml_fields.py`. Inspect these to decide whether they're informational plumbing or data worth capturing.

- `ACHUZ-HAFRASHA` (6×)
- `ACHUZ-HAGDALAT-GAG-HATAM-O-K-A` (9×)
- `ACHUZ-ME-SCM-BTH-YESODI` (9×)
- `ACHUZ-MESACHAR` (9×)
- `ACHUZ-MEUSHAR-O-K-A-SHICHRUR` (6×)
- `ACHUZ-NECHUT` (6×)
- `ACHUZ-TAT-SHNATIYOT` (6×)
- `ACHUZ-TSUA-BRUTO-CHS-2` (6×)
- `ACHUZ-TSUA-MUVTAHT` (6×)
- `ALUT-KISUI` (6×)
- `AZMADA-LEALVAHA` (6×)
- `CHODESH-SACHAR` (15×)
- `CHODESH-YECHUS` (6×)
- `DEMI-AAVARAT-MASLOL` (6×)
- `DMEI-NIUL-MENAEL-TIKIM` (6×)
- `ERECH-PIDION-MARKIV-PITZUIM-LEMAS-NOCHECHI` (6×)
- `ERECH-PIDION-PITZUIM-LEHON-MAAVIDIM-KODMIM` (6×)
- `ERECH-PIDION-PITZUIM-LEKITZBA-MAAVIDIM-KODMIM` (6×)
- `ERECH-PIDION-PITZUIM-MAASIK-NOCHECHI` (6×)
- `ERECH-PIDION-PITZUIM-MAAVIDIM-KODMIM-RETZEF-ZEHUYUT` (6×)
- `GIL-PRISHA` (6×)
- `HACHRAGA` (9×)
- `HAFKADA-LEHISCHON-A` (2×)
- `HAFKADA-LEHISCHON-B` (2×)
- `HAIM-NECHTAM-TOFES-HITZTARFUT` (6×)
- `HANACHA` (9×)
- `HANACHA-MEDUREGET` (9×)
- `HARSHAA-LEBITZUAE-PEULA` (6×)
- `HATNAYA-LAHANACHA-DMEI-BITUAH` (9×)
- `HEAROT` (16×)
- `HOTZOT-NIHUL-ASHKAOT` (6×)
- `HUTAL-IKUL` (6×)
- `HUTAL-SHIABUD` (6×)
- `ILAT-HAAVARA` (7×)
- `IND-CHITUM` (9×)
- `KAMUT-METAFELIM` (1×)
- `KAMUT-MUTZARIM` (1×)
- `KAMUT-POLISOT` (1×)
- `KAMUT-YATZRANIM` (1×)
- `KAMUT-YESHUYOT-MAASIK` (1×)
- `KAMUT-YESHUYOT-MEFITZ` (1×)
- `KAYAM-KISUY-BITUCHI-COLECTIVI-LEAMITIM` (6×)
- `KAYAM-KISUY-HIZONI` (6×)
- `KAYAM-RETZEF-ZECHUYOT-PITZUIM` (6×)
- `KAYEMET-HATAVA` (8×)
- `KENAS-MESHICHAT-KESAFIM` (8×)
- `KISUY-ISHY-KVOZATI` (6×)
- `KITZBA-ZMUDA-LAMADAD` (9×)
- `KITZVAT-HODSHIT-TZFUYA` (6×)
- `KIVUN-MIMSHAK-XML` (1×)
- `KOD-CHISHUV-SACHAR-POLISA-O-HESHBON` (6×)
- `KOD-EMTZAEI-TASHLUM` (6×)
- `KOD-ISHUN` (9×)
- `KOD-MASLUL-DMEI-NIHUL` (8×)
- `KOD-MASLUL-HASHKAA` (7×)
- `KOD-MASLUL-HASHKAA-BAAL-DMEI-NIHUL-YECHUDIIM` (8×)
- `KOD-MEZAHE-KOPA-MAAVIRA` (13×)
- `KOD-MEZAHE-KOPA-MEKABELET` (7×)
- `KOD-MEZAHE-METAFEL` (6×)
- `KOD-MIKTZOA` (9×)
- `KOD-MIUTZAR-LAKISUY` (9×)
- `KOD-MUTZAR-LEFI-KIDUD-ACHID-LAYESODI` (6×)
- `KOD-NIMAAN` (5×)
- `KOD-NISPACH-KISUY` (9×)
- `KOD-OFEN-HATZMADA` (6×)
- `KOD-STATUS-TVIAA` (6×)
- `KOD-SUG-HAFRASHA` (13×)
- `KOD-SUG-ITRA` (6×)
- `KOD-SUG-MASLUL` (7×)
- `KOD-SUG-MUTZAR-BITUACH` (6×)
- `KOD-SUG-PEULA` (7×)
- `KOD-SVIVAT-AVODA` (1×)
- `KOD-TECHULAT-SHICHVA` (8×)
- `KOD-ZIHUY-LAKOACH` (6×)
- `KOLEL-PRENZISA` (9×)
- `KOLEL-SIUD` (9×)
- `KOLEL-ZAKAUT-AGACH` (6×)
- `KSAFIM-LO-MESHUYACHIM-MAASIK` (6×)
- `MADAD-BASIS` (6×)
- `MAHUT-MUTAV` (15×)
- `MASLUL-BITUACH-BAKEREN-PENSIA` (6×)
- `MEAFYENEI-MASLUL-DMEI-NIHUL` (8×)
- `MEKADEM-HAVTACHAT-TSUA` (6×)
- `MEKADEM-HAVTACHAT-TSUATKUFA` (6×)
- `MEKADEM-HAVTACHST-TOCHELET` (6×)
- `MEKADEM-HAVTACHST-TOCHELETPRISHA` (6×)
- `MEKADEM-MOVTACH-LEPRISHA` (6×)
- `MEMOTZA-SHEUR-DMEI-NIHUL-HAFKADA` (6×)
- `MEMOTZA-TOTAL-DMEI-NIHUL-HAFKADA` (6×)
- `MESHALEM-DMEI-HABITUAH` (6×)
- `MESHALEM-HAKISUY` (9×)
- `MEVUTACH` (6×)
- `MEYOPE-ZIHUY` (6×)
- `MEZAHE-LAKOACH-MISLAKA` (1×)
- `MISDAR-SIDURI-SHEL-HAHALVAA` (6×)
- `MISPAR-BAAL-POLISA-SHEEINO-MEVUTAH` (6×)
- `MISPAR-CHODSHEI-PIGUR` (6×)
- `MISPAR-GIMLAOT` (6×)
- `MISPAR-KISUI-BE-YATZRAN` (15×)
- `MISPAR-MASKOROT` (6×)
- `MISPAR-MEZAHE-MAASIK` (5×)
- `MISPAR-MISLAKA` (5×)
- `MISPAR-POLISA-O-HESHBON-NEGDI` (9×)
- `MISPAR-SHLUCHA` (11×)
- `MISPAR-SHORA` (5×)
- `MISPAR-SHURA-MEKORI` (5×)
- `MISPAR-TIK-NIKUIIM` (5×)
- `MISPAR-TVIA-BE-YATZRAN` (6×)
- `MISPAR-YELADIM` (5×)
- `MISPAR-YESHUYUT-LAKOACH-BAKOVETZ` (1×)
- `MISPAR-ZIHUI-ETZEL-YATZRAN-NIMAAN` (5×)
- `MISPAR-ZIHUI-NIMAAN` (5×)
- `MISPAR-ZIHUY` (12×)
- `MISPAR-ZIHUY-MESHALEM` (6×)
- `MOED-KOVEA` (7×)
- `MOED-KOVEA-NIUD` (13×)
- `MOED-SIUM-TKUFAT-HANACHA` (9×)
- `MPR-MAASIK-BE-YATZRAN` (11×)
- `MPR-MEFITZ-BE-YATZRAN` (6×)
- `NACHUT-MITPATAHAT` (9×)
- `NetuneiSheerim` (6×)
- `OFEN-GEVIAT-DMEI-BITUACH` (6×)
- `OFEN-HAFRASHA` (8×)
- `OFEN-HATZMADAT-GVIA` (6×)
- `OFEN-TASHLUM` (6×)
- `OFEN-TASHLUM-SCHUM-BITUACH` (9×)
- `PENSIA-VATIKA-O-HADASHA` (6×)
- `PREMIA-ZFOYA` (15×)
- `PROMIL-TOSEFET` (9×)
- `PTIRA` (5×)
- `PirteiHafkadaAchrona` (4×)
- `RACHIV-NIMSHACH-NUYAD` (7×)
- `RAMAT-HALVAA` (6×)
- `REKIV-ITRA-LETKUFA` (8×)
- `RESERVA-MISLAKA` (5×)
- `RIBIT` (6×)
- `SACH-DMEI-BITUAH-SHENIGBOO` (6×)
- `SACH-DMEI-NIHUL-ACHERIM` (6×)
- `SACH-DMEI-NIHUL-MASLUL` (8×)
- `SACH-ITRA-LESHICHVA-BESHACH` (8×)
- `SACHAR-POLISA` (6×)
- `SCHOOM-MESHICHA-NIUD` (7×)
- `SCHUM-BITUACH-LEMASLUL` (6×)
- `SCHUM-BITUAH-LEMAVET` (6×)
- `SCHUM-BITUH-KAVOA-MISHTANE` (9×)
- `SCHUM-BITUH-ZFOY` (6×)
- `SCHUM-HAFRASHA` (6×)
- `SCHUM-HALVAA` (6×)
- `SCHUM-HECHZER-TKUFATI` (6×)
- `SCHUM-KITZVAT-ZIKNA` (6×)
- `SCHUM-MAX-DNHL-HAFKADA` (8×)
- `SCHUM-SHEUR` (9×)
- `SCHUM-TVIA-MEUSHAR` (6×)
- `SCHUM-TZVIRA-BAMASLUL` (7×)
- `SEIF-14` (6×)
- `SHEM-BAAL-POLISA-SHEEINO-MEVUTAH` (6×)
- `SHEM-KISUI-BE-YATZRAN` (6×)
- `SHEM-KOPA-MAAVIRA` (13×)
- `SHEM-KOPA-MEKABELET` (7×)
- `SHEM-KOVETZ-MEKORI` (5×)
- `SHEM-MAASIK` (5×)
- `SHEM-MASLOL` (6×)
- `SHEM-MASLUL-HABITUAH` (6×)
- `SHEM-MASLUL-HASHKAA` (7×)
- `SHEM-MESHALEM` (6×)
- `SHEM-METAFEL` (1×)
- `SHEM-MEVATACHAT` (6×)
- `SHEM-MEYUPE-KOACH` (6×)
- `SHEM-MISHPACHA-KODEM` (5×)
- `SHEUR-BITUH-KAVOA-MISHTANE` (9×)
- `SHEUR-BITUH-ZFOY` (6×)
- `SHEUR-DMEI-NIHUL` (8×)
- `SHEUR-DMEI-NIHUL-HAFKADA` (13×)
- `SHEUR-DMEI-NIHUL-HAFKADA-MIVNE` (7×)
- `SHEUR-DMEI-NIHUL-HISACHON` (7×)
- `SHEUR-DMEI-NIHUL-HISACHON-MIVNE` (7×)
- `SHEUR-DMEI-NIHUL-TZVIRA` (6×)
- `SHEUR-PNS-ZIKNA-TZFUYA` (6×)
- `SHEUR-TOSEFET` (9×)
- `SHEUR-TSUA-MOVTACHAT-MEYOADOT` (6×)
- `SHIOR-AGACH-MEUADOT` (6×)
- `SHIUR-ALUT-SHNATIT-ZPUIA-LMSLUL-HASHKAH` (7×)
- `SHIUR-HANACHA-BEKISUI` (9×)
- `STATUS-MAASIK` (6×)
- `STATUS-RESHOMA` (5×)
- `SUG-BAAL-HAPOLISA-SHE-EINO-HAMEVUTACH` (6×)
- `SUG-HACHRAGA` (9×)
- `SUG-HAFKADA` (2×)
- `SUG-HAFRASHA` (21×)
- `SUG-HAMAFKID` (6×)
- `SUG-HANACHA-KISUY` (9×)
- `SUG-HATAVA` (8×)
- `SUG-HATVIAA` (6×)
- `SUG-HATZMADA-DMEI-BITUAH` (6×)
- `SUG-HATZMADA-SCHUM-BITUAH` (6×)
- `SUG-HATZNMADA` (6×)
- `SUG-HECHZER` (6×)
- `SUG-HOTZAA` (8×)
- `SUG-HOV` (6×)
- `SUG-ISUK` (9×)
- `SUG-ITRA-LETKUFA` (8×)
- `SUG-KEREN-PENSIA` (6×)
- `SUG-KISUY-BITOCHI` (9×)
- `SUG-KUPA` (6×)
- `SUG-MAFKID` (15×)
- `SUG-MASLUL-LEBITUAH` (6×)
- `SUG-MEVUTACH` (9×)
- `SUG-MEZAHE-MAASIK` (5×)
- `SUG-MEZAHE-NIMAAN` (5×)
- `SUG-POLISA` (6×)
- `SUG-RIBIT` (6×)
- `SUG-TEUDA` (9×)
- `SUG-TEUDA-MESHALEM` (6×)
- `SUG-TOCHNIT-O-CHESHBON` (12×)
- `SUG-ZIHUY` (6×)
- `SUG-ZIHUY-MUTAV` (15×)
- `TAARICH-ACHRON-MOTAV-MUVET` (6×)
- `TAARICH-BIZOA` (7×)
- `TAARICH-CHITUM` (9×)
- `TAARICH-CIUM-AVTACHT-TESOA` (6×)
- `TAARICH-ERECH` (7×)
- `TAARICH-ERECH-TZVIROT` (6×)
- `TAARICH-HAFKADA-ACHARON` (2×)
- `TAARICH-HAFSAKAT-TASHLUM` (9×)
- `TAARICH-HITZTARFUT-MUTZAR` (6×)
- `TAARICH-IDKUN-HABA-SHEL-DMEI-HABITUAH` (9×)
- `TAARICH-IDKUN-SHEUR-DNHL` (8×)
- `TAARICH-KABALAT-HALVAA` (6×)
- `TAARICH-MADAD` (6×)
- `TAARICH-MASKORET` (6×)
- `TAARICH-MINUY-SOCHEN` (6×)
- `TAARICH-PTIRA` (5×)
- `TAARICH-SIUM-HATAVA` (8×)
- `TAARICH-SIYUM-HALVAA` (6×)
- `TAARICH-STATUS-TVIA` (6×)
- `TAARICH-TCHILA-RISK-ZMANI` (6×)
- `TAARICH-TCHILAT-HABITUACH` (6×)
- `TAARICH-TCHILAT-KISUY` (9×)
- `TAARICH-TCHILAT-TASHLUM` (6×)
- `TAARICH-TECHILAT-PIGUR` (6×)
- `TAARICH-TECHILAT-PIGUR-NOCHECHI` (6×)
- `TAARICH-TECHILAT-TASHLUM` (6×)
- `TAARICH-TOM-KISUY` (9×)
- `TAARICH-TOM-TKUFAT-HABITUAH` (6×)
- `TAARICH-TOM-TOKEF-YEPUI-KOACH` (6×)
- `TAARICH-TOM-TOSEFET` (9×)
- `TACHVIVIM-O-ISUKIM` (9×)
- `TADIRUT-HATSHLUM` (6×)
- `TADIRUT-HECHZER-HALVAA` (6×)
- `TADIRUT-SHINUY-DMEI-HABITUAH-BESHANIM` (9×)
- `TADIRUT-TASHLUM` (6×)
- `TCHILAT-TKUFA` (21×)
- `TCHUM-ISUK-CHADASH` (9×)
- `TIKRAT-GAG-HATAM-LE-O-K-A` (9×)
- `TIKRAT-GAG-HATAM-LEMIKRE-MAVET` (6×)
- `TIKRAT-HAFKADA-MUTEVET` (8×)
- `TIKUN-190` (6×)
- `TKUFAT-ACHSHARA` (9×)
- `TKUFAT-HAGBALA-BESHANIM` (6×)
- `TKUFAT-HALVAA` (6×)
- `TKUFAT-HAMTANA-CHODASHIM` (9×)
- `TNAEI-HANACHA` (9×)
- `TOCHELET-MASHPIA-KITZBA` (6×)
- `TOM-TKUFA` (21×)
- `TOM-TOKEF-RISK-ZMANI` (6×)
- `TOSEFET-TAARIF` (9×)
- `TOTAL-CHISACHON-MITZTABER-TZAFUY` (6×)
- `TOTAL-CHISACHON-MTZBR` (6×)
- `TOTAL-CHOVOT-O-PIGURIM` (6×)
- `TOTAL-DMEI-NIHUL-HAFKADA` (6×)
- `TOTAL-DMEI-NIHUL-POLISA-O-HESHBON` (6×)
- `TOTAL-DMEI-NIHUL-TZVIRA` (6×)
- `TOTAL-ERKEI-PIDION` (6×)
- `TOTAL-HAFKADA` (2×)
- `TOTAL-HAFKADA-ACHRONA` (2×)
- `TOTAL-HAFKADOT-MAAVID-TAGMULIM-SHANA-NOCHECHIT` (6×)
- `TOTAL-HAFKADOT-OVED-TAGMULIM-SHANA-NOCHECHIT` (6×)
- `TOTAL-HAFKADOT-PITZUIM-SHANA-NOCHECHIT` (6×)
- `TOTAL-ITRA-TZFUYA-MECHUSHAV-LEHON-IM-PREMIOT` (6×)
- `TOTAL-MUTZARIM-PER-MONTH` (5×)
- `TOTAL-SCHUM-MITZVTABER-TZFUY-LEGIL-PRISHA-MECHUSHAV-HAMEYOAD-LEKITZBA-LELO-PREMIYOT` (6×)
- `TOTAL-SCHUM-MTZBR-TZAFUY-LEGIL-PRISHA-MECHUSHAV-LEKITZBA-IM-PREMIYOT` (6×)
- `TOTAL-ZEHUT-PER-MONTH` (5×)
- `TSUA-MASHPIA-KITZBA` (6×)
- `TSUA-NETO` (7×)
- `TZVIRAT-CHISACHON-CHAZUYA-LELO-PREMIYOT` (6×)
- `TZVIRAT-CHISACHON-TZFUYA-LEHON-LELO-PREMIYOT` (6×)
- `TZVIRAT-PITZUIM-31-12-1999-LEKITZBA` (6×)
- `TZVIRAT-PITZUIM-MAAVIDIM-KODMIM-BERETZEF-KITZBA` (6×)
- `TZVIRAT-PITZUIM-MAAVIDIM-KODMIM-BERETZEF-ZECHUYOT` (6×)
- `TZVIRAT-PITZUIM-PTURIM-MAAVIDIM-KODMIM` (6×)
- `YESH-HALVAA-BAMUTZAR` (6×)
- `YESH-TVIA` (6×)
- `YISKON-YITRAT-KESAFIM` (6×)
- `YITRAT-HALVAA` (6×)
- `YITRAT-PITZUIM-LELO-HITCHASHBENOT` (6×)
- `YITRAT-SOF-SHANA` (6×)
- `YOM-GVIYA-BECHODESH` (6×)
- `ZAKAUT-LELO-TNAI` (6×)
- `ZMAN-PERAON` (13×)

## Section C · Recommended follow-up persist targets

Priority-ordered sketch of how the DAT could extend Nifraim's data model:

1. **Drop-in writes to `ClientRecord`** — same columns the Excel path already uses, populated from the XML's `HeshbonOPolisa` + `PERSON.MBT` enrichment. Zero schema work; replaces the SaaS middleman for `total_premium`, `accumulation`, `management_fee*`, `product`, `fund_policy_number`, `client_email`, etc.
2. **JSON extension column** (`client_records.mimshak_extras JSONB`) — capture surrender value, gross/net yield, P/L indicators, and all the flag fields (`KAYAM-*`, `IND-*`) without new tables. Queryable in Postgres via `->>` for reports.
3. **Child tables for rich structure**:
   - `policy_beneficiaries` — id, policy_id, beneficiary_id, name, dob, share_pct, relationship
   - `policy_funds` — id, policy_id, fund_code, fund_name, allocation_pct, holding_pct
   - `policy_yield_history` — id, policy_id, period, gross_pct, net_pct, p_and_l
   Only worth it once the UI needs to surface this data.
4. **Ingestion UX** — zip upload (all files in one go). The DAT filename (`…HOLDNGINP009….DAT`) encodes sender + timestamp, so we can dedup/replace by that key.

## MBT companion files

| File | Rows loaded | Notes |
|------|-------------|-------|
| AGENTS.MBT | 5 | agent codes |
| COMPANY.MBT | 0 | insurer metadata (often blank) |
| PERSON.MBT | 82 | customer master: email, DOB, gender, city |
| COVRLIFE.MBT | 399 | 115 policies × riders |
| LIFE.MBT | 5 | per-policy life summary |
| LIFEHLTH.MBT | 75 | life+health bundles |
