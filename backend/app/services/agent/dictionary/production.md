# פרודוקציה ותיק
מה יש לכל לקוח בכל חברה — מוצר, צבירה, פרמיה, מסלול

## client_records

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| user_id | uuid | — |  |
| upload_id | uuid | — |  |
| id_number | varchar | — | ת.ז לקוח בלי אפסים מובילים |
| first_name | varchar | — |  |
| last_name | varchar | — |  |
| sign_date | date | — |  |
| recruitment_type | varchar | — |  |
| product | varchar | — |  |
| fund_policy_number | varchar | — |  |
| employment_status | varchar | — |  |
| is_active | varchar | — |  |
| receiving_company | varchar | — | החברה המנהלת (שם משפטי; לנרמל לפי שורש: הפניקס/מגדל/…) |
| track | varchar | — | מסלול השקעה (שם כפי שהחברה כותבת) |
| transferring_fund | varchar | — |  |
| transferring_body | varchar | — |  |
| product_type | varchar | — |  |
| total_premium | numeric | — | פרמיה ₪ (חודשית בביטוח) |
| accumulation | numeric | — | צבירה ₪. accumulation_source='nifraim' = הושלם מהנפרעים כשהפרודוקציה הייתה ₪0 |
| accumulation_source | varchar | — |  |
| track_split | jsonb | — | פיצול צבירה בין מסלולים: [{track, amount}] |
| product_status | varchar | — | סטטוס מוצר מהחברה (פעיל/מבוטל/מוקפא…) |
| fund_type | varchar | — |  |
| fund_number | varchar | — |  |
| month_end_balance | numeric | — |  |
| annual_commission_pct | numeric | — |  |
| monthly_commission_pct | numeric | — |  |
| reported_commission_pct | numeric | — |  |
| commission_before_fee | numeric | — |  |
| expected_amount | numeric | — |  |
| actual_amount | numeric | — |  |
| expected_raw | text | — |  |
| actual_raw | text | — |  |
| amount_difference | numeric | — |  |
| transfer_date | date | — |  |
| management_fee | numeric | — |  |
| lead_source | varchar | — |  |
| agent_number | varchar | — |  |
| rights_assignment_date | date | — |  |
| general_notes | text | — |  |
| management_fee_amount | numeric | — |  |
| processing_date | varchar | — |  |
| balance | numeric | — |  |
| commission_paid | numeric | — | עמלה ששולמה בפועל ₪ (שורות נפרעים) |
| commission_expected | numeric | — |  |
| client_phone | varchar | — |  |
| client_email | varchar | — |  |
| employer_name | varchar | — |  |
| employer_id | varchar | — |  |
| reconciliation_status | varchar | — |  |

## file_uploads

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| user_id | uuid | — |  |
| filename | varchar | — |  |
| file_type | varchar | — |  |
| company_source | varchar | — |  |
| record_count | integer | — |  |
| format_type | varchar | — |  |
| is_production | boolean | — | True = קובץ הפרודוקציה הפעיל של החברה |
| file_category | varchar | — |  |
| file_path | varchar | — |  |
| uploaded_at | datetime | — |  |
| period_month | date | — | החודש שהקובץ מדווח עליו (לא תאריך ההעלאה); נפרעים מגיעים ~30 יום באיחור |

## production_summaries

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| user_id | uuid | — |  |
| upload_id | uuid | — |  |
| period_label | varchar | — |  |
| upload_date | datetime | — |  |
| total_records | integer | — |  |
| unique_clients | integer | — |  |
| total_premium | numeric | — |  |
| total_accumulation | numeric | — |  |
| companies_json | json | — |  |
| product_types_json | json | — |  |
| top_clients_json | json | — |  |
| changes_json | json | — |  |
| created_at | datetime | — |  |

## recruits

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| user_id | uuid | — |  |
| id_number | varchar | — |  |
| first_name | varchar | — |  |
| last_name | varchar | — |  |
| company | varchar | — |  |
| product | varchar | — |  |
| amount | numeric | — |  |
| customer_status | varchar | — |  |
| sign_date | date | — |  |
| category | varchar | — |  |
| created_at | datetime | — |  |
