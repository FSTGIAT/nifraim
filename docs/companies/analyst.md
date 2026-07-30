# אנליסט (Analyst) — `analyst` / `analyst_nifraim`

Investment house (gemel/pension). Delivers **נפרעים** (agent commission) — its production is מסלקה territory.

| | |
|---|---|
| Portal | `https://agent.analyst.co.il/auth/login` |
| Plugin | `services/portal_automation/companies/analyst.py` |
| Parser | `analyst_nifraim` (format detection in `parser_service.py`) |
| Login | ת"ז + phone; button **"שלחו לי קוד"** → SMS OTP |
| OTP route | its OWN route `/auth/otp` (NOT a query param) — six segmented `maxlength=1` boxes |
| Browser | **Edge REQUIRED** (`browser_channel="msedge"`), `headed=True`, `use_persistent_profile=True` |

## ✅ CONFIRMED WORKING END-TO-END (kiko's worker, 2026-07-25 06:45)

```
07-25 06:45:17 (59s)  success@parse  →  אנליסט עמלות 06-2026.xlsx
worker log:  run 3c090cb4 analyst: recycled browser profile (last run on it was rejected)
             run 3c090cb4 analyst: persistent browser=msedge COLD-PROFILE
```

**How the working run flows — the exact chain that succeeds:**
1. The *previous* run failed at `@login` → the runner's stage-aware recycle marks the profile for reset.
2. This run **discards the poisoned profile** (`recycle_profile_on_login_failure=True`) and launches a
   **fresh COLD Edge profile** (`browser=msedge COLD-PROFILE`). A cold profile is what passes v3 — proven
   locally: fresh profile → valid 2169-char token → `Authorization/Login` 200 → OTP screen.
3. Login submits `שלחו לי קוד` → SMS → the runner grabs the code from `otp_inbox`.
4. `submit_otp` types the 6 boxes → `Authorization/ValidateOTP` → **`{"isError":false,"role":1}`** (200).
   If a stale-code rejection (`errorCode:2`) occurs, the runner **re-grabs the newest code and retries**.
5. `→ /lobby` → drive the date calendar (readonly pickers) → export → `analyst_nifraim` file ingested.

**The two fixes that made it work (both regressions, found by local reproduction — see below):**
- **Login:** `recycle_profile_on_login_failure=True` — shed the poisoned profile, run on a fresh one.
- **OTP:** on `errorCode:2`, re-fetch the newest unconsumed code and retry the submit once
  (`runner._run_inner`, `_wait_for_otp(..., timeout_s=8)`).

**Operational note that mattered:** after pressing "עדכן עובד", WAIT for the worker to finish
re-exec'ing (chip online/idle) before running — kiko's 18:55 run fired 20 s into the update and executed
on the OLD code (recycle=False), so it failed identically to before. The 06:45 run, on the settled new
code, recycled and succeeded.

## The gate: reCAPTCHA v3 (this is the whole story)

Analyst is refused by a **reCAPTCHA v3 score**, evaluated **before any SMS is sent**. The rejection
is `400 {"...":"Recaptcha validation failed"}` and the agent sees "לא נשלחה הודעת SMS".

- **Automated Chrome is refused; Edge is accepted.** `browser_channel="msedge"` is mandatory. This is
  why analyst **cannot be tested on a box without Edge** (e.g. the dev WSL box has only Chrome) — a
  Chrome run fails at reCAPTCHA for the wrong reason.
- **`recycle_profile_on_login_failure = False`** — analyst keeps its persistent Edge profile to age the
  Google/browsing cookies a v3 gate scores on (recycling to cold gets refused too — a documented
  deadlock).

