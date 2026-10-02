# עמלות ונפרעים
מה שולם בפועל מול מה שצפוי, חובות וגבייה

## commission_comparisons

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| user_id | uuid | — |  |
| category | varchar | — |  |
| production_upload_id | uuid | — |  |
| summary_json | jsonb | — |  |
| result_json | jsonb | — |  |
| commission_company_sources | jsonb | — |  |
| computed_at | datetime | — |  |

## debts

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| user_id | uuid | — |  |
| company_name | varchar | — |  |
| category | varchar | — |  |
| customer_id_number | varchar | — |  |
| customer_name | varchar | — |  |
| product | varchar | — |  |
| policy_number | varchar | — |  |
| expected_amount | numeric | — | עמלה צפויה שלא שולמה ₪ (status=open) |
| premium | numeric | — |  |
| accumulation | numeric | — |  |
| status | varchar | — |  |
| status_changed_at | datetime | — |  |
| production_upload_id | uuid | — |  |
| commission_upload_id | uuid | — |  |
| last_emailed_at | datetime | — |  |
| email_count | integer | — |  |
| created_at | datetime | — |  |
| updated_at | datetime | — |  |

## collection_cases

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| user_id | uuid | — |  |
| company_key | varchar | — |  |
| company_name | varchar | — |  |
| period | date | — |  |
| items | jsonb | — |  |
| customers_count | integer | — |  |
| expected_total | float | — |  |
| to_email | varchar | — |  |
| contact_name | varchar | — |  |
| status | varchar | — |  |
| draft_subject | varchar | — |  |
| draft_body | text | — |  |
| sent_at | datetime | — |  |
| sent_message_id | varchar | — |  |
| reminder_count | integer | — |  |
| last_reminder_at | datetime | — |  |
| replied_at | datetime | — |  |
| reply_message_id | varchar | — |  |
| reply_summary | text | — |  |
| resolved_at | datetime | — |  |
| error | text | — |  |
| created_at | datetime | — |  |
| updated_at | datetime | — |  |

## volume_bonus_payments

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| user_id | uuid | — |  |
| company_name | varchar | — |  |
| year | integer | — |  |
| is_paid | boolean | — |  |
| paid_date | date | — |  |
| notes | text | — |  |
| created_at | datetime | — |  |
| updated_at | datetime | — |  |
