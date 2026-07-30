# אלטשולר שחם (Altshuler Shaham) — `altshuler` → `altshuler_nifraim`

| | |
|---|---|
| Portal | `https://agents.as-invest.co.il/Login` (Angular SPA) |
| Plugin | `companies/altshuler.py` |
| Parser | `altshuler_nifraim` (commission, גמל) |
| Login | 17 segmented boxes (8 license + 9 ת"ז) → **"שלחו לי קוד זיהוי"** → SMS OTP |
| Nav | top nav → עמלות → "פירוט עמלות סוכנים לפי קופה" → export Excel |

## Two separate issues seen 2026-07-24, both fixed

### 1. Login SPA stuck on the loading spinner (batch 778bd998, ×2)
The screenshot proved it: the page reached the right URL/title but sat on the Angular **loading
spinner** — the login form (`.login-new-input-container`) never painted within the ~30s wait. Nothing
was submitted, so it is NOT a login/rate problem — the SPA bootstrap just hung.
**Fix:** `login()` now tries the load up to **3×**, reloading between attempts (a stuck Angular
bootstrap recovers on reload). Cheap and OTP-free (nothing submitted yet).

### 2. `NaN` in a numeric cell killed the whole file
`אלטשולר נפרעים גמל.xlsx` failed ingest: `ValueError: invalid literal for int() with base 10: 'NaN'` —
openpyxl dies on the FIRST numeric cell whose value is the literal string `NaN`, losing the whole file.
**Fix:** `parser_service._repair_nan_numeric_cells()` strips `<v>NaN</v>` from the sheet XML before
parsing (pure zipfile rewrite). Reproduced the crash and verified the file parses after repair.

## Status
Reliable at login (7/8 batch runs succeeded before the spinner issue). The download+parse path works;
the two fixes address the spinner hang and the NaN ingest. Login dumps now auto-upload
(`altshuler_login.{png,txt,html}`) via the fixed-name artifact catch.
