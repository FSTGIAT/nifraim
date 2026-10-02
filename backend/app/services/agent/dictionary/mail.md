# מייל
מיילים מחברות ולקוחות, טיוטות, שולחים במעקב

## mail_items

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| user_id | uuid | — |  |
| watch_sender_id | uuid | — |  |
| provider_id | varchar | — |  |
| internet_message_id | varchar | — |  |
| in_reply_to | varchar | — |  |
| references | text | — |  |
| from_address | varchar | — |  |
| from_name | varchar | — |  |
| subject | varchar | — |  |
| received_at | datetime | — |  |
| encrypted_body | text | — |  |
| attachments | json | — |  |
| category | varchar | — |  |
| summary | text | — |  |
| entities | json | — |  |
| suggested_action | varchar | — |  |
| ai_skipped_reason | varchar | — |  |
| linked_company | varchar | — |  |
| linked_customer_id_number | varchar | — |  |
| draft_subject | varchar | — |  |
| draft_body | text | — |  |
| draft_warnings | json | — |  |
| draft_model | varchar | — |  |
| draft_edited | boolean | — |  |
| sent_message_id | varchar | — |  |
| sent_at | datetime | — |  |
| imported_upload_id | uuid | — |  |
| status | varchar | — |  |
| created_at | datetime | — |  |
| updated_at | datetime | — |  |

## mail_watch_senders

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| user_id | uuid | — |  |
| address | varchar | — |  |
| label | varchar | — |  |
| kind | varchar | — |  |
| company_name | varchar | — |  |
| customer_id_number | varchar | — |  |
| created_at | datetime | — |  |

## mail_agent_profiles

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| user_id | uuid | — |  |
| signature | text | — |  |
| tone | varchar | — |  |
| address_form | varchar | — |  |
| writer_form | varchar | — |  |
| greeting | varchar | — |  |
| closing | varchar | — |  |
| customer_rules | text | — |  |
| insurer_rules | text | — |  |
| never_say | text | — |  |
| style_notes | text | — |  |
| encrypted_examples | text | — |  |
| learn_opt_in | boolean | — |  |
| learned_at | datetime | — |  |
| skipped_at | datetime | — |  |
| completed_at | datetime | — |  |
| created_at | datetime | — |  |
| updated_at | datetime | — |  |
