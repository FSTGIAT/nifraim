# מיטב דש (Meitav Dash) — `meitav` → `meitav_nifraim`

| | |
|---|---|
| Portal | `https://customers.meitav.co.il/v2/login/loginAmit` (agents tab) |
| Plugin | `companies/meitav.py` |
| Parser | `meitav_nifraim` (commission; the agent-commission report IS the נפרעים data) |
| Login | identity + prefixPhone + phoneNumber; SMS OTP. **Edge REQUIRED** (`browser_channel="msedge"`) |
| Browser | `headed=True`, `use_persistent_profile=True` |

## The gate: reCAPTCHA **Enterprise** + Akamai Bot Manager
Different mechanism from Mor/analyst: `grecaptcha.enterprise.*` (not `.execute`) + an Akamai sensor
(obfuscated script at a hex-named path). Refusal shows **"נסה שנית"** / `401 gCaptcha error`.
- **Automated Chrome refused, Edge accepted** — measured same machine/minute. `browser_channel="msedge"`.
- `recycle_profile_on_login_failure=True` (default) — Enterprise poisons the profile; nuke-to-cold is
  the cure. Recycle rule is stage-aware ("last run failed at LOGIN") + "gone-bad, not only never-worked".
- ~19% flaky even when everything is right — treat a single failure as flake.

## Seen 2026-07-24: post-OTP session bounce (NOT the same as the login gate)
In the batch, meitav **passed login+OTP** but `download_reports` found the page **back on the login
screen** (`/v2/login/loginAmit`, "לקוחות פרטיים" tab) — the FIRST nav step (`nav_1_report`) already
showed login, so the session bounced after OTP. Reported as a confusing "no-export-trigger".
- **Root cause:** post-OTP session rejection (score/Akamai), not a nav/selector bug.
- **Recommended improvement (not yet shipped):** `submit_otp` should VERIFY it left `/login/loginAmit`
  and fail as an OTP/login rejection (→ retry-eligible), instead of drifting to "no-export-trigger".

## Status
Beaten headed + Edge + persistent profile (e2e 07-19/07-20). Inherently flaky; a single failure is
within its flake rate. Login dumps auto-upload (`<run_id>_nav_1_report.*`, `_nav_2_no_download.*`).
See memory `portal_meitav`.