### The regression and the fix (2026-07-24) — a FRESH profile passes
**Reproduced locally 2026-07-24 (the decisive test):** launch a BRAND-NEW profile with the runner's
headed args, go to `/auth/login`, fill ת"ז+phone, submit → `grecaptcha` mints a **2169-char token** and
the `Authorization/Login` POST returns **200 `{"isError":false...}`** → OTP screen, and the SMS
actually arrives. So **a fresh profile passes end-to-end.** (It passed even with SwiftShader WebGL, so
the GPU / `--disable-gpu` is NOT the cause — that lead was wrong and was reverted.)

**What broke it:** commit **`2d5a0fd` (07-22) "let the profile PERSIST across login rejections"** set
`recycle_profile_on_login_failure=False`. It worked for ~a day while the profile was clean (07-22,
07-23), then the SAME kept profile accumulated failed-login reputation and was refused from 07-24 on —
the textbook "worked before, then stopped." A poisoned profile beats every downstream fix (memories
`portal_mor`, `portal_cold_profile_recaptcha`).

**Fix = recycle to fresh, like Mor/Meitav:** `recycle_profile_on_login_failure=True`. The runner's
recycle is **stage-aware** — it nukes the profile only after a **login-stage** rejection (a run that
passed login and failed at `@otp`/`@download` keeps its proven profile). So a poisoned profile is shed
and the next run starts fresh → passes, as the local test proves.

## Downstream flow (proven working 07-22 15:46, 07-23 batch)
login (shed → ת"ז/phone → "שלחו לי קוד") → OTP screen `/auth/otp` → **type whole code into the FIRST
box**, let the component auto-advance (per-box clicking desyncs vs auto-advance and drops digits) →
"כניסה" → `/reports` → **drive the date calendar** (pickers are READONLY) → export → `analyst_nifraim`.

## The OTP leg — `errorCode:2` is a stale code, NOT reCAPTCHA (solved 2026-07-24)
The `@otp` failures ("קוד ה-OTP נדחה — עדיין במסך הקוד") were NOT a second captcha gate. Reproduced
locally: the OTP-verify POST is `200 Authorization/ValidateOTP {"isError":true,"errorCode":2}` — HTTP
200 (reCAPTCHA passed), the CODE rejected. **Cause:** the portal honours only the NEWEST code, and when
a SECOND code is issued (the login captcha-retry re-requests, a resend fires, or two runs overlap) the
runner had grabbed and submitted the OLDER, now-invalidated one → errorCode 2.
**Proven end-to-end with a SINGLE clean code:** `submit 676014 → {"isError":false,"role":1}` →
GetUserData → GetAgentFinancialInfo → **`/lobby`** (fully logged in).
**Fix:** `runner._run_inner` — on an OTP-submit rejection, wait briefly, re-grab the NEWEST unconsumed
code (`_wait_for_otp(..., timeout_s=8)`) and retry the submit ONCE (no extra OTP requested). So a
stale-code rejection self-heals to the valid newest code.

## Known-open / watch
- **Interactive-desktop matters for v3.** The score drops on a locked/RDP-disconnected/idle screen —
  run on an UNLOCKED, actively-used machine. This is a real lever, not hand-waving.
- **Let the reputation BUILD — don't reset it.** The stage-aware shed keeps a proven reputation and
  sheds only a poisoned one, so consecutive good runs raise the v3 score. Rapid-fire rejected attempts
  in a short window work against that build; space real attempts out. The goal is a self-reinforcing
  GOOD reputation, which is achievable — this portal is not unsolvable.

## History (kikohib, batch vs single)
`07-23 05:39 success BATCH` · `07-22 15:46 success single` · everything else `@login` reject (v3) —
2 successes / ~14 attempts. It works in BOTH batch and single; the shed fix is meant to raise the odds.

## Test notes
- **Not testable on a no-Edge box** and **not testable on a cold profile** (no poison to shed). The
  real test is a **single analyst run on kiko's worker** (Edge + IL IP + the real poisoned profile).
- Evidence artifacts auto-upload on failure: `analyst_login*.{png,txt,html}`, `analyst_post_otp.*`,
  `analyst_after_send.*` → `GET /api/portal-automation/_debug/screenshots`.
