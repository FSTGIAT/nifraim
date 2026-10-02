# פורטל לקוח
קישורים ותמונות מצב שהסוכן שיתף עם לקוחות

## customer_portal_links

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| user_id | uuid | — |  |
| token | varchar | — |  |
| customer_id_number | varchar | — |  |
| customer_name | varchar | — |  |
| customer_email | varchar | — |  |
| password_hash | varchar | — |  |
| expires_at | datetime | — |  |
| is_active | boolean | — |  |
| failed_attempts | integer | — |  |
| last_failed_at | datetime | — |  |
| created_at | datetime | — |  |
| last_accessed_at | datetime | — |  |
| settings | jsonb | — |  |

## portal_snapshots

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| portal_link_id | uuid | — |  |
| upload_id | uuid | — |  |
| user_id | uuid | — |  |
| customer_id_number | varchar | — |  |
| snapshot_date | datetime | — |  |
| period_label | varchar | — |  |
| kpi_json | json | — |  |
| products_json | json | — |  |
| company_breakdown_json | json | — |  |
| has_changes | boolean | — |  |
| changes_json | json | — |  |
| created_at | datetime | — |  |
