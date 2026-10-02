# זיכרון ה-AI
מה ה-AI למד על הסוכן ואילו שאלות הוא שואל

## ai_memories

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| user_id | uuid | — |  |
| kind | varchar | — |  |
| text | text | — |  |
| source | varchar | — |  |
| uses | integer | — |  |
| created_at | datetime | — |  |
| last_used | datetime | — |  |

## ai_intent_log

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| user_id | uuid | — |  |
| intent | varchar | — |  |
| lane | varchar | — |  |
| ms | integer | — |  |
| question | varchar | — |  |
| created_at | datetime | — |  |
