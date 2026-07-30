# מור (Mor) — `mor` → `nifraim` parser

| | |
|---|---|
| Plugin | `companies/mor.py` |
| Login | 3 fields packed into 2 DB cols (`PORTAL_LOGIN_FIELDS`); licence is **8-digit, NOT zero-padded** |
| Browser | `headed=True`, `use_persistent_profile=True`; accepts BOTH Chrome and Edge |
| Delivers | נפרעים (gemel/pension house — production is מסלקה territory) |

## Status: WORKING (07-24 batch: `מור נפרעים 06-2026.xlsx`, e.g. 490 records)

## The gate: reCAPTCHA (score), not a request bug
- Config that passes: headed · real Chrome/Edge (never bundled Chromium) ·
  `--disable-blink-features=AutomationControlled` · NO `navigator.webdriver` JS patch · `no_viewport` +
  `--start-maximized` · fresh/unwarmed profile.
- The captcha token is an HTTP **header** (`recaptcha:`), not a body field.
- `recycle_profile_on_login_failure=True` — a poisoned `_GRECAPTCHA` beats every downstream fix; cold is fine.
See `docs/ARCHITECTURE.md` §4c and memory `portal_mor` / `portal_login_fields`.
