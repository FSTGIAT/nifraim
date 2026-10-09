# נתוני שוק
תשואות, דמי ניהול וזרימות רשמיים לכל קופה לפי חודש (גמל-נט/פנסיה-נט/ביטוח-נט); פילוח נכסים של קרנות הפנסיה (פנסיה-נט)

## fund_market_monthly

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| source | varchar | — |  |
| fund_id | integer | — |  |
| report_period | integer | — | YYYYMM של הדיווח (פיגור של 1–2 חודשים) |
| fund_name | varchar | — |  |
| classification | varchar | — |  |
| specialization | varchar | — |  |
| sub_specialization | varchar | — |  |
| target_population | varchar | — |  |
| parent_company | varchar | — |  |
| managing_corporation | varchar | — |  |
| managing_corp_legal_id | bigint | — |  |
| total_assets | float | — | גודל הקופה, מיליוני ₪ |
| deposits | float | — |  |
| withdrawals | float | — |  |
| internal_transfers | float | — |  |
| net_monthly_deposits | float | — | צבירה נטו בחודש, מיליוני ₪ |
| mgmt_fee | float | — | דמי ניהול מצבירה באחוזים (0.53 = 0.53%) |
| deposit_fee | float | — |  |
| monthly_yield | float | — |  |
| ytd_yield | float | — |  |
| yield_3y | float | — |  |
| yield_5y | float | — |  |
| avg_yield_3y | float | — | תשואה שנתית ממוצעת 3 שנים באחוזים |
| avg_yield_5y | float | — |  |
| std_dev | float | — |  |
| alpha | float | — |  |
| sharpe | float | — |  |
| liquid_pct | float | — |  |
| stock_exposure | float | — |  |
| foreign_exposure | float | — |  |
| fx_exposure | float | — |  |
| actuarial_adjustment | float | — |  |
| fetched_at | datetime | — |  |

## pensyanet_data

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| report | varchar | — | general/assets_main/assets_full/assets_trad/yields/tracks — דוחות ה-XML של פנסיה-נט |
| level | varchar | — | track = מסלול (entity_id = fund_id של fund_market_monthly) · fund = קרן |
| entity_id | integer | — |  |
| entity_name | varchar | — |  |
| period | integer | — |  |
| grp | varchar | — | קבוצת הפילוח (10 קבוצות ראשיות / רמת סיכון / חשיפות / סחיר / ארץ-חו"ל) |
| item_id | integer | — |  |
| item_name | varchar | — |  |
| amount | float | — | באלפי ₪ (דוחות נכסים) |
| pct | float | — | אחוז מנכסי המסלול/הקרן |
| data | jsonb | — |  |
| fetched_at | datetime | — |  |

## fund_tracks

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| label_he | varchar | — |  |
| category | varchar | — |  |
| maslul | varchar | — |  |
| sort_order | integer | — |  |
| month_return | numeric | — |  |
| ytd_return | numeric | — |  |
| y1_return | numeric | — |  |
| y3_return | numeric | — |  |
| y5_return | numeric | — |  |
| period_label | varchar | — |  |
| scraped_at | datetime | — |  |

## yield_recommendations

| עמודה | סוג | מילוי | הערה |
|---|---|---|---|
| user_id | uuid | — |  |
| production_upload_id | uuid | — |  |
| id_number | varchar | — |  |
| client_name | varchar | — |  |
| fund_policy_number | varchar | — |  |
| product_type | varchar | — |  |
| current_company | varchar | — |  |
| current_track | varchar | — |  |
| current_yield_1y | numeric | — |  |
| current_yield_3y | numeric | — |  |
| current_yield_5y | numeric | — |  |
| recommended_track_id | varchar | — |  |
| recommended_track_name | varchar | — |  |
| recommended_fund_name | varchar | — |  |
| recommended_yield_1y | numeric | — |  |
| recommended_yield_3y | numeric | — |  |
| recommended_yield_5y | numeric | — |  |
| risk_class | varchar | — |  |
| move_type | varchar | — |  |
| accumulation | numeric | — |  |
| potential_annual_gain | numeric | — |  |
| reasoning | varchar | — |  |
| confidence | varchar | — |  |
| generated_at | datetime | — |  |
