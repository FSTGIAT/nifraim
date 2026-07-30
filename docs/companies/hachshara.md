# הכשרה (Hachshara) — `hachshara` → `hachshara_nifraim`

| | |
|---|---|
| Portal | `https://agents-login.hcsra.co.il/my.policy` (F5 BIG-IP APM) |
| Plugin | `companies/hachshara.py` |
| Parser | `hachshara_nifraim` (commission) |
| Login | 9-digit username (leading-zero padded: `40336281`→`040336281`); SMS OTP (input `#text`) |

## Status: FIXED + VERIFIED LIVE 2026-07-24 (356 rows downloaded)

## The failure that was fixed (batch 3c0b055f)
After OTP the Angular SPA boots slowly. Every navigation click timed out **silently**, and the run
died much later at `no-download-trigger-visible` with `url = the site ROOT` — blaming the wrong step.
The report id had also moved (`/reports/66` → `/reports/152`).

## The fix — verified navigation, not fire-and-forget
Each hop now **verifies the URL advanced**, retries, and fails loudly AT that step:
1. Slow-boot gate: `wait_for_selector('דוחות', timeout=45s)` before touching anything.
2. דוחות → must land on `/reports` (retry ×3).
3. עמלות section (scroll to it) → **בסט אינווסט-עמלות נפרעים** tile → must land on `/reports/<digits>`
   (match the pattern, NEVER a fixed id — it changes).
4. Wait for the report form (agent autocomplete / excel button) to render — up to 60s (lazy).
5. Agent autocomplete → **הכל** → **הורד ל excel** (native download + XHR fallback).

## Real report layout (live 2026-07-24)
Report tile lives under the **עמלות** section header at the bottom of `/reports`. The report form has
`בחר מספר פיננסי סוכן` / `בחר סוכן` / `בחר חודש עיבוד` — all default to **הכל**. `הורד ל excel` streams a
native download. File = `hachshara_nifraim` (356 rows verified: id/commission/balance/fund_type).

## Note
הכשרה **production** arrives by EMAIL (`Ild_prod_*.zip`), NOT this portal — see `docs/ARCHITECTURE.md`
§10 and `services/hachshara_prod/`. This portal is **נפרעים only**.
