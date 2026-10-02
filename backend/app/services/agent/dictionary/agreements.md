# הסכמים ושיעורי עמלה
שיעורי עמלה מההסכמים, מסמכי הסכם ובקשות הסכם

## commission_rates

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| user_id | uuid | — |  |
| company_name | varchar | — |  |
| product | varchar | — |  |
| rate | numeric | — | שיעור כשבר (0.0025 = 0.25%). נפרעים = עמלת ספר + שיעור תגמול; לא להמציא רכיב חסר |
| rate_kind | varchar | — |  |
| rate_scope | varchar | — |  |
| payment_frequency | varchar | — |  |
| paid_to | varchar | — |  |
| company_email | varchar | — |  |
| effective_from | date | — |  |
| effective_to | date | — |  |
| source_document_id | uuid | — |  |

## volume_commission_rates

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| user_id | uuid | — |  |
| company_name | varchar | — |  |
| nifraim_rate | numeric | — |  |
| volume_rate_per_million | numeric | — |  |
| pension_accumulation | numeric | — |  |
| changed_percent | numeric | — |  |
| conversion_to_annuity | numeric | — |  |
| payment_frequency | varchar | — |  |
| paid_to | varchar | — |  |
| notes | text | — |  |

## ai_documents

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| user_id | uuid | — |  |
| filename | varchar | — |  |
| sha256 | varchar | — |  |
| size_bytes | integer | — |  |
| doc_type | varchar | — |  |
| companies_mentioned | jsonb | — |  |
| structured_data | jsonb | — |  |
| summary | text | — |  |
| status | varchar | — |  |
| error | text | — |  |
| file_path | varchar | — |  |
| extracted_text | text | — |  |
| uploaded_at | datetime | — |  |
| processed_at | datetime | — |  |

## agreement_requests

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| user_id | uuid | — |  |
| company_key | varchar | — |  |
| company_name | varchar | — |  |
| to_email | varchar | — |  |
| contact_name | varchar | — |  |
| subject | varchar | — |  |
| sent_message_id | varchar | — |  |
| status | varchar | — |  |
| sent_at | datetime | — |  |
| replied_at | datetime | — |  |
| reply_message_id | varchar | — |  |
| document_id | uuid | — |  |
| error | text | — |  |
| created_at | datetime | — |  |

## company_contacts

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| user_id | uuid | — |  |
| company_name | varchar | — |  |
| email | varchar | — |  |
| contact_name | varchar | — |  |
| notes | varchar | — |  |
| created_at | datetime | — |  |

## paying_companies

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| user_id | uuid | — |  |
| company_name | varchar | — |  |
| created_at | datetime | — |  |
