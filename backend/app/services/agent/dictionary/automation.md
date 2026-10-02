# הורדה אוטומטית ומחזור
ריצות פורטלים, מחזור חודשי ב-21

## portal_runs

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| user_id | uuid | — |  |
| credential_id | uuid | — |  |
| started_at | datetime | — |  |
| finished_at | datetime | — |  |
| kind | varchar | — |  |
| status | varchar | — |  |
| stage | varchar | — |  |
| error_message | text | — |  |
| screenshot_path | varchar | — |  |
| downloaded_filename | varchar | — |  |
| upload_id | uuid | — |  |
| batch_id | uuid | — |  |

## portal_run_batches

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| user_id | uuid | — |  |
| status | varchar | — |  |
| total | integer | — |  |
| succeeded | integer | — |  |
| failed | integer | — |  |
| current_run_id | uuid | — |  |
| started_at | datetime | — |  |
| finished_at | datetime | — |  |
| merged_upload_id | uuid | — |  |
| merged_commission_upload_id | uuid | — |  |
| period_month | date | — |  |
| error_message | text | — |  |
| trigger | varchar | — |  |
| cycle_period | date | — |  |

## cycle_notifications

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| user_id | uuid | — |  |
| kind | varchar | — |  |
| period | date | — |  |
| created_at | datetime | — |  |
| emailed_at | datetime | — |  |
| seen_at | datetime | — |  |
