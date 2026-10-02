# מסלקה פנסיונית
בקשות למסלקה ותשובות — החזקות לקוח, פרודוקציה ב-15 לחודש

## pension_inquiries

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| user_id | uuid | — |  |
| customer_id_number | varchar | — |  |
| customer_name | varchar | — |  |
| status | varchar | — |  |
| interface_code | varchar | — | events_v007:<קוד> — 9100 טרום ייעוץ כל הגופים, 9101 גוף אחד, 9102 איתור קופות רדומות, 2000/2100 פרודוקציה |
| target_yatzran_id | varchar | — |  |
| information_date | varchar | — |  |
| mislaka_number | varchar | — |  |
| request_reference | varchar | — |  |
| vault_outbound_filename | varchar | — |  |
| submitted_at | datetime | — |  |
| acknowledged_at | datetime | — |  |
| completed_at | datetime | — |  |
| expires_at | datetime | — |  |
| error_code | varchar | — |  |
| error_detail | varchar | — |  |
| providers_expected | integer | — |  |
| providers_received | integer | — |  |
| created_at | datetime | — |  |

## pension_holdings

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| user_id | uuid | — |  |
| inquiry_id | uuid | — |  |
| customer_id_number | varchar | — |  |
| receiving_company | varchar | — |  |
| provider_code | varchar | — |  |
| product | varchar | — |  |
| product_type | varchar | — |  |
| fund_policy_number | varchar | — |  |
| track | varchar | — | ריק במסלול ה-15 לחודש — לא לנתח |
| accumulation | numeric | — | צבירה ₪ מהמסלקה |
| total_premium | numeric | — |  |
| management_fee_deposit | numeric | — | ריק במסלול ה-15 לחודש — לא לנתח |
| management_fee_balance | numeric | — |  |
| expected_pension | numeric | — | ריק במסלול ה-15 לחודש — לא לנתח |
| insurance_coverage | text | — |  |
| status_date | date | — |  |
| matched_client_record_id | uuid | — |  |
| match_status | varchar | — |  |
| raw_payload_id | uuid | — |  |
| created_at | datetime | — |  |

## maslaka_agent_links

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| user_id | uuid | — |  |
| agent_id_number | varchar | — |  |
| agent_name | varchar | — |  |
| agent_licence_number | varchar | — |  |
| status | varchar | — |  |
| form_downloaded_at | datetime | — |  |
| submitted_at | datetime | — |  |
| approved_at | datetime | — |  |
| auto_production | boolean | — |  |
| auto_production_at | datetime | — |  |
| rejected_reason | varchar | — |  |
| signed_pdf | blob | — |  |
| signed_pdf_filename | varchar | — |  |
| delivery_note | text | — |  |
| sent_message_id | varchar | — |  |
| reply_message_id | varchar | — |  |
| reply_received_at | datetime | — |  |
| reply_subject | varchar | — |  |
| reply_snippet | text | — |  |
| decided_via | varchar | — |  |
| created_at | datetime | — |  |
| updated_at | datetime | — |  |
