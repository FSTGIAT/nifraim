# Nifraim — Architecture Map

> **Purpose of this file.** A machine-readable map of the app so any Claude Code
> session can orient itself *without* being re-briefed. Read this first. The
> Mermaid graphs below render visually on GitHub and encode the module graph +
> data flows; the **Navigation Index** tells you which file owns each concern.
>
> Pair with `CLAUDE.md` (conventions, pitfalls, how-to-add-a-parser). This file
> answers **"how is it wired and where do I look"**; `CLAUDE.md` answers **"how
> do I write code that fits."**

---

## 0. One-paragraph mental model

Nifraim reconciles **production** (what the agent sold — premium/accumulation)
against **נפרעים / commission** (what each insurer actually paid). Files arrive
three ways: manual upload, **hands-free portal automation**, or — for the one
insurer that emails instead of publishing (הכשרה production) — **mail intake**
(§10). Because Israeli
insurer WAFs geo-block the cloud IP, automation runs on **two planes**: the
**cloud** (Railway — UI, DB, Claude, analytics) is the brain; a **local worker**
on the agent's Windows PC in Israel is the hands. They never call each other
directly — the **PostgreSQL database is the only rendezvous**. OTP codes flow
from the agent's phone → cloud inbox → worker.

---

## 1. System graph (the two planes)

```mermaid
graph TB
    subgraph CLOUD["☁️ CLOUD · Railway (foreign IP, geo-blocked from insurers)"]
        FE["Frontend · Vue3+Pinia<br/>frontend/src/"]
        API["FastAPI · api/*.py<br/>thin routers, JWT auth"]
        SVC["services/*.py<br/>business logic"]
        DB[("PostgreSQL 16<br/>single source of truth")]
        SCHED["scheduler.py<br/>APScheduler cron"]
        CLAUDE["Claude API<br/>document_extraction.py"]
        MAIL["mail_intake/*.py<br/>Graph · IMAP · Resend"]
        FE -->|/api Bearer| API
        API --> SVC
        SVC --> DB
        SCHED --> SVC
        SCHED --> MAIL
        SVC --> CLAUDE
        MAIL -->|"ingest_mail_attachment"| DB
    end

    subgraph LOCAL["🖥️ LOCAL WORKER · agent's Windows PC in Israel (real IL IP)"]
        WK["local_worker.py<br/>heartbeat + CAS claim"]
        RUN["portal_automation/runner.py<br/>login→OTP→export→ingest"]
        BATCH["batch_runner.py<br/>run-all fan-out + merge"]
        PLUG["companies/*.py<br/>21+ Playwright plugins"]
        WK --> BATCH --> RUN --> PLUG
    end

    PHONE["📱 Android app<br/>android/ · OtpFilter.kt"]
    INS["🏢 Insurer portals<br/>Harel·Menora·Phoenix·Mor…"]
    BOX["📧 Agent's mailbox<br/>M365 · Gmail · other"]

    WK -.->|"heartbeat / claim pending<br/>(DB is the rendezvous)"| DB
    RUN -->|"ingest_file_bytes"| DB
    PLUG <-->|"login + download"| INS
    INS -->|"OTP SMS"| PHONE
    PHONE -->|"POST /phone-forward/{token}"| API
    API -->|"otp_inbox row"| DB
    RUN -.->|"_wait_for_otp polls"| DB

    MAIL <-->|"poll (Graph/IMAP)"| BOX
    BOX -.->|"forwarded mail → webhook"| API

    classDef cloud fill:#E7EEFB,stroke:#2D6FE0,color:#111;
    classDef local fill:#ECE7FA,stroke:#6D4FD0,color:#111;
    classDef ext fill:#F3F4F6,stroke:#8A909C,color:#111;
    class FE,API,SVC,SCHED,CLAUDE,MAIL cloud;
    class WK,RUN,BATCH,PLUG local;
    class PHONE,INS,BOX,DB ext;
```

**Not everything comes from a portal.** הכשרה never publishes production in its agent
portal — it **emails** a `Ild_prod_*.zip`. That harvest runs on the **cloud**, not
the worker: mail hosts aren't geo-blocked, so none of the two-plane machinery
applies. See §10.

**Dispatch rule** (`api/portal_automation.py::_should_defer_to_worker`): if the
user's worker heartbeated ≤ **90 s** ago (or global `WORKER_MODE`), a batch stays
`pending` for the worker to claim; otherwise it runs **inline on the cloud**
(where IL portals fail). Installing + running the worker is the only switch.

**Worker identity is a TOKEN, not a machine — and machines are not interchangeable.**
`local_worker.py` resolves *whose* worker it is from `WORKER_LOG_TOKEN` in its local
`.env` (= `users.phone_forward_token`). Run one agent's installer link on a second PC
and that PC becomes a full copy of their worker: it heartbeats as them, claims their
batches, logs into the insurers with their credentials, and writes their clients'
files to its own disk. Atomic claims stop double *execution*; they say nothing about
*which machine* executes — and only a machine with the Ericom PowerTerm client can
open Phoenix's green terminal (§ Windows-native terminal). Shipped incident: an
agent's token was installed on a colleague's laptop, `worker_heartbeats.hostname`
flipped with whichever PC was on, and Phoenix "randomly" worked or didn't for weeks.
Invariants:
1. **`worker_heartbeats.approved_hostname` pins an account to one machine.** Any other
   machine refuses to beat and refuses to claim. `NULL` = unpinned = original
   behaviour, so nobody can be locked out.
2. **One owner at a time.** The `ON CONFLICT … WHERE` guard in `_beat` decides
   ownership atomically (take the row if it's ours, or its owner went stale >90 s), so
   two PCs cannot flip-flop the hostname. The loser stands by; it never claims.
3. **Only the owner self-updates** — `_maybe_self_update` *clears* the flag, so a
   standby consuming it would strand the working machine on stale code.

---

## 2. Navigation index — "where do I look for X"

| I need to change / understand… | Go to |
|---|---|
| **Nifra AI v2 — any AI answer (chat + Nifra Agent ask), its tools, cache, privacy, fund data** | §17c → `services/agent/` (`loop.py`, `registry.py`, `tools_*.py`), `api/ai_agent.py`, `services/fund_market/`, `utils/agentStream.js`, `tests/test_nifra_agent.py` |
| **AI chat charts (viz) — why a graph did/didn't open, silk open, hover trace** | §17c + `docs/AI_VIZ.md` → `tools_viz.render_chart`, `ai_service.stream_chat`, `ai_viz_fallback.py`, `AiVizPanel.vue` |
| **Parse a new insurer Excel format** | `services/parser_service.py` + `utils/hebrew_mappings.py` (see CLAUDE.md "How to Add a Parser") |
| **Hebrew → DB column mapping / format signatures** | `utils/hebrew_mappings.py` |
| **Which reporting month a file is *for*** | `parser_service.py::detect_period_month` |
| **Commission ↔ production matching (paid/unpaid)** | `services/comparison_service.py::compute_comparison` |
| **"Full picture" multi-company comparison** | `services/comparison_orchestrator.py::compute_merged_comparison` |
| **Upload + auto-compare pipeline** | `services/upload_ingest.py::ingest_file_bytes`, `schedule_post_ingest` |
| **Record-level reconciliation & analytics** | `services/reconciliation_service.py` |
| **A single portal run (login→OTP→export)** | `services/portal_automation/runner.py::_run_inner` |
| **"Run all companies" batch** | `services/portal_automation/batch_runner.py::_run_batch_inner` |
| **A specific insurer's automation** | `services/portal_automation/companies/<name>.py` |
| **Which fields the "הוסף פורטל" form shows** | `companies/__init__.py::PORTAL_LOGIN_FIELDS` → `/portal-kinds` → `PortalCredentialModal.vue` |
| **Merge per-company files into one workbook** | `services/portal_automation/aggregate.py` |
| **הכשרה production (emailed zip, no portal)** | `services/hachshara_prod/` + §10 |
| **Which mail path an agent gets (M365/Gmail/other)** | `services/mail_intake/detect.py::detect_mail_host` |
| **The one seam mail uses to reach ingest** | `services/mail_intake/__init__.py::ingest_mail_attachment` |
| **Microsoft consent / Gmail IMAP / Resend webhook** | `services/mail_intake/{graph,gmail,resend}.py`, `api/mailbox.py` |
| **Local worker lifecycle / self-update** | `backend/local_worker.py` |
| **New customer journey / monthly cycle (21st, locked tab, manual vs מסלקה production)** | §13 · `services/cycle_service.py`, `api/cycle.py`, `stores/cycle.js`, `ProductionTab.vue` |
| **Worker endpoints (bundle, heartbeat, update, log)** | `api/portal_automation.py` (`/worker/*`) |
| **OTP webhook / templates / next-otp** | `api/portal_automation.py` (`/phone-forward/*`) |
| **OTP company routing from SMS text** | `services/otp_routing.py::match_otp_company` |
| **Android SMS forwarder logic** | `android/app/.../smsforwarder/OtpFilter.kt`, `SmsReceiver.kt` |
| **Global SMS OTP templates (CRUD/seed)** | `api/sms_otp_templates.py`, `models/sms_otp_template.py` |
| **Claude agreement/rate extraction** | `services/document_extraction.py`, `api/ai_documents.py` |
| **How extracted rates are picked for math** | `services/rate_select.py` |
| **How expected commission is calculated** | `services/rate_select.py` + skill `commission-calculation` |
| **Why a company contributes ₪0 (coverage)** | `rate_select.explain_expected_commission`, `GET /api/commission-rates/coverage` |
| **Company name spaces (legal vs collapse vs stem)** | `utils/company_norm.py` — see §6b |
| **AI chat (streaming)** | `services/ai_service.py::stream_chat` |
| **Customer portal (shareable link)** | `services/portal_service.py`, `api/portal.py`, `CustomerPortalView.vue` |
| **Phoenix native terminal (green-screen)** | `scripts/windows/phoenix_terminal_run.py`, `services/phoenix_mu.py` |
| **Volume report (דוח היקפים, multi-sheet)** | `parser_service.py::_parse_volume_report`, `services/volume_service.py` |
| **Scheduled jobs (cron)** | `backend/app/scheduler.py` |
| **CSS design tokens / RTL root** | `frontend/src/App.vue` (`:root`) |
| **Main workspace UI (5 tabs)** | `frontend/src/views/WorkspaceView.vue` |
| **Comparison dashboard UI** | `frontend/src/components/comparison/ComparisonDashboard.vue` |
| **Workspace tab bar (home cards + strip) + hover FX** | `frontend/src/components/workspace/WorkspaceTabs.vue` |
| **Tab icons (duotone) — single source of truth** | `frontend/src/components/icons/{AppIcon.vue, tabIcons.js}` |
| **Per-tab colour identity tokens** | `App.vue` `:root` (`--tab-*` accent/wash/ink) |
| **Card ambient hover animation (Remotion)** | `remotion/CardAmbientLoop.tsx`, `components/workspace/CardAmbientIsland.vue` |
| **User-to-user chat (messenger)** | `api/messenger.py`, `models/dm_*.py`, `stores/messenger.js`, `components/workspace/MessengerDock.vue` |
| **Who is online (a PERSON, not a worker PC)** | `models/dm_presence.py` (50s) — contrast `worker_heartbeat.py` (90s) |
| **A user's public handle / directory search** | `users.username`, `services/username_service.py` |
| **Generated avatar (seed → palette + character)** | `utils/avatarSeed.js`, `utils/avatarFace.js` — shared by `Avatar.vue` **and** `remotion/AvatarLoop.tsx` |
| **Delete a conversation (per-side)** | `api/messenger.py::delete_thread`, `dm_conversations.*_cleared_at` |

---

## 3. Hands-free harvest — end-to-end sequence

```mermaid
sequenceDiagram
    autonumber
    participant U as Agent (browser)
    participant API as Cloud API
    participant DB as PostgreSQL
    participant WK as Local worker (IL)
    participant INS as Insurer portal
    participant PH as Agent phone

    U->>API: POST /batches/run  (run all companies)
    API->>DB: INSERT batch(status=pending)
    Note over API,DB: worker alive ≤90s → leave pending<br/>else run inline on cloud
    WK->>DB: CAS claim: UPDATE...WHERE status='pending' RETURNING id
    loop each active credential (sequential — shared OTP inbox)
        WK->>DB: read otp_since = DB clock (BEFORE login)
        WK->>INS: login (real Chrome, IL IP)
        INS-->>PH: OTP SMS
        PH->>PH: OtpFilter.shouldForward (BLOCK›ALLOW›fail-open)
        PH->>API: POST /phone-forward/{token} {message: body}
        API->>DB: INSERT otp_inbox(otp_code, portal_kind tag, received_at=DB clock)
        WK->>DB: _wait_for_otp poll (1s/300s, exact-tag preferred)
        DB-->>WK: code → mark consumed_at
        WK->>INS: submit_otp → download נפרעים + production files
        WK->>DB: ingest_file_bytes (make_active=False, held)
    end
    WK->>DB: merge held files → 1 production + 1 נפרעים workbook (source מאוחד)
    WK->>DB: compute_comparison per category → persist CommissionComparison
```

---

## 4. OTP correctness invariants (do NOT break these)

These look arbitrary; each encodes a fixed production incident.

1. **Anchor `otp_since` on the DB clock, before `login()`.** Not the worker's
   clock (a PC 5 min fast discarded every real code). Before login because some
   portals SMS on credential-submit. — `runner.py::_wait_for_otp`, `_db_utc_now`
2. **Exact company tag beats NULL, via `CASE` sort.** A naive
   `ORDER BY (portal_kind==base) DESC` lets untagged junk (NULL sorts first under
   DESC) steal the code. Codes tagged for *other* companies are excluded. Stops
   cross-company OTP theft in a run-all batch. — `runner.py`, mirrored in `/next-otp`
3. **Body-only forwarding.** The phone drops the sender, so the backend
   re-derives company from body text. Device (`OtpFilter.kt`) and server
   (`otp_routing.py`) share the one **global** `sms_otp_templates` set.
4. **Fail-open on the phone.** Any unlisted-company SMS with a 4–8 digit code is
   still forwarded, so a new insurer never silently drops. BLOCK templates are
   the privacy lever for personal 2FA.

## 4b. Credentials — the login form is DECLARED, not assumed

`portal_credentials` has exactly two value columns (`username` +
`encrypted_password`). Real insurer login forms don't agree with that shape: **מור
asks for THREE fields** — מס' רשיון + ת"ז + טלפון — and `mor.py::_split` reads them
back out of a *packed* `username="<license>|<id>"` and `password="<phone>"`.

The packing used to be invisible to the UI: "הוסף פורטל" rendered a hardcoded שם
משתמש + סיסמה, so a user adding מור had **no field for the phone** — the number Mor
SMS-OTPs. The credential was unenterable, and only rows hand-packed for the dev
account worked. Invariants:

1. **A portal that needs non-default fields declares them** in
   `companies/__init__.py::PORTAL_LOGIN_FIELDS`; `/portal-kinds` ships the spec and
   `PortalCredentialModal.vue` renders it. No portal-specific branching in the Vue.
2. **`target` + list order ARE the packing convention.** Fields sharing a `target`
   are joined with `"|"` in spec order — precisely what the plugin's `_split()`
   parses. Reorder the spec and you silently swap רשיון with ת"ז.
3. **`secret: True` never round-trips.** The password column is encrypted, so those
   fields render blank on edit and blank means *leave unchanged* — never overwrite a
   stored secret with an empty string.

## 4c. Score-gated portals (Mor, Meitav) — the browser must look like a human's

Mor and Meitav are gated by a **reCAPTCHA score**. Nothing about the request is wrong when
they refuse it: Mor answers `400 {"resultCode":"Bad Request"}` — visible to the agent as the
generic `אירעה שגיאה` — to a perfectly formed login. Everything here was established by
measurement on 2026-07-20, after ~9 hypotheses died; the section it replaces asserted a cause
(cold profiles) that is now **refuted**, and that wrong entry is what cost most of the day.

### Status: BOTH PORTALS CONFIRMED WORKING (2026-07-20, agent's worker)

```
מור     success  490 records  מור נפרעים 05-2026.xlsx      period 2026-05
מיטב    success    9 records  מיטב דש עמלות לסוכן.xlsx     period 2026-05
```
Both deliver **נפרעים**, not production — they are gemel/pension houses, so their production
belongs to מסלקה (§12). Fixing them does not move the production totals.

### The configuration that PASSES — do not drift from it

Reproduced green twice from a dev box (`201 {"resultCode":"Success"}` + OTP modal), with real
Windows **Edge** and real Windows **Chrome**, driving our own login flow:

| Setting | Value | Why |
|---|---|---|
| `headed` | `True` | headless is refused outright |
| browser | real Chrome/Edge | bundled Chromium reports `sec-ch-ua: "Chromium"` — a bot brand |
| `--disable-blink-features=AutomationControlled` | **always** | makes Chrome not set `navigator.webdriver`; genuinely false, nothing left to detect |
| `navigator.webdriver` JS patch | **never** for native | `defineProperty` IS detectable (descriptor + `getter.toString()`) |
| `no_viewport` + `--start-maximized` | headed runs | a pinned viewport on a headed browser disagrees with the OS window — a mismatch no real browser shows |
| profile | fresh, **unwarmed** | both winning runs used a brand-new throwaway profile |
| warm-up | **off** (`mor.py`, `_skip_warmup`) | synthetic mouse dwell is itself a signal, and both winning runs did none |

`runner.py` applies the flag/viewport/profile rules; the per-plugin flags are `headed`,
`native_fingerprint`, `use_persistent_profile`.

### What is DISPROVEN — do not re-derive these

- **"A COLD profile is what the score punishes."** Both winning runs were cold and unwarmed.
  What actually fails is a **poisoned** profile: the `_GRECAPTCHA` cookie IS the accumulated
  reputation, so every rejection makes the next attempt start worse. It spirals, and correct
  fixes underneath become invisible — webdriver/payload/token fixes that day each changed
  nothing observable until the fingerprint was also corrected.

  → `runner.py` therefore recycles a profile when it has **never succeeded OR its last run was
  rejected**. The rule is *not* "never succeeded": the warm marker is written once and never
  expires, so a profile that worked for weeks and then rotted stays "proven" forever. That is
  exactly what happened to **meitav** — success 2026-07-19, then four `נסה שנית` rejections on
  07-20 on the same kept profile, while the identical flow on a FRESH profile reached the OTP
  screen. Discarding costs nothing measurable (every green run on record used a brand-new
  profile); keeping a rotten one costs everything.
- **The payload.** `{licenseId=len8, identity=len9, phoneNumber=len10}` is byte-identical to
  what Mor's own Angular form submits. Padding, field order and typing delays are all fine.
  (The licence is **8 digits, NOT zero-padded**; only ת"ז→9 and phone→10 are padded.)
- **A missing captcha token.** It is minted (~1300 chars) and sent — see below.
- **`navigator.webdriver`** as sole cause: setting it False did not, by itself, fix Mor.
- **XSRF.** Mor's server sets **no cookies at all**, so Angular's `X-XSRF-TOKEN` is correctly
  absent for real browsers too.
- **Automation being detectable.** Playwright-driven real Edge/Chrome logs in fine.

### Mor's login, as its own bundle defines it

`curl https://join.more.co.il/agentsportal/main.*.js` — fetchable from WSL, and it settles in
minutes what live runs cannot:

```js
LoginAgentForm = {licenseId, identity, phoneNumber}      // the ENTIRE body
logIn(v) = captchaService.getToken('login')
             .pipe(tok => _login(v, new HttpHeaders({recaptcha: tok})))
getToken(a) = from(grecaptcha.execute(siteKey, {action:a}))   // reCAPTCHA v3
```

**The token is an HTTP HEADER, not a body field.** Body-only instrumentation therefore shows a
flawless payload while the request is refused — that single misreading drove days of work.
Corollary: `g-recaptcha-response` DOES exist under v3, but is filled only *after* `execute()`
resolves, i.e. after the submit click. Waiting on it beforehand can never succeed.

### Invariants

1. **Reproduce locally before theorising.** Windows Python (`/mnt/c/Python313`) driving real
   Edge/Chrome runs the same flow in minutes — the two-Python split already used for Phoenix.
   This is what cracked Mor, after eight live-run hypotheses failed.
2. **Read the portal's own JS bundle** before asserting what it sends.
3. **Never assert a cause you didn't measure.** `אירעה שגיאה` covers a low score AND wrong
   credentials; `mor.py::_classify` reads the server's own words.
4. **A diagnostic must not perturb what it measures.** A probe that called `grecaptcha.execute()`
   itself added a second assessment right before the login — it was removed.
5. **Log which browser binary launched.** `_launch_real_persistent` tries
   chrome → chrome.exe → **msedge** → chromium; a silent Chromium fallback is the worst
   possible fingerprint. `WORKER-LOG … persistent browser=chrome` is the first line to read.
6. **Do not retry a rejected submit.** Every extra submit lowers the score; recovery needs
   ~20–30 min of quiet. `_MAX_SUBMIT_ATT = 1`.

### Meitav — same gate class, DIFFERENT mechanism (measured 2026-07-20)

Meitav sets the identical three flags, so it inherits every runner-level fix above
automatically (flag, viewport, profile recycling). It has **no** warm-up call, so that change
does not apply. Beyond that it is genuinely a different portal, and reproducing it locally
(real Windows Edge, our exact flow) settled three things:

**1. The login WORKS — it is not score-blocked.** Reproduced green:
```
login form painted = True
submit button: {'disabled': False, 'text': 'אישור'}
OTP field visible  = True
POST /v2/api/Login/LoginWithPhoneAgent -> 200 {"actionTarget":"LoginCode","isFailed":false}
```
So `לא נמצאו שדות ת"ז/טלפון` is **not** a DOM change and not a rejection — it is the
hydration race, addressed by the 30 s `_FORM_READY` wait. Meitav runs ~19% flaky; treat a
recurrence as a race to widen, not a login bug to hunt.

**2. reCAPTCHA ENTERPRISE, not v3.** `enterprise.js?render=6LehTw…` (sitekey also at
`globalParam.reCaptchaClient`). The API is **`grecaptcha.enterprise.*`**; `grecaptcha.execute`
is undefined. Measured on the live page:
```
has_grecaptcha=True   has_enterprise=True   plain_execute=False   tok=2148
```
`_probe_recaptcha` used to check `window.grecaptcha.execute` (Mor's shape), so it reported
`execute_ready=False` on a healthy page and told the agent their **antivirus** was blocking
Google — a finding that was never once true. Fixed to read the Enterprise surface, and it now
claims a block only when the script is genuinely absent. **A diagnostic that manufactures its
own false finding is worse than no diagnostic**; this one sent real effort at an imaginary
firewall.

**4. Meitav REQUIRES Edge — Chrome is refused.** The browser brand is not cosmetic. Measured
twice each, same machine, same minute, same fresh profile, same flow:
```
msedge -> 200 {"actionTarget":"LoginCode","isFailed":false}  + OTP screen
chrome -> 401 {"message":"gCaptcha error"}                   -> agent sees "נסה שנית"
```
The server names the cause itself, so this is not inference. The worker had been picking Chrome
only because it heads the default `chrome→chrome.exe→msedge→chromium` ladder — which is why
meitav failed on the agent's PC all day while the identical flow passed on a dev box. **Mor
accepts BOTH channels (201 on each)**, so this is per-portal: `browser_channel = "msedge"` on
the plugin moves Edge to the front, and the full ladder still runs behind it so a PC without
Edge degrades rather than fails. When a score-gated portal fails, TRY THE OTHER REAL BROWSER
before theorising — it is one run and it is decisive.

**3. Akamai Bot Manager sits in front of it.** The page loads an obfuscated sensor from a
random path whose filename is the **hex of the page path**
(`76322f6c6f67696e2f6c6f67696e6167656e74` = `v2/login/loginagent`), plus a `<noscript>`
tracking pixel and a `POST /qwacKJ/` telemetry beacon. That is a second, independent bot layer
Mor does not have. It did not block a real-Edge run — but if Meitav ever starts failing at the
network level rather than the form level, look here first, and do not attribute it to
reCAPTCHA.

## 5. Comparison / merge invariants

1. **Normalize the national ID.** Production drops leading zeros, commission
   keeps them → `_normalize_id` (`id.lstrip('0') or '0'`) reconciles.
2. **Match products by policy number**, handling the compound
   `X-YYY-ZZZZ-N` form (3rd segment = bare account no.). — `_policy_matches`
3. **Exclude stale מאוחד.** The merged batch file is *derived*; when a fresher
   per-company upload coexists, drop just that company's rows from the merge
   (`exclude_from_merged`), never double-count. — `comparison_orchestrator.py`
4. **Multi-production aware.** Production is one file *per company*; never
   `scalar_one_or_none()` it — aggregate with `.in_(prod_upload_ids)`.
5. `period_month` is **filename-first**, then data dates, then `uploaded_at`. —
   `parser_service.py::detect_period_month`

## 6. Claude (AI) invariants

> Chat charts (`<<VIZ:…>>` → `AiVizPanel`): see [`docs/AI_VIZ.md`](AI_VIZ.md) — the panel is mounted once at the `WorkspaceView` root; chat model is `claude-sonnet-5` → `claude-haiku-4-5`.

1. **Forced tool_use** (`tool_choice=save_extracted_document`) → validated dict,
   never text-JSON. Model `claude-sonnet-4-6` → Haiku fallback. — `document_extraction.py`
2. **Literal-value guard.** Every extracted % must appear verbatim in the PDF
   text layer (pdfplumber, or Hebrew OCR if <200 chars) or it's dropped as
   fabricated. — `_normalize_and_validate_rates`
3. **`rates[]` = ongoing נפרעים only.** Scope/היקף/מענק-גיוס/clawback are
   stripped (they'd pollute expected-commission math). Ceilings `0.03` gemel /
   `0.25` insurance are the last guard, plus a FLOOR of `0.03` on premium-based
   fallbacks so a savings rate can't price an insurance premium. — `rate_select.py`

---

## 6b. Commission calculation invariants

Full detail lives in the **`commission-calculation` skill**; these are the ones
you must not break.

1. **Two numbers, never mixed.** *עמלות שהתקבלו* comes from נפרעים files only
   (per company, latest `period_month`). *עמלות צפויות* comes from production ×
   agreements and needs no נפרעים at all. — `api/production.py`, `rate_select.py`
2. **The commission basis is per RECORD, not per category.** `accumulation × rate
   ÷ 12` when `accumulation_based()`, else `premium × rate`. Pension and
   pure-risk are excluded from the accumulation path — that exclusion is a
   deliberate fix; reverting it refiles insurance rows under pension entities.
3. **THE NAME SEAM — the root of a whole class of silent-₪0 bugs.**
   `utils/company_norm.py` has three functions with different jobs:
   `canonical_company` (full legal entity, written into the merged production
   file's `יצרן`), `normalize_company` (collapse key, comparison/AI equality)
   and `company_stem`/`company_residue` (brand + product remainder, **rate
   matching**). **`normalize_company` does NOT invert `canonical_company`** —
   for מנורה, מגדל(savings), אלטשולר, ילין and אנליסט the merged file's legal
   name and the agreement shelf's short name do not compare equal, so rate
   lookup silently returned 0 and whole companies contributed nothing.
   `company_stem` is the fallback tier that closes it.
4. **No silent skip.** Every failure in the expected math is a `continue`.
   `select_rate` returns a `route` for every decision and
   `explain_expected_commission` turns those into a per-company coverage report,
   surfaced at `GET /api/commission-rates/coverage` and in the agreements shelf.
5. **There is no גמל/ביטוח dimension in the comparison.** Production is scoped
   by **company coverage** — a record is judged paid/unpaid only if its company
   appears in the commission set; uncovered companies are returned as
   `uncovered_companies`, never as unpaid. The old category split halved the
   picture and double-counted (802 rows for 624 customers; 97 reported
   `only_in_production` where the truth is 33). `commission_comparisons.category`
   and `debts.category` remain as **passive labels** — nothing branches on them.
6. **`rate_select.py` is the single source of truth.** Dashboard, monthly
   insights and AI chat must report the same number. (`/expected-trend`,
   `insights.py` and `ai_service._rate_for` still re-implement the loop — open.)
7. **A record's company comes from its COMPANY COLUMN, never guessed from the
   product name.** `_extract_short_company` trusts `receiving_company` first and
   only parses the product string when there is no company at all — and then
   only accepts a name `known_company_stem` recognises. It used to guess first,
   and invented insurers: the product `פרודוקציה - חיים` became the company
   "פרודוקציה" for 285 records and `מבטחים יותר` became "מבטחים" for 68, each
   rendering as a fake insurer with real unpaid customers behind it. Sub-brands
   map to their parent (מבטחים→מנורה, אינטרגמל→מור). Both product sides carry
   `company` = short brand (the grouping key) and `company_full` = raw legal
   name; group on `company`, or one insurer splits in two.

---

## 7. Data model — the tables that matter

| Table | Role | Model file |
|---|---|---|
| `client_records` | The 80+ col fact table (production **and** commission rows) | `models/record.py` |
| `file_uploads` | One row per uploaded/harvested file; `file_category`, `period_month`, `is_production`, `company_source` | `models/upload.py` |
| `commission_comparisons` | Persisted `compute_comparison` result per category | `models/*comparison*` |
| `commission_rates` | Claude-extracted agreement rates (incl. `rate_scope`) | `models/commission_rate.py` |
| `otp_inbox` | Forwarded OTP codes, `portal_kind` tag, DB-clock `received_at` | `models/otp_inbox.py` |
| `sms_otp_templates` | GLOBAL regex templates (allow/block) | `models/sms_otp_template.py` |
| `worker_heartbeats` | One row/user; DB-clock `last_seen`, `update_requested_at` | `models/worker_heartbeat.py` |
| `portal_runs` / `portal_run_batches` | Automation run state machine | `models/portal_run*.py` |
| `portal_links` | Shareable customer-portal tokens | `models/portal_link.py` |
| `mailbox_configs` | One per user: `mail_host`, encrypted refresh-token / app-password, `forward_token`, `last_received_at` | `models/mailbox_config.py` |
| `mailbox_processed_messages` | Mail dedup ledger, unique on `(mailbox_id, external_id)` | `models/mailbox_message.py` |
| `dm_conversations` | One row per user PAIR; ordered-pair invariant, denormalized unread/preview, per-side `*_cleared_at` (delete-for-me) | `models/dm_conversation.py` |
| `dm_messages` | Direct messages; `seq` identity column is the poll/page cursor | `models/dm_message.py` |
| `dm_presence` | PERSON liveness (browser open, 50s window) — **not** `worker_heartbeats` | `models/dm_presence.py` |

**Universal rule:** every query filters by `user_id` (strict multi-tenancy).

**The one sanctioned exception:** `api/messenger.py` (`/contacts`, `/search`). A
user-to-user messenger must let one user see that another exists, so those two
queries join `users` without a `user_id` filter. Do not "fix" them. The exposure
is bounded by three things, all load-bearing:
1. `ContactOut` is a strict whitelist — `id`, `username`, `full_name`, `initial`,
   `online`. **Never** `email` / `phone` / `company_name`.
2. `/search` requires ≥2 chars and matches a **prefix** (`LIKE 'q%'`, never a
   leading `%`), so the directory can't be enumerated or read as a substring oracle.
3. `/contacts` returns only people you already have a conversation with.

`users.username` (NOT NULL UNIQUE, `^[a-z0-9_]{3,32}$`) exists to make people
identifiable in that directory *without* exposing an email — `full_name` is
nullable and non-unique, so it can't do the job. `users.avatar_seed` (nullable,
NULL ⇒ derive from `username`) is the seed for a person's generated face.

---

## 8. Frontend — workspace nav chrome & icon system

The top chrome a user sees, top→bottom, is `StockTicker` → `WorkspaceTabs`
(the tab bar) → `CircleMenuIsland` (a React-island radial menu holding
settings/logout, lucide-react by name). **The legacy `WorkspaceHeader.vue` is
dead code — not mounted.**

### `WorkspaceTabs.vue` — two render modes, one tab list

One `tabs[]` array drives both:
- **Home mode** — a grid of premium `.card` "cubes" (icon chip + label + desc).
- **Content mode** — a compact sticky `.strip` of pills (active pill tinted).

Each tab owns a **colour identity** via three CSS vars bound inline
(`--accent`, `--accent-glow` wash, `--accent-ink` text-safe): `production`=cobalt,
`comparison`=green, `commission`=purple, `emails`=magenta, `recruits`=turquoise,
`portal`=sky, `ai`=lavender, `automation`=teal. Tokens live in `App.vue :root`
as `--tab-*` → `CHART_PALETTE`. **Orange is retired (2026-09-26)**: actions use the
tab's colour inside a tab and ink (`--primary` #181818) outside — see the `nifraim-style` skill.

Home-card **hover** = grow + ambient loop (both were subtle traps):
- **Resize**: `.card:hover` scales to `1.14` + `z-index:5` (grows *over*
  neighbours). ⚠️ `@keyframes cardEnter` ends on `scale(1)`; the card MUST use
  `animation-fill-mode: backwards` (not `both`) or the retained end keyframe
  overrides `:hover`'s transform (animations outrank normal rules) and the card
  silently never resizes.
- **Ambient glow**: `<CardAmbientIsland>` mounts a Remotion loop
  (`CardAmbientLoop`) behind the content, tinted to the card's accent, **only
  while hovered** (`v-if="hoveredCard === id"`) → at most one Player alive.

### Icon system — `components/icons/`

Tab glyphs are a **duotone** set, defined **once** (they used to be inline
Lucide strokes duplicated per size per tab):
- `tabIcons.js` — registry of inner SVG markup, id → glyph. Geometry vendored
  from **Phosphor Duotone (MIT)**; each glyph is two `fill="currentColor"`
  layers, the tint at `opacity≈0.2`.
- `AppIcon.vue` — renders `<svg viewBox="0 0 256 256" fill="currentColor"
  v-html=…>` at a `size` prop.

**Why `currentColor`+opacity matters:** colour flows entirely through the
surrounding `--tab-*` token — accent-ink at rest, white on card-hover, grey on
inactive strip pills — with **zero icon-side colour logic**. Recolour a glyph by
changing its wrapper's colour, never the SVG. The registry is reusable for any
future surface (KPI cards etc.) that still uses ad-hoc inline strokes.

### Remotion-in-Vue (RTL gotcha)

Every Remotion Player mounted here needs `direction: ltr` on its **inner** mount
div only (never the positioned root) — the Player centres with LTR-assuming math
and drifts ~half a scene off-box under the app's RTL root. Directional scenes add
`transform: scaleX(-1)` to flow right-to-left; `CardAmbientLoop` is
non-directional so it doesn't. See `remotion/TabHeroLoops.tsx`,
`AutomationHeroLoopIsland.vue`.

---

---

## 9. Messenger — invariants

A floating dock (bottom-right, the only free corner) lets any user DM any other.
It is **deliberately isolated from the worker/portal-automation plane**: it never
imports `api/portal_automation.py`, never reads `worker_heartbeats`, and ships its
own pulse keyframes rather than borrowing the worker chip's CSS.

All under `/api/messenger`, all `Depends(get_current_user)` — **not** `get_paid_user`:
`is_active` means "subscription paid", and a lapsed agent must still be able to
receive and reply or every thread they're in becomes a dead end.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/presence/heartbeat` | mark me online (50s window); returns `total_unread` |
| `GET` | `/contacts` | people I've already messaged (+ presence, unread, preview) |
| `GET` | `/online` | anyone with the app open right now |
| `GET` | `/search?q=` | prefix lookup, ≥2 chars, ≤20 results |
| `GET` | `/poll?since=<seq>` | new INCOMING messages since a cursor |
| `GET` | `/threads/{id}/messages?before=<seq>` | history, newest-first paging |
| `POST` | `/threads/{id}/messages` | send (self-DM 400, 5 per 10s, body ≤4000) |
| `POST` | `/threads/{id}/read` | zero my unread counter |
| `DELETE` | `/threads/{id}` | clear the conversation **for me only** |

1. **Ordered-pair invariant.** `dm_conversations` always stores
   `user_a_id = min(uuid)`, `user_b_id = max(uuid)`, under a unique index. That
   collapses (a,b) and (b,a) onto one row without a hash column. Always build the
   tuple via `ordered_pair()` — never by hand. — `models/dm_conversation.py`
2. **`seq`, not `created_at`, is the cursor.** UUIDv4 has no time order and
   `created_at` ties at microsecond precision under concurrent inserts, so
   `WHERE created_at > :since` can skip or double-deliver. `seq` is a Postgres
   identity column giving a gap-tolerant total order. — `models/dm_message.py`
3. **`/poll` returns INCOMING messages only.** Your own sends never echo back, so
   the client never has to dedupe a polled message against its optimistic bubble.
4. **The presence heartbeat returns `total_unread`.** The always-on 20s beat
   doubles as the low-frequency unread poll, so the collapsed pill's badge stays
   live with zero extra requests. There is deliberately no closed-dock message poll.
5. **Message bodies render as TEXT.** `{{ msg.body }}`, never `v-html`, never
   `renderMarkdown` — that util is safe in the AI sheet only because it is applied
   solely to the trusted `assistant` role. User-authored text through it is stored XSS.
6. **Rate limiting counts rows in the DB**, not an in-process bucket: Railway runs
   multiple uvicorn workers, so a per-process counter would multiply the real limit.
7. **Delete is PER-SIDE.** A `dm_conversations` row is shared by two people, so
   `DELETE /threads/{id}` never drops it — that would erase the other person's
   history. It stamps *my* `a_cleared_at`/`b_cleared_at`; messages at or before it
   vanish from my contacts + thread only. A newer message revives the thread with
   just that message. — `api/messenger.py::delete_thread`
8. **`/contacts` ≠ `/online` ≠ `/search`.** `/contacts` = people I've messaged
   (inner join, bounded). `/online` = anyone with the app open right now, so you
   can discover someone you've never talked to. `/search` = prefix lookup. All
   three are cross-user reads under the same `ContactOut` whitelist.

**Generated avatars.** A person's face is derived from a seed (`users.avatar_seed`,
NULL ⇒ derive from `username`), never uploaded — no storage, no moderation, 64
bytes per user. `utils/avatarSeed.js` (palette) + `utils/avatarFace.js` (character)
are the **single source of truth**, consumed by *both* the static `Avatar.vue` and
the animated `remotion/AvatarLoop.tsx`. If they ever hash separately, the picker's
swatch stops matching the avatar it produces — the preview becomes a lie.
Each feature draws from its own hashed sub-stream (`seed:hair`, `seed:glasses`…):
sharing one stream correlated features with the palette (glasses on 6 faces in 8)
and made the draw *order* load-bearing, so adding a feature rerolled every face.

Under the RTL root, `inset-inline-start` is the physical **right** edge — that is
how the dock pins bottom-right. `inset-inline-end` would put it bottom-left, on top
of `BatchResultsToast`.

---

## 10. Mail intake — הכשרה production arrives by email

הכשרה's portal plugin (`companies/hachshara.py`) downloads **נפרעים only**. Production
is emailed as `Ild_prod_<n>_<agent>_<DDMMYYYY>.zip` — CP862, visual-order Hebrew,
2000-char fixed-width `SP`/`SB`/`RM` members, parsed by `services/hachshara_prod/`.
There is no production portal to add, and there never will be.

```mermaid
graph LR
    A["agent types ONE thing:<br/>their email address"] --> B{"detect_mail_host<br/>MX over DNS-over-HTTPS"}
    B -->|"*.mail.protection.outlook.com"| M["Graph OAuth<br/>Mail.Read + offline_access"]
    B -->|"gmail.com / googlemail.com"| G["IMAP + app password<br/>EXAMINE, read-only"]
    B -->|"anything else / unsure"| R["forward to<br/>hachshara+&lt;token&gt;@…<br/>Resend webhook"]
    M --> S["ingest_mail_attachment"]
    G --> S
    R --> S
    S --> I["ingest_file_bytes → production"]
```

### Invariants

1. **Never ask the user who hosts their mail.** With custom domains the mail *client*
   they name says nothing: an agent reading mail in the Outlook app may sit on M365,
   on Workspace, or on cPanel. Route on the MX record. Detection is a **hint** —
   split delivery, vanity MX and security gateways (Mimecast/Proofpoint) all mislead
   it — so the UI always offers a manual override and `other` is the safe default.
2. **The three paths are forced by the providers, not chosen.**
   *M365*: Exchange Online basic auth is permanently disabled and app passwords are
   blocked with it → OAuth is the only door (free Azure app, **no** CASA).
   *Personal Gmail*: app passwords still work; the OAuth alternative `gmail.readonly`
   is a Google **restricted** scope → annual security assessment, and an unverified
   app's refresh tokens die after **7 days**.
   *Google Workspace*: refuses app passwords entirely → routed to forwarding. Personal
   Gmail is told apart by the **domain**, not the MX (both use `aspmx.l.google.com`).
3. **One seam touches ingest.** All three paths converge on `ingest_mail_attachment`,
   which guards the filename (`^Ild_prod_\d+_\d{4,6}_\d{8}\.zip$`) and size *before*
   parsing, then writes a dedup-ledger row — including for rejects and parse errors, so
   one permanently-bad attachment can't wedge the poller. Swapping a transport (Gmail
   app-password → XOAUTH2) never reaches the parse pipeline.
4. **`external_id` is per-path and must carry its epoch.** Graph message id, Resend
   `email_id`, or `f"{uidvalidity}:{uid}"` — an IMAP uid is unique only *within* one
   UIDVALIDITY, so a server renumber must reset the cursor, not silently skip mail.
5. **Never fold the recipient's local part.** `secrets.token_urlsafe` emits mixed case;
   lowercasing `hachshara+<token>@…` breaks the tenant lookup, and the webhook then 200s
   as "unknown token" and drops the mail **with no error anywhere**. Log unknown-token
   deliveries at WARNING, not INFO. (This shipped once.)
6. **The Resend webhook is the app's first unauthenticated write path.** Verify the Svix
   signature (stdlib `hmac`, replay-windowed) *before* the tenant lookup and before any
   outbound fetch. An unknown token returns **200**, never 404 — mirroring
   `/phone-forward/{token}` so responses can't be used to enumerate tokens.
7. **Errors are CODES, never provider strings.** `AADSTS65001` means nothing to an
   agent, and `imaplib` error text can echo the failed `LOGIN` line *with the password*.
   The backend stores a code in `last_error`; `utils/mailboxCopy.js` maps it to Hebrew.
   `connected_no_mail_yet` is the **normal** state 29 days a month and must not render
   as an error.
8. **Every path fails silently.** Revoked consent, a rotated app password and a wrong
   forwarding rule all look identical to "הכשרה sent nothing this month". The
   `last_received_at` chip is the only thing that distinguishes them — treat it as
   required, not polish.
9. **A refused consent is not an unreachable mailbox, and `error` alone can't tell them
   apart.** Microsoft returns `access_denied` both when the agent presses Cancel
   (`AADSTS65004`) and when the tenant never offered an Approve button at all
   (`AADSTS65001`, user consent restricted to verified publishers). Classify on `error`
   **and** `error_description` (`graph.classify_redirect_error`) — reading only `error`
   labelled every refusal `mailbox_unreachable`, whose copy promises an automatic retry
   for a flow that is waiting on a human to click Approve. (This shipped once: an agent
   declined twice, saw nothing, and every בדיקה answered "החיבור עדיין לא הושלם".)
10. **The consent outcome must be PERSISTED, not just redirected.** The reason lives on
   `mailbox_configs.last_error`, or it dies in a query string nobody reads. And the
   poller must not clobber it: polling a token-less microsoft mailbox always yields
   `not_configured`, which downgrades an actionable reason ("approve it" / "ask your
   admin") into "you never started" — see `_KEEP_OVER_NOT_CONFIGURED` in `poller.py`.

**Deployment gates**: `HACHSHARA_MAIL_ENABLED` (scheduler), `MAILBOX_ENCRYPTION_KEY`
(separate Fernet key from `PORTAL_CRED_FERNET_KEY`), `MS_OAUTH_*`, `RESEND_*`. The API
reports `microsoft_available` / `forwarding_available` so the UI never shows a button
that 503s. Local end-to-end without any provider account:
`backend/scripts/simulate_hachshara_mail.py`.

---

## 11. Windows-native terminal — Phoenix production is a green screen, not a DOM

Phoenix production lives in an Ericom **PowerTerm** terminal, so there is nothing to
select and nothing to click: `scripts/windows/phoenix_win_terminal.py` **injects
keystrokes** (SendInput) at a host that answers only in painted characters. Everything
below exists because a keystroke that misses is *silent* — the run still "succeeds".

```mermaid
graph TD
    A["TERM window exists<br/>(PowerTerm created it)"] --> B{"has the HOST painted<br/>the main menu?"}
    B -->|"black screen<br/>green ≈ 0.3%"| B2["WAIT — keys sent now are SWALLOWED"]
    B2 --> B
    B -->|"painted + stable<br/>green ≥ 5% (menu ≈ 11%)"| C["type 13"]
    C --> D["Enter (submits the 13)"]
    D --> E{"did the menu screen<br/>advance?"}
    E -->|"unchanged = 13 was lost"| E2["retype once → else SystemExit(4)"]
    E -->|"advanced"| F["Enter ×4"]
    F --> G["Down-arrow ×1 (newer month row)"]
    G --> H["Hebrew layout → 'כ' (scancode 0x21) → Enter"]
    H --> I{"did an MU file appear<br/>and stop growing?"}
    I -->|"no"| I2["SystemExit(4) — do NOT ingest"]
    I -->|"yes"| J["parse MU → production"]
```

### Invariants

1. **Never type into a screen the host has not painted.** The `TERM` window exists the
   moment PowerTerm creates it, but the host paints the menu seconds later, and every key
   sent into that gap is swallowed. `wait_for_menu()` polls the **pixels** — painted menu
   ≈ 21% ink / 11% green, the black pre-menu gap ≈ 2% / 0.3%, a 10× margin — and requires
   two identical samples (a half-drawn screen loses keys too). A fixed sleep is a *guess at
   a race*: it won some days and lost others, and an 8s guess is what let the `13` vanish.
2. **Prove the `13` registered; never fire Enters blindly.** Selecting option 13 must
   replace the menu screen. If the screen is unchanged the keys went nowhere — retype once,
   then fail. The digits and the Enter that submits them are typed as **separate** steps so
   `export_1_typed13.png` answers "did the 13 land?" on its own.
3. **The keystroke sequence is exactly:** `13` → Enter → **Enter ×4** → Down-arrow ×1 →
   Hebrew `כ` → Enter. Five Enters, not six. The Down-arrow must be the **extended** arrow
   (`_press_arrow_down()`); a naive VK_DOWN is read as numpad-`2` under NumLock and the
   highlight never moves. `כ` is the raw scancode `0x21` and needs the layout set
   **deterministically** (`_ensure_hebrew`) — a blind `Alt+Shift` flips the already-Hebrew
   screen to English and types `f`. `כ` does nothing until **Enter** submits it.
4. **`grab()` is forbidden between the `כ` and its Enter, and during the transfer.** It
   force-foregrounds and toggles topmost + PrintWindow, which steals the command-field focus
   (the Enter then misses) and stalls the KERMIT receive at block 6 / 0 B/s. Use the
   **passive** `_shot()` (reads screen pixels; touches neither focus nor z-order) when you
   need evidence there. During the transfer, poll the **filesystem** only, and re-assert
   `SetForegroundWindow` every few seconds — Windows throttles a backgrounded window's
   message loop and starves the receive.
5. **"Success" is not evidence of freshness — this is the dangerous one.** When the
   keystrokes silently do nothing, no MU file is written, and the naive next step ingests the
   *newest MU file on disk* — which is **last run's**. Live 2026-07-14: two runs reported
   green while serving **yesterday's 261 records as today's production**. So: no file change
   → `SystemExit(4)`, never exit 0; `_parse_and_ingest` refuses any MU file older than
   `_MU_MAX_AGE_S` (45 min); and every run logs the chosen file's real mtime and age, because
   a stale re-ingest and a real download are otherwise indistinguishable from outside.
6. **Two interpreters, one flow.** The orchestrator runs on the **WSL/app venv** (DB +
   ingest); the GUI sub-steps are shelled to **Windows Python** (`WIN_PY`), which needs
   `pywin32` + `Pillow` — they were never in `requirements.txt`, so the terminal opened and
   just sat there on every machine but the dev box. `_ensure_win_deps()` installs them
   **before** the login, so a missing dep never costs an OTP.

---

## 12. Maslaka Gateway — the clearinghouse is a THIRD plane, and it is LIVE

The מסלקה הפנסיונית is **not a REST API**. It is an asynchronous, file-based vault
exchange: we drop an XML request into an `OUT` folder, their **Transporter** agent syncs it
to the clearinghouse, and their answer lands in an `IN` folder minutes-to-days later. There
is nothing to `await`.

> **Status 2026-09-24: the exchange is PROVEN end-to-end.** Eleven files have been delivered
> and the מסלקה has acknowledged **all** of them with zero defects. Sections below marked
> *(historical)* describe the pre-go-live state and are kept only because the invariants they
> explain still hold. **Response latency is ~2 DAYS, not minutes** — see §12.4.

That forces a **third plane**. Railway has a foreign IP and no static egress; the מסלקה
whitelists **one fixed IP** and installs onto **Windows Server**. So the vault cannot live
in the cloud plane — the same wall that already pushed the portal automation onto an
Israeli worker (§1).

```mermaid
graph LR
    subgraph cloud["☁️ Railway (foreign IP)"]
        API["POST /api/maslaka/inquiry<br/>→ row: status=pending"]
        DB[("Postgres<br/>pension_inquiries")]
        API --> DB
    end
    subgraph gw["🇮🇱 Maslaka Gateway VM — 51.58.32.28 (STATIC)"]
        W["Nifraim worker<br/>submit + poll_and_ingest"]
        F["C:\\Nifraim\\Maslaka\\{TST,PRD}\\{IN,OUT}"]
        T["מסלקה Transporter<br/>(their agent)"]
        W -->|"writes events XML"| F
        F --> T
        T -->|"feedback / holdings XML"| F
        F -->|"reads"| W
    end
    W <-->|"claims pending, writes holdings"| DB
    T <-->|"whitelisted IP"| M["מסלקה vault"]
```

### The Y/N switch — `MASLAKA_ENABLED`

**Now `True` on both planes (flipped on Railway 2026-09-24).** The vault is open, the XSDs are
vendored, and `MASLAKA_AGENT_*` are set. `MASLAKA_VAULT_HOST` stays **false on Railway** — that
is the flag that matters, and it is what keeps the cloud from touching vault folders it cannot
see. *(Historical: it was `False` until 2026-09-24, for the reasons below.)* While it is False:

- the scheduler's poll + retention jobs never fire (`scheduler.py`), **and**
- the two routes that would *transport* anything — `POST /api/maslaka/inquiry` and
  `POST /api/maslaka/poll` — return **503** (`require_maslaka_enabled` in `api/maslaka.py`).
  Read-only routes stay open; they only touch our own DB.

**Flip it to `True` (= Y) only when all three are true:** the מסלקה has opened the vault,
the Transporter is syncing the folders, and `MASLAKA_AGENT_*` are set. Turning it on early
means shipping a guessed XML tree at a regulator.

### Invariants

1. **Never send an unidentified request.** With `MASLAKA_AGENT_*` unset the adapter used to
   emit a literal `TODO(XSD)` as our agent number — and *did*, into a real outbox file.
   `build_events_request` now raises `MaslakaIdentityNotConfigured`. A regulator's vault is
   the wrong place to discover the deployment was never configured.
2. **The outbox write must be atomic.** The Transporter syncs that folder on **its** schedule,
   not ours; a bare `write_bytes` lets it ship a half-written XML. `LocalVaultTransport.send`
   writes `.tmp` then renames (as the SFTP path always did). Inbound is safe already —
   `list_inbox` skips `.tmp` and dotfiles.
3. **The API host is NOT the vault host.** ✅ **CLOSED 2026-09-09.** `submit_inquiry` used to
   run as a FastAPI BackgroundTask, i.e. on whichever host served the request — Railway —
   where `transport.send()` writes to a container disk the Transporter cannot see, reports
   success, and flips the row to `submitted` with the request silently lost. The BackgroundTask
   is gone; `POST /inquiry` now only creates a `pending` row, and `backend/maslaka_worker.py`
   on the Gateway claims it (`SELECT … FOR UPDATE SKIP LOCKED`) and does the transport.
   **There is no inline fallback** — on Railway no send could ever work, so a row waiting for
   the Gateway is correct behaviour, not degraded behaviour.

   This forced splitting one overloaded flag in two, because `require_maslaka_enabled` also
   gated `POST /inquiry` — so invariant #6 (`MASLAKA_ENABLED=false` on Railway forever) meant
   an agent could never create an inquiry at all:

   | | Railway | Gateway VM |
   |---|---|---|
   | `MASLAKA_ENABLED` — the feature is live | true (after go-live) | true |
   | `MASLAKA_VAULT_HOST` — **this host owns the vault folders** | **false** | **true** |
   | creates inquiry rows | yes | — |
   | transports XML / polls the inbox | **no** | yes |

   `MASLAKA_VAULT_HOST` is named as a statement about the host, not a feature, so nobody sets
   it on Railway "to make maslaka work". Design + what is and isn't tested:
   `.claude/plans/maslaka-gateway-claim-loop.md`.
4. **Vault paths must be ABSOLUTE.** `MASLAKA_LOCAL_*` resolve against the process CWD — a
   worker started from a different directory silently gets a *different, empty* vault and
   looks healthy while exchanging nothing.
5. **Transporter = Yes is what makes the code free.** `LocalVaultTransport` is pure
   drop-a-file / read-a-file, so an external folder-syncing agent needs zero changes inside
   `services/maslaka/`.

   ⚠️ **Inbound is classified by `SUG-MIMSHAK` inside the envelope — NOT by the root element.**
   This invariant used to say "root element, not filename", and that was wrong: the stub
   matched `<Feedback>` / `<Holdings>`, names *we invented*. Every real מסלקה file has root
   `<Mimshak>`, so when the first 12 live acks arrived on 2026-09-24 all 12 classified as
   `unknown`. They were not lost — `_route_inbound` leaves what it cannot parse in the inbox
   rather than archiving it, which is the behaviour that saved them. `classify_inbound` now
   reads `SUG-MIMSHAK`: `20` = feedback, `1|2|3` = the holdings / טרום-ייעוץ families.
6. **An ack is the ABSENCE of an error code.** There is no status word on the wire. A feedback
   file is a defect report iff `KOD-SHGIHA-BERAMAT-KOVETZ` or `-RESHUMA` is non-empty. The stub
   looked for `Status in {ACK, OK, ACCEPTED}` — values that do not exist.
7. **Feedback correlates by FILENAME.** `SHEM-HAKOVETZ` echoes the name of the file being
   answered; match it against `PensionInquiry.vault_outbound_filename`. There is no
   `RequestReference` on the wire — that too was our stub's invention.
8. **משוב א' is a receipt, not the answer.** `SUG-MASHOV=1` means "well-formed, accepted"; the
   data arrives later as משוב ב' (FEDBKB) or a holdings file. `_ingest_feedback` deliberately
   stops at `acknowledged` — advancing further would report success on an inquiry holding no
   data at all.

### The static IP is load-bearing — what to do when it changes

`51.58.32.28` (Azure, Israel Central, **Standard SKU + Static assignment**) is whitelisted by
the מסלקה. **It must never change.** Static assignment survives reboot *and* deallocation —
but it is destroyed if the resource is deleted.

**If the Gateway's public IP ever changes, the vault stops working silently** — no error, no
alert, just files that never arrive. That failure looks exactly like a code bug, so check the
IP first, before you debug anything.

| Situation | What to do |
|---|---|
| VM restarted / resized | **Nothing.** Static survives both. Resizing (e.g. B2s_v2 → B2s once quota clears) keeps the IP. |
| Public IP resource deleted / recreated | You get a **new** address. Email the מסלקה the new IP and wait for them to re-whitelist. Nothing works until they do. |
| Rebuilding the VM | **Do not delete the public IP.** Detach it, delete the VM, attach the same IP to the new one. `Delete public IP when VM is deleted` is intentionally **unchecked**. |
| Region change | You cannot move a VM between regions. New VM = new IP = re-whitelist. |
| **Your own home IP changed** (RDP broken) | Irrelevant to the מסלקה — they never talk to your laptop. Only *your* RDP rule breaks. Update the NSG rule `Allow-RDP-Roy` source to your new `x.x.x.x/32`. This happens often; it is not an outage. |

**Do not confuse the two addresses.** The Gateway's IP (`51.58.32.28`) is what the מסלקה
whitelists and must be static. Your home IP is dynamic, changes constantly, and gates only
your own RDP access.

Full setup + IP-change runbook: **`maslaka-gateway` skill**.

---

### 12.3 The XSDs — the wire format is never inferred

**All 18 official schemas are vendored** under `backend/tests/fixtures/maslaka/xsd/`, from
<https://www.swiftness.co.il/agents/קבצים-עדכניים-לעבודה-מול-המסלקה/>. That directory is **the
spec, not test data** — `services/maslaka/xsd.py` loads from it at runtime.

| Interface | Version | Schema file | We SEND? |
|---|---|---|---|
| **ממשק אירועים (Events)** | **007** | `events_007.xsd` | **YES — the only one we send** |
| משוב מנהלי והתראות (Feedback) | 009 | `feedback_009.xsd` | no — we RECEIVE (FEDBKA/FEDBKB) |
| אחזקות / טרום-ייעוץ | 009 | `kupotgemel`, `karnotpensiahadashot`, `karnotpensiavatikot`, `hevrotbituah` | no — we RECEIVE |
| יתרות פיצויים | 005 | `pitzuim_{9300_9302,9301_9303,9305_9306}_005.xsd` | no — employer/institution role |
| ניוד | 003 | `niyud_{haavaraamit,hizuncaspi,hizunminhali,nispachpigurim,nispasha}_003.xsd` | no — fund-to-fund |
| מעסיקים | **006** | `maasikim_{shotef,shliliim,mesakem,shnati}_006.xsd` | no — employer role |

**A בעל רישיון sends EVENTS and nothing else.** The other 17 exist so we can *validate and parse
what arrives*, or belong to roles we do not hold. "We have 18 schemas, let's send more of them"
is not a diagnostic step.

⚠️ **The savers page is stale; use the agents page.** `/savers/…` lists מעסיקים as **005**;
`/agents/…` lists **006** (eff. 26/07/2026) and that is what is vendored. Swiftness support has
also circulated a link to the **006** Events schema — do **not** downgrade from 007.

**Validate against the XSD; never infer from samples.** Reverse-engineering from the 13 vendor
samples produced four fatal defects that XSD validation caught in seconds — most notably
`KOD-SVIVAT-AVODA`, which is **1 = TEST, 2 = PRODUCTION**, and which we had inverted. Every
sample is a `.DAT` production file carrying `2`, so the samples fit both readings and could
never have settled it; the schema's own `<xsd:documentation>` says it outright.
`tests/test_maslaka_xsd_validation.py` validates all 10 action codes on every run.

**Events action codes** (`KOD-EIRUA`), all schema-valid:

| Code | Meaning | Needs customer | Sent live? |
|---|---|---|---|
| 1700 / 1900 | grant / cancel ייפוי כוח | yes | 1700 ✅ |
| 2000 / 2100 / 2500 | production report: one-off / monthly / cancel | no* | 2000 ✅ |
| 9100 / 9101 / 9102 | טרום-ייעוץ information request | yes | 9100 ✅ ×3 |
| 9200 / 9201 | אחזקות information request | yes | not yet |

\* semantically customer-less, but the XSD still makes `MISPAR-MEZAHE-LAKOACH` mandatory and
not nillable. The builder **refuses** rather than invent one (`allow_placeholder_identity` is a
preview-only escape). Whose identity belongs there is an open question for Swiftness.

### 12.4 The live exchange — what was actually sent and answered

| | |
|---|---|
| Vault | `558638623_558638623` · TEST `mft-trn.swiftness.co.il:20022` · PROD `mft.swiftness.co.il:20022` |
| **We upload to** | their **`/FROM/`** |
| **We poll** | their **`/TO/`** and `/REPORTS/` |

The asymmetry is correct — the directory names are from the **מסלקה's** point of view. Do not
"fix" it.

**Eleven files sent, eleven acknowledged, zero defects.** Six on 2026-09-10 (hand-dropped, before
the Gateway worker existed), five on 2026-09-22 (the first ever built and transported by the app
itself). On 2026-09-24 at 09:37 UTC, **12 FEDBKA files** arrived: every one `SUG-MASHOV=1`, every
error field empty. **Our XML is correct, confirmed by the regulator rather than by our own
validator.**

⚠️ **Turnaround is ~2 DAYS.** An 8m28s figure derived from three vendor FEDBKA samples was
treated as an SLA and drove a false "their vault is dead" diagnosis across 2026-09-22. It is not
an SLA — the circular's **3 business days** is the real number. **Silence for hours, or a day, is
normal. Do not escalate it as an outage.**

Bulwarx logs `File size (KB): 0.07421875` for **every** upload — 8+ different files, identical
value. It tracks the remote path length, not the file. Our payloads are ~3.9 KB. It is not
evidence about content.

### 12.5 Two gates before customer data — do not confuse them

| Gate | Who signs | How often | Unlocks |
|---|---|---|---|
| **שיוך לבית תוכנה** | the **agent** | once per agent | the agent may transact through our vault at all |
| **ייפוי כוח** (event **1700**) | the **customer** | once per customer | a 9100 may return *that saver's* data |

**Nifraim is a בית תוכנה** (ח.פ `558638623`): ONE מסלקה account and ONE vault for every agent on
the platform. Each agent signs the מסלקה's `טופס שיוך לבית תוכנה` and sends it to
`helpdesk@swiftness.co.il`; approval links them to our ח.פ. Modelled by
`maslaka_agent_links` + `services/maslaka/association.py` + `/api/maslaka/association/*`.

**Do NOT give each user their own `MASLAKA_AGENT_ID`.** The sender stays the global Nifraim ח.פ;
the *acting agent* varies per request inside `YeshutGoremPoneLemislaka` (`SUG-PONE=3` מפיץ,
`SUG-KOD-MEZAHE-PONE=3` ת.ז, `MISPAR-MEZAHE-PONE`, `SHEM-GOREM-PONE`) — a block we currently send
**entirely nil**.

**UNCONFIRMED, ask Swiftness:** as a בית תוכנה should `KOD-SHOLECH` become `6` (לשכת שירות) and
the filename direction `006`, instead of today's `3` (מפיץ) / `001`? A vendor FEDBKA sample acks a
`006000511511511EVENTS…` file, which supports it — but our `001`/`3` files were accepted with
**zero defects**, so this is an *entitlement* question, not a validity fix.

**The 1700 we sent is NOT a real ייפוי כוח.** The builder emits `<YipuiKoach/>` and
`<mismachim/>` **empty** (self-closing — a regex for `<YipuiKoach>…</YipuiKoach>` reports them
*absent*, which misleads; dump the tree instead). A valid one needs ~30 fields — licence number
and type, both signature dates, validity, the full address block — plus a signed PDF attached as
`…<seq>_001.PDF`. **This is the real blocker for customer data.**

### 12.6 Clocks and filenames

**The wire clock is ISRAEL LOCAL TIME, everywhere.** `filenames.maslaka_now()` is THE single
definition; `events.py` imports it rather than keeping a copy. The Gateway runs **UTC** and the
dev box runs **IDT**, so `datetime.now()` is correct on exactly one of them and `utcnow()` on the
other — and **the tests run on the dev box**, which is why a UTC filename bug survived a fully
green suite until a live Gateway send exposed it (`…174253…` in the name over `204253` in the
payload). Any test that compares a timestamp to the host clock is blind to this; the guard
asserts `maslaka_now() - utcnow()` is 2–3h, which is host-independent.

**Filename grammar** (נספח ו'): `AAA` direction · `BBBBBBBBBBBB` sender zero-padded to 12 ·
`CCCCCC` service · `PPP` product family · `VVV` version · 14-digit `YYYYMMDDHHMMSS` ·
`EEEE` daily sequence · `.DAT` (production) or `.TST` (test). The suffix and
`KOD-SVIVAT-AVODA` must agree — `environment()` returns both from one call so they cannot
diverge. The sequence must be unique per sender per business day: identical sequence → identical
name → the Transporter uploads one and **silently drops the rest**.

*Regenerate this map when the two-plane topology, the OTP routing, the mail-intake
routing, or the comparison/merge selection logic changes — those are the parts a new
session cannot safely infer from reading one file.*

## 13. Monthly cycle (מחזור) — the ONLY trigger of portal automation

Since 2026-09-28 agents never run automation by hand. `services/cycle_service.py` is the
whole domain; `GET /api/cycle/status` is the single source for every cycle-aware UI.

```mermaid
flowchart RL
  S[signup] --> L[Production tab LOCKED<br/>rest of app open]
  L --> C1[first 21st · 06:00 IL<br/>signed before the 21st → same month, else next<br/>cycle batch queued pending → worker]
  C1 --> N[נפרעים of the month before]
  SH[שיוך SUBMITTED before 27th] --> MS[15th next month<br/>מסלקה 2100 production]
  N --> CMP{production for period?}
  MS --> CMP
  U[manual upload — only after the cycle batch ended,<br/>filed under the cycle period] --> CMP
  CMP --> R[comparison_ready notification]
```

- **Cycle** = `CYCLE_DAY` (21) at `CYCLE_HOUR` (06:00 Asia/Jerusalem). Its period is the month
  **before** the cycle month (21/10 → September). Hourly `run_cycle_tick` (scheduler, :00) queues
  and catches up idempotently; the partial unique index `(user_id, cycle_period) WHERE trigger='cycle'`
  makes a double fire a no-op.
- **First cycle depends on the signup day** (changed 2026-09-28; it used to be "always next month"):
  - Signed up **before the 21st** (day 1–20, Israel time): that month's 21st. Signed 1/8 → 21/8 downloads July, and the agent uploads July production manually.
  - Signed up **on or after the 21st**: next month's 21st (28/9 → 21/10).
- **מסלקה timing**: שיוך SUBMITTED before `MASLAKA_CUTOFF_DAY` (27) of M → first production on the
  15th of M+1, else M+2. A cycle whose production landed by its month's 15th is `production_source=maslaka`
  (no upload); otherwise `manual`.
- **`CYCLE_LAUNCH` ("2026-10")** — cycles before it are never queued. Without it, deploying would fire
  last month's cycle for every existing user at once. Pre-launch users keep legacy upload behaviour.

### New customer — the cycle method (what a new agent goes through)

Two dates decide everything, and both come from the server:

- **Signup date** (`users.created_at`): gives the **first cycle**. Before the 21st it's the same month's 21st; on or after the 21st it's next month's.
- **שיוך SUBMITTED date** (`maslaka_agent_links.submitted_at`): gives the **first מסלקה production**.
  - Submitted **before the 27th** of month M: the 15th of M+1.
  - Submitted **on or after the 27th**: the 15th of M+2.

Each cycle then picks its production source, `production_source_for_cycle(y, m, maslaka_first)`:

- **`maslaka`** when the first מסלקה production is on or before the 15th of the cycle month. Nothing to upload.
- **`manual`** otherwise. The agent uploads production for that cycle's period, and only after the cycle download ended.

**Path A — early signup, on-time שיוך.** Signup and שיוך on 19.9, before the 21st and the 27th:

| When | What happens | Production tab |
|---|---|---|
| 19.9 → 21.9 | Setup wizard; the rest of the app is open | **Locked**, countdown to 21.9 |
| 21.9 06:00 | Cycle 1: August נפרעים download; source `manual` (the מסלקה starts 15.10) | Upload refused until the batch ends, then a **big "upload August production" call** |
| 15.10 | The מסלקה sends September production (2100) | — |
| 21.10 06:00 | Cycle 2: September נפרעים; source `maslaka` | Small מסלקה icon in place of the upload; comparison runs on its own |

**Path A2 — early signup, no מסלקה yet.** Signup 1.8, with the cycle already running: 21.8 downloads July נפרעים and the agent uploads July production manually. Local test user `aug-signup@test.com`.

**Path B — late שיוך.** Signup and שיוך on 28.9, on or after the 27th. Walked end to end on 2026-09-28:

| When | What happens | Production tab |
|---|---|---|
| 28.9 → 21.10 | Setup; first מסלקה production shown as 15.11 | **Locked**, countdown to 21.10 |
| 21.10 06:00 | Cycle 1: September נפרעים download | Upload refused (403 `waiting`) until the batch ends |
| 21.10, batch ended | `upload_production` email + modal | **Big "upload September production" call**. The upload is forced to September, and `compare_now` runs the comparison |
| 15.11 | The מסלקה sends October production | — |
| 21.11 06:00 | Cycle 2: October נפרעים, source `maslaka` | Upload refused (403 `maslaka`). The upload **shrinks to a small מסלקה icon** (`.gate-icon`, tooltip "arrives on the 15th") |

**Other cases:**

- **Signup on time, שיוך late** (signup 19.9, submitted 5.10 → 15.11): same as path B. The first cycle comes from the signup date; the source comes from the submitted date.
- **No שיוך, or rejected:** `manual` every cycle. Each 21st asks for that month's upload, and the wizard and מסלקה tab keep showing the next deadline (`maslaka_deadline` / `maslaka_if_submitted_now`).
- **Worker offline at 06:00:** the batch stays `pending`, the agent gets `worker_waiting`, and the worker claims it when it comes online. The upload window opens only after that.

**Production-tab state machine** (`ProductionTab.vue`, all from `/api/cycle/status`):

```
locked ─(first 21st 06:00)─► cycle batch pending/running ─► batch ended ─┬─ source=manual → upload OPEN (big CTA / needs_production_upload banner)
                                                                          │                  → uploaded → dashboard + small upload icon
                                                                          └─ source=maslaka → no upload; small מסלקה icon (tooltip)
```

### Dates the agent sees (2026-09-28)
`GET /api/cycle/status` also returns:

| Field | Meaning |
|---|---|
| `signup_at` | `users.created_at` in Israel time. The first cycle is derived from it. |
| `maslaka_submitted_at` / `maslaka_approved_at` | From `maslaka_agent_links`. |
| `maslaka_first_auto` | The 15th the first מסלקה production lands (27th rule, from submitted, else approved). |
| `maslaka_deadline` | The last day that still makes the next 15th: the 26th this month, or next month's once today is ≥ 27. From `cycle_service.maslaka_deadline()`. |
| `maslaka_if_submitted_now` | The 15th a submission today would give. |
| `server_now` | The server's clock (honours `CYCLE_NOW_OVERRIDE`). `stores/cycle.js` keeps the skew against the browser, and every countdown uses `cycleNow()` / Remotion `skewMs`, so a PC with a wrong clock never shows a wrong countdown. |

- **Pure helpers + tests:** the 26th vs 27th around midnight Israel time, and the year rollover.
- **One wording source:** `stores/cycle.js`: `signupLine`, `maslakaLine` (tone todo / wait / ok) and `MASLAKA_RULE`.
  - Surfaces that use it: the cycle widget (date chips + a "נרשמתם" rail marker), the locked Production timeline, wizard step 5, the מסלקה tab header, and the admin dashboard (`expected_first_production`).
- **The UI never recomputes the rule.** Where it compares dates, it compares plain `YYYY-MM-DD` strings, not `Date` objects across time zones.

### Upload-pending moment (the agent's part of the month)
When `needs_production_upload` is set, the upload call is the only message:

- **Home widget:** turns production blue with the chip "ממתין לפרודוקציה" and the title "עכשיו: להעלות את הפרודוקציה של <month>". Its button goes to the Production tab.
- **Alarm clock and rail icon:** say the same thing.
- **The `upload_production` notice:** plays the Remotion `CycleGears` scene: ONE big hand-drawn gear (the strokes draw on) that is missing one tooth. Its hub carries a green ✓ (נפרעים in), and its inner ring is green except a blue dashed stretch under the gap. The missing tooth (the agent's production, blue with an upload arrow) floats above the gap, It opens with a fast spin that eases to a stop over 3s (3 whole turns, so the gap lands back at the top), then keeps trying to turn, catching and snapping back. While the pointer is on it the gear spins (real time, `hoverStartMs`/`hoverEndMs` props), and on leave it eases to a stop on a whole turn. `RemotionLoopIsland` re-renders the same Player when `inputProps` change, so it keeps its frame. The copy reads "הורדת דוחות נפרעים הסתיימה" and says when the system goes automatic (the 21st of the month of `maslaka_first_auto`, else of `maslaka_if_submitted_now` plus the שיוך deadline). The only button is the upload.
- **The agent's FIRST cycle:** the drawing is slower and green emphasis strokes burst around the gear once. No confetti.
- **Setup wizard:** the notice mounts only while the full-screen wizard is closed, because the wizard used to cover it.

### Simulating future cycles locally
`CYCLE_NOW_OVERRIDE` (config) sets the instant that `cycle_service.utc_now()` returns. Start local uvicorn with it (e.g. `2026-11-21T09:00:00+02:00`), and set the same instant on the browser clock (Playwright `page.clock.install`) to walk a user through the upcoming 21sts. **Never set it on Railway.**

Path B above was verified this way.

- Under a fake clock, a batch queued by the tick still gets the real `started_at`, so a spurious `worker_waiting` fires. It's a simulation artifact.
- Date math for every path is covered in `tests/test_cycle_service.py` (`test_scenario_*`).

### Invariants
- **No manual run for agents.** `POST /batches/run` and `/credentials/{id}/run` are admin-only
  (`_require_manual_run_allowed`); the UI hides every run button unless `user.is_admin`.
- **A cycle batch never runs inline on Railway.** It is inserted `pending`; only the worker claims it.
- **A PENDING cycle batch is never reaped** — not by `_recover_orphan_batches` (API) and not by the
  worker's startup `_reconcile_orphans`. It is the month's work waiting for the worker. The claim sets
  `started_at = now` so the running-age reaper counts from the claim, not the (days-old) queue time.
  ⚠️ The worker-side half ships in the BUNDLE — every worker must self-update before a cycle fires.
- **Manual production is gated server-side** (`api/cycle.manual_production_window`): 403 +
  `X-Cycle-Gate: locked|maslaka|waiting`; when allowed, the upload's `period_month` is FORCED to the cycle
  period. `/api/uploads` checks after parsing (uncommitted ingest → rollback on refusal).
- **Only the Production tab locks**, never the app. Admins are never locked.
- **Notifications** (`cycle_notifications`, UNIQUE user+kind+period) are emitted only by the server tick
  (the worker has no SMTP): `worker_waiting`, `upload_production`, `cycle_failed`, `comparison_ready`.
  Each is emailed once (Resend) and shown once in `CycleNotificationModal`.
- **Manual run is admin-only, also before launch** (decided 2026-09-28): `cycle_service.manual_run_allowed` = `is_admin`, exposed as `manual_run_allowed` on the status; the button shows only for admins as "הרצה ידנית (תמיכה)". Agents who already have production are never locked.
- The frontend's `hydrateBatch` ignores `pending` batches (a waiting cycle batch is not a live run);
  `stores/cycle.js` hands it to the progress widget when the worker flips it to `running`.

UI: `CycleLockedState.vue` (locked tab, Remotion `CycleCountdown` countdown + hand-drawn strip),
`CycleEmotionClock.vue` (home, ≥1360px: a line-drawn alarm clock right of the cards — live countdown in the dial read like a clock (hours left, seconds right), month-progress arc, subtle ring; mood = motion only), `CycleRailIcon.vue` (small alarm clock in the top-right corner for tabs/smaller screens). The notification bell lives in the `HomeSidebar` rail (`:show-bell`), falling back to the corner only where the rail is hidden or ≤720px tall; exactly one bell is mounted because it owns the store poll → popover `CycleHomeTimer.vue` (Remotion `CycleWidget` ring + month rail), the cycle card in
`PortalRunAllBar.vue`, the `maslaka` + "first cycle" steps in `useSetupPipeline.js`.
Tests: `backend/tests/test_cycle_service.py` (date math for every scenario).

## 14. Agreement requests — the wizard emails insurers for the commission agreement

`services/agreement_requests.py` + `/api/agreement-requests` + `AgreementRequestsPanel.vue` (inside the
setup wizard's "מדף ההסכמים" step — no navigation away).

- Companies = brands of the agent's portal logins (`PORTAL_META`) + their production book
  (`receiving_company` → `company_stem`) + existing `company_contacts`; a brand-new agent gets
  `COMMON_INSURERS`. Identity is `company_stem`, never the display string.
- Sending goes FROM the agent's mailbox via `mail_intake.send.send_as_agent` — **Gmail app-password
  only today** (Outlook consent is Mail.Read). The panel says so instead of offering a dead button.
  Each send upserts the company contact and stores `sent_message_id` on `agreement_requests`
  (one row per user+company).
- Follow-up: `run_agreement_request_poll` (every 15 min, 45-day window) → `find_messages_matching`
  on the contact addresses; a reply = In-Reply-To/References ∋ our Message-ID, or from the contact
  after `sent_at`. PDF attachments are loaded by calling `api.ai_documents.upload_document`
  itself (rates_only) — the exact manual-shelf path (sha dedupe, Claude extraction, rate upsert,
  race handling). Status: sent → replied (no PDF) | imported. Non-PDF replies are not imported.

## 15. Setup wizard (welcome) — full-screen, one page per step

`SetupPipelineModal.vue` + `composables/useSetupPipeline.js` (steps, copy, done-detection, flags) +
`utils/setupState.js` (open / leave / resume). Opens for every new agent until setup is completed.

| # | id | Done when | Action |
|---|---|---|---|
| 1 | phone | phone-forward token exists | PhoneForwardModal (stacks above, z 1300) |
| 2 | worker | worker online or ever connected | download installer; live install telemetry |
| 3 | mail | mailbox connected (`/mailbox`) | opens **Nifraim Mail Agent** (MailAgentModal) |
| 4 | agreements | agreement docs/rates exist OR requests sent | `AgreementRequestsPanel` **inside** the wizard (§14) |
| 5 | maslaka | שיוך submitted/approved | MaslakaTab (association wizard) |
| 6 | portal | ≥1 portal credential | PortalAutomationTab → add-portal modal |
| 7 | run | first cycle succeeded, or all other steps done | informational (the cycle runs itself, §13) |

- **Layout:** full-screen (`100vw × 100vh`). Left: the step's Kling loop (`assets/welcome/step-<id>.mp4`,
  poster `step-<id>.webp`) with an outlined `NN/07` number top-right. Right: kicker, two-colour title
  (`StepTitle` wordmarks / `split`), one line, the action, Back/Next + a numbered step bar. Phones: picture
  becomes a top banner. The messenger dock is unmounted while the wizard is open (it would cover Back).
- **Leave / resume invariant:** steps whose action lives elsewhere call `leaveSetupFor(id)`; the surface
  that completes it calls `resumeSetupIfAway(id)` (portal saved, Mail Agent closed, שיוך submitted) and a
  "חזרה להפעלת האוטומציה" pill shows while away. On reopen the wizard re-bootstraps and lands on the
  first incomplete step.
- **Bell** lives in the `HomeSidebar` rail (`:show-bell`); the corner only when the rail is hidden or
  ≤720px tall. Exactly one `NotificationBell` is mounted (it owns the store poll).
- **Adding/replacing a step picture:** Kling `text_to_image` 2:3 in the step colour (surreal pastel 3D) →
  crop the bottom ~7% (watermark), re-centre 2:3, 900×1350 webp → upload the cropped PNG with
  `file_upload` → `image_to_video` kling-video-v3_0, 5s, first = tail frame (seamless loop), no audio →
  ffmpeg crop the bottom 8% + scale 736×1104, h264 crf 27, `+faststart`, `-an`; crop the still the same
  way so poster == first frame. The account runs ONE video job at a time. `import.meta.glob` picks the
  files up — no code change.
- **Mail Agent connect window** (`HachsharaMailModal`, `purpose="general"` from Mail Agent): wide 2-pane,
  Remotion `MailAgentLoop` (reads mail → drafts reply from data → sends on approval → loads agreements),
  Gmail app-password as 3 step cards. Same window serves הכשרה intake with its own copy.

## 16. Admin operations dashboard (`/admin` → "תפעול")

`services/admin_operations.py` → `GET /api/admin/operations` (admin-only, `get_admin_user`) →
`components/admin/AdminOperations.vue`, the default tab of `AdminView`. Reached from the sidebar item
**ניהול** (admins only). Auto-refresh 30s.

- **Per agent:** worker (online ≤90s heartbeat, host, last seen, active portals) · monthly cycle state for
  the CURRENT period (`locked` before their first cycle → `prelaunch` → `no_portals` / `not_queued` /
  `queued` / `waiting_worker` / `running` / `success` / `partial` / `failed`, + last batch of any
  trigger) · Mail Agent (connected, can-send = Gmail app-password, last error, watched senders, 30-day
  mails received/sent) · מסלקה (association status, inquiries by status, holdings → distinct customers,
  last update) · agreement requests by status.
- **Summary KPIs** + filters (דורש טיפול = failed / waiting_worker / not_queued / partial / שיוך rejected /
  mailbox error). One grouped query per area; latest batch via `DISTINCT ON (user_id)`.

## 17. Nifra Agent (office agent, was סוכן המשרד) + the data map — the back-office AI that works for the agent

The agent's back-office AI speaks first. **Nifra Agent WRITES, it does not show tickets** (user rule 2026-09-29): on open, `GET /api/office-agent/narrate` has Haiku (`narrate()`, `NARRATE_SYSTEM`) turn the cards into a greeting + ≤5 lines, each tied to a card `ref`; the panel streams them one after another (`AiStreamingText`) and ends a line with ONE inline link that opens its action in place (draft to approve, contact to add). The narration must not invent times/amounts; the cards stay the source of truth behind it (cached per user by card signature). A short ask box answers in ≤3 plain sentences and ends with a step. It is not a chat. It owns no new data; it **speaks for two workers** and reads the **data map**.

```mermaid
flowchart RL
  MA[Mail Agent<br/>triage · summary · draft] --> OA[office_agent.brief<br/>greeting + cards by urgency]
  CA[collection_agent<br/>unpaid per insurer · draft · follow-up] --> OA
  DM[data_map<br/>Markdown site, drill-down] --> ASK[POST /api/ai/agent<br/>services/agent — §17c]
  OA --> NR[office_agent.narrate<br/>greeting + ≤5 lines → card refs]
  NR --> UI[OfficeAgentPanel = Nifra Agent]
  ASK --> UI
```

- **Code:**
  - Backend: `services/office_agent.py` and `api/office_agent.py` (`GET /api/office-agent`, `GET /narrate`, `POST /ask`, `GET /map?path=`).
  - Frontend: `stores/officeAgent.js`, `OfficeAgentPanel.vue` (streamed lines, aurora + ThinkingOrb), `NifraAgentIcon.vue` (live ThinkingOrb in a breathing glass ring, under the cycle clock), `components/ui/AiStreamingText.vue`.
- **Cards:**
  - Open Mail Agent items (`mail_items`, 14 days): send the draft / make a draft / import the file / done.
  - Open collection cases: approve and send / add the contact / remind / read the reply and resolve.
  - Order: `PRIORITY` (insurer replied, then customer question, then reminder due, …).
  - Every action goes through the EXISTING endpoints (`/mail-agent/items/*`, `/collection-agent/cases/*`). **Sending is always the agent's click.**

- **Actions (it DOES, not only answers — 2026-09-29):** `ask()` runs on **Sonnet 5** (`ASK_MODEL`; Haiku kept asking for details instead of acting) with the recent panel turns as `history`, and has two more tools beside `open_page`, both in `services/agent_actions.py`:
  - `propose_email` prepares a mail to any address.
  - `propose_meeting` schedules a meeting. It becomes a real **iCalendar REQUEST invite** (accept/decline in Gmail/Outlook) to the invitee, with a Cc to the agent. There is no Google Calendar consent (the mailbox is IMAP/SMTP), so the invite IS the scheduling channel.
  - The tools only PREPARE. `ask` returns `{answer, proposal}`; the panel shows an editable sheet, and **`POST /api/office-agent/act` sends only on the agent's approve click**, via `send_as_agent`. The only question it may ask is a missing recipient email. Tests: `tests/test_agent_actions.py`.

- **@ contacts:** typing `@` (or the @ button) in the ask box opens a search. `GET /api/office-agent/contacts?q=` returns customers from the active production files (name, ת.ז, email/phone), saved insurer contacts and mail senders. The picked contacts go with the question as `mentions`, so the agent gets the exact ID and email.
- **No false "done":** if the model's final text claims it prepared something (`הכנתי` / `מחכה לאישור`) but no proposal exists (the tool was never called, or it was cut off by `max_tokens`), it is sent back once to call the tool. Otherwise the answer says it failed. It never claims an action that wasn't prepared.
- **Every production customer is on the map:** `load()` adds each customer from the active production files who isn't in the last comparison (`ctx.extra`), so name/ID search and customer pages match the app's own search.
- **`top.md`:** ranks the biggest customers by accumulation, premium and commission received (for "הלקוח הכי גדול").

- **The agent's jobs as computed pages (`services/agent_insights.py`, 2026-09-29).** Python computes each page; the model only narrates it:
  - `reconcile.md`: expected (agreements) vs paid נפרעים per insurer; ₪0 / below-agreement lines; active policies with no נפרעים line; insurers that sent no file.
    - A **suspicious expected** (> ₪5,000 and > 50× paid, e.g. a pension rate applied to the balance) is listed apart and kept out of the gap. It is most likely a calculation error, not a debt.
  - `policy/<n>.md` answers "did I get paid on policy X" (₪0 is shown as ₪0, not as paid).
  - `retention.md`: arrears/cancellation **signals** (active, nothing paid this period) and dormant funds with a balance.
  - `crosssell.md` + the customer page's "תמונת תיק": rule-based overlaps, consolidation, dormant funds, missing cover — **in this agent's book only**.
  - `tasks.md`: open mails and insurer follow-ups.
  - **Market returns and fees now exist** (official גמל-נט/פנסיה-נט/ביטוח-נט, §17c). **Still not in the data, so the agent says so:** policy end dates (renewals), birth dates (age-change alerts).
- **Action tools only on an explicit ask (`wants_action`):** `propose_email` / `propose_meeting` are offered only when the message, or the agent's previous one, contains an action verb (שלח/תכין/קבע/תזכיר/תענה…). Otherwise the model gets `open_page` only, so "אילו משימות פתוחות יש לי?" is answered and not turned into a drafted email.
- **Mail Agent customer lookup** (`mail_agent/context.py`) also matches the sender's **name** against production first+last name, trying every split point and either order, but only when exactly ONE customer matches. `[להשלים]` stays only for data that truly isn't there.

### 17a. The data map (`services/data_map.py`) — the agent's data as Markdown the AI navigates

The AI never gets one giant dump. It gets `index.md` (categories, a one-line fact each, links) and **drills down** with the `open_page` tool, following the connections the answer needs:

```
index.md ─┬─ companies.md ──► companies/<key>.md   production · paid/unpaid · נפרעים received ·
          │                                        agreement rates · contact · open mail ·
          │                                        collection case + next step · unpaid customers ─► customers/<id>.md
          ├─ unpaid.md  ──► companies/<key>.md
          ├─ mail.md    ──► companies/<key>.md · customers/<id>.md
          ├─ agreements.md ─► companies/<key>.md
          └─ search/<name>.md   (the agent says a NAME, not an ID)
```

- **Rendering:** pages are rendered **on demand** from one loaded `MapContext`: the latest merged comparison, rates, contacts, collection cases and open mail. A book has hundreds of customers, so only the pages the AI opens are built.
- **Safety:** read-only and user-scoped. Links are the exact paths `open_page` accepts.
- **The ask loop:** superseded by Nifra AI v2 (§17c) — both ask boxes stream from `POST /api/ai/agent`; `open_page` is one of its tools. (`office_agent.ask` / `POST /office-agent/ask` remain as the legacy path.)
  - **Invariant:** answers only from the pages it opened. When something isn't there, it says so and suggests what to check.
  - The reply blocks are re-sent as **plain dicts**, because re-sending the SDK objects trips its serializer.
- **Extending it:** new capabilities (tasks, client-file gaps, renewals) plug in as NEW pages and cards, not as a bigger prompt. Add a page renderer and a link from `index.md`.

### 17c. Nifra AI v2 — one agent, typed tools, fast answers (2026-10-02)

Both the home chat (`AiChatWidget`/`AiConversationSheet` → `stores/chat.js`) and the Nifra Agent ask box (`stores/officeAgent.js`) stream from **`POST /api/ai/agent`** (`api/ai_agent.py` → `services/agent/loop.py`, client `utils/agentStream.js`). SSE events: `{status}` (which tool runs — shown as a chip), `{text}`, `{viz}`, `{proposal}`, `{done, lane, ms}`.

```mermaid
flowchart LR
  Q[question] --> C{answer cache<br/>user · question · ai_data_version}
  C -- hit --> OUT[SSE]
  C -- miss --> R{router.py<br/>top intents, regex}
  R -- match --> T1[ONE tool → Hebrew template + chart<br/>no LLM, ~50ms]
  R -- no --> P[prefetch.py<br/>company / customer / fund → run those tools first]
  P --> L[Sonnet 5 · effort low · thinking DISABLED<br/>tools+system prompt-cached 1h · usually 1 call]
  L --> TOOLS[registry.py — 47 tools]
  T1 --> OUT
  L --> OUT
```

- **Code:** `services/agent/` — `registry.py` (decorator, sorted frozen list, dispatcher), `context.py` (`ToolContext`), `tools_data.py`, `tools_maslaka.py`, `tools_market.py`, `tools_actions.py`, `tools_memory.py`, `tools_viz.py`, `router.py`, `loop.py`, `prompt.py`, `cache.py`, `versioning.py`, `dictionary/*.md`.
- **Tools by category:** overview · commissions (`get_unpaid`, `get_commission_trend`) · production (`get_portfolio`, `top_customers`, `get_production_changes`) · customer (`find_customer`, `get_customer`) · agreements (`get_rate`, `list_agreements`, `get_agreement_doc`) · מסלקה (`maslaka_status`, `customer_holdings`, `propose_maslaka_request`) · opportunities (`get_insights`) · market (`compare_hishtalmut/gemel/gemel_invest/child_savings/pension/savings_policy`, `get_customer_fund_fit`, `fund_opportunities`, `market_flows`) · mail/calendar (`list_mail`, `propose_email`, `propose_meeting`, `propose_collection_reminder`) · navigation (`open_page`, incl. `dict/<cat>.md`) · `render_chart` · `remember`.

**Invariants — do not break:**
1. **Privacy.** No tool schema has a user id (`registry.FORBIDDEN_ARGS` asserts it; `dispatch()` strips one the model invents). Every tool reads through `ToolContext(db, user)` = the session user. Cache keys start with the user id. Memory (`ai_memories`) is per user — nothing is learned across agents. Market data (`fund_market_monthly`) is the only global table, and it joins customer data only inside a user's `ToolContext`.
2. **One source per number.** Data tools call the dashboard's own endpoint functions directly (`comparison.company_summary` / `company_unpaid`, `production.get_commission_trend` / `get_expected_commission_trend` / `get_production_breakdown` / `get_production_clients`) and the data map. Never new money SQL. `tests/test_nifra_agent.py` asserts the AI's unpaid / received / trend numbers EQUAL the dashboard's.
3. **Nothing is sent without the agent's click.** `propose_*` only append to `ctx.proposals`; `POST /office-agent/act` executes (`email`, `meeting`, `collection` → `collection_agent.send_case/send_reminder`, `maslaka` → **9100 only** — exactly what the מסלקה tab sends (ID + name, no extra consent fields) — through the SAME gates: `require_maslaka_enabled` + `require_association_approved`, then `orchestration.create_inquiry`; 9101/9102 stay off until the tab supports them and one was accepted live). A *question* can't trigger an action: `ctx.allow_actions = wants_action(...)` and `dispatch()` refuses action tools otherwise — the tool LIST stays constant so the prompt cache holds.
4. **Stale answers can't survive new data.** `users.ai_data_version` is part of every cache key. `versioning.register_listeners` (registered in `app/models/__init__.py`, so the API, the local worker and scripts all get it) COLLECTS user ids on `after_flush` for real ORM changes to AI-read tables (`session.is_modified` filters no-op sets — opening the Nifra Agent panel must not empty the cache) and bumps **after commit, in its own short transaction** (`bump_now`) — never inside the ingest's transaction, where an `UPDATE users` would hold the row lock for the whole ingest and could deadlock two ingests of one agent. Rolled-back work bumps nothing. Background recomputes that write with core `update()` (accumulation backfill) call `bump_now` explicitly at the end (`upload_ingest._after_*_bg`). TTL (10 min answers / 30 min metrics) is only a backstop.
5. **Prompt-cache prefix is byte-stable.** `prompt.SYSTEM_STATIC` + the dictionary index carry `cache_control: 1h`; tools render before system, sorted. Date, name, memory and screen context go in the per-turn user block — never in the static prompt. Verify with `cache_read` in the `NIFRA-AGENT hop=` log lines.
6. **Strict tools ≤ 20** (API limit) — only actions + `render_chart` are `strict`.
10. **An explicit address means `propose_email`.** `propose_collection_reminder` refuses a case with no contact email (it would reach no one) — the model is told to email the address the agent gave instead.
7. **Charts by reference.** Tools `ctx.keep(rows)` and return a `result_id`; the model calls `render_chart(result_id, type)` and the server builds the payload (`tools_viz.build_viz`, same contract as `components/ai-charts/registry.js`). The model never re-types numbers.
9. **Only open funds are switch targets.** `tools_market.is_open`: sector/employer-only funds (`target_population` ≠ כלל האוכלוסיה, e.g. רום for local-authority employees) and closed veteran pension funds (קרנות כלליות) never rank as "best" — they're matched only when the customer is already in them.
8. **Fund matching never crosses insurers.** `tools_market.match_fund` narrows to the same `company_stem` + category, then exact name or key-token Jaccard ≥ 0.75; else "לא זוהה מסלול". Fuzzy string matching mapped מור→מיטב and אלפא מור→הראל — don't go back to it.

- **Fast lane (`router.py`):** conservative regex for the top questions (unpaid, unpaid per company, this month's commission, portfolio, top customers, who left, rate, מסלקה, what to do, overview, customer by ID). Never for an action verb or a "why". Hebrew final letters matter (`שילם` ≠ `שילמ`).
- **Data dictionary:** `backend/scripts/build_data_dictionary.py [--fill-rates]` → `services/agent/dictionary/` (index in the cached prompt; category pages via `open_page("dict/…")`; columns <5% filled marked ⚠). Regenerate after a schema change; fill rates should be generated against PROD (percentages only).
- **Official fund data (`services/fund_market`):** the old `gemelnet.cma.gov.il` views are gone (gov.il "not found" page). The same data is CKAN open data on data.gov.il — גמל-נט `a30dcbea-…`, פנסיה-נט `6d47d6b5-…`, ביטוח-נט `c6c62cc7-…` (2024→today; 2023 and 1999-2022 resources too). `sync()` upserts `fund_market_monthly` (never deletes; ~52k rows from 2023). Scheduler `sync_fund_market` runs daily on the 1st–15th. Units: yields/fees in PERCENT, assets/flows in ₪ MILLIONS. Answers always state the data month + "תשואות עבר…".
- **Latency (local, 2026-10-02, after the latency fix):** cache <20ms · fast lane p50 40ms · agent lane: first word 1.8–3.9s, complete 4–6.5s (was 7–10.5s). Where the time went before: Sonnet 5.5 cannot disable thinking — `between_tools` still reasons ~5s after EVERY tool result and releases the answer in one burst at the end (measured: 665 output tokens, ~250 visible). Fixes, all three: (1) `MODEL = claude-sonnet-5` with `thinking: disabled`, effort low (streams the first word ~1–1.5s into a call; 5.5 kept as fallback); (2) answers ≤60 words unless asked (per-turn instruction — generation speed is now the limit); (3) `prefetch.py` runs the obvious tools (company → unpaid/rate/trend, customer name/ID → card, fund category → compare_*) BEFORE the model, so most questions take ONE model call. Prefetch is skipped for explanation questions ("מה ההבדל…"). `NIFRA-AGENT hop=… ttft=…` and `tools=…` log lines show the split. `backend/scripts/agent_latency.py` measures it.
- **Calls from the agent (2026-10-02):** `tools_calls.py` — `start_call_recording`, `stop_call_recording`, `get_call_summaries`. Recording is in the BROWSER (calls store → /api/calls → ivrit.ai → Claude summary, §18), so the tools return a `proposal` (`record_call` / `stop_call`) that the chat surfaces run at once via `frontend/src/utils/agentCalls.js` — the agent's own request is the consent, but the legal "הלקוח יודע שהשיחה מוקלטת" ack (`calls_consent_ack`, same flag as the Calls studio) is asked first if never given. "תקליט…" / "עצור" are instant router intents (never cached). `AgentCallCard.vue` mirrors the calls store (timer, stop, processing); `followCall` posts "הסיכום של השיחה מוכן — title · tldr · next step" into the same chat when the call is done, and "פתיחת הסיכום" opens it in the Calls studio (`callsStore.requestStudio`). Questions like "מה סיכמתי…/מה היה בשיחה" prefetch the call summaries.
- **Surfaces:** `surface: "panel"` (Nifra Agent) asks for plain text and the store strips Markdown (`utils/agentStream.stripMarkdown`); the chat renders Markdown. The answer cache is keyed per surface.
- **Data dictionary fill rates:** the shipped pages carry NO fill %; local test data would mislead. Generate `--fill-rates` against PROD (read-only, percentages) before relying on them; known-empty columns are flagged through `NOTES` regardless.
- **Learning:** `remember` → `ai_memories` (≤60 per user, injected each turn); every question → `ai_intent_log` (lane, intent, ms) — also the DB-backed rate limit (60/hour/user). Agent-lane calls are logged to `ai_usage` (`feature="agent"`).
- **Charts in the UI:** every AI chart opens with the shared **silk** transition (App.vue `--ease-silk` iOS sheet curve, `--dur-silk` 650ms; `.silk-*` classes; `composables/useSilkOpen.js`) and bars enter after `--silk-content-delay`, staggered from the right. `AiBarChart` / `AiTrendChart` carry the **hover trace** (ported from a React/recharts component to Vue — no React/Tailwind/shadcn added): a big spring-animated readout (`composables/useSpring.js`), a dashed line that springs to the traced value, other bars dimmed to 0.2; at rest it traces the leader / latest point.
- **Not built yet:** Google Calendar / Outlook calendar providers (need OAuth apps + Google verification — meetings are still ICS invites by email), server-side conversation history, a Haiku intent classifier behind the regex router, cache warm-up of each agent's top intents.

### 17b. Collection agent (סוכן גבייה) — one of the office agent's workers

- **Unpaid** = `only_production` customers of insurers that DO report נפרעים that month (no נפרעים at all = "no data"). Inactive or cancelled products are never claimed.
- **Drafts:** one line per customer + policy.
- **Flow:** DRAFT → the agent approves (send via `send_as_agent`) → replies polled every 15 minutes, with a one-line Haiku summary → a reminder is SUGGESTED after 7 days → resolved.
- **Code:** `services/collection_agent.py`, `/api/collection-agent`, `collection_cases` (UNIQUE user + company + month), `tests/test_collection_agent.py`.

## 18. Calls plane (שיחות) — browser recording → ivrit.ai transcript → Claude summary

A fourth plane of three small Railway services plus Redis. The agent records a conversation from the
**home-hub calls widget** (beside the cycle clock and the Nifra Agent orb). The audio is transcribed by a
self-hosted **ivrit.ai** Hebrew Whisper model, and the API summarises the transcript with Claude.

```mermaid
flowchart LR
  B[Browser MediaRecorder<br/>webm/opus 32kbps] -->|POST /api/calls| API[nifraim API]
  API -->|POST /ingest/id<br/>private net + X-Calls-Secret| GW[calls-gateway<br/>volume /data/calls<br/>inbox→queued→done/failed]
  GW -->|listener: Lua SET-NX + XADD| J[(Redis calls:jobs)]
  J -->|XREADGROUP transcribers| T[ivrit-transcriber<br/>ffmpeg + faster-whisper<br/>ivrit-ai/whisper-large-v3-turbo-ct2]
  T -->|GET /files/id| GW
  T -->|PUT /transcripts/id + SET calls:tx:id| GW
  T -->|XADD transcribing/transcribed/failed| E[(Redis calls:events)]
  E -->|group api| API
  E -->|group gateway: move file| GW
  API -->|call_tool| C[Claude summary + insights]
  API --> DB[(call_recordings)]
```

| Piece | Code |
|---|---|
| Wire contract (stream names, fields, timeouts). Copied VERBATIM into both service images. | `backend/app/services/calls/contract.py` |
| API routes `/api/calls` (`status`, POST, list, get, delete) | `backend/app/api/calls.py` |
| Events consumer (supervised asyncio task, started in `main.py` lifespan) | `backend/app/services/calls/events_consumer.py` |
| Claude summary tool (`title, summary, key_points, action_items, customer_needs, products_mentioned, objections, sentiment, follow_up`) | `backend/app/services/calls/summarize.py` |
| Model + migrations | `models/call_recording.py`, `alembic/versions/calls_01.py`, `calls_02.py` |
| Shared ingest (widget + phone), phone keys | `backend/app/services/calls/ingest.py` |
| Phone routes `/phone-forward/{token}/call`, `/client-phones` | `backend/app/api/portal_automation.py` |
| Nifraim App (Android) calls pickup | `android/…/{CallSync,CallWorkers}.kt` |
| Gateway | `services/calls-gateway/` |
| Transcriber | `services/ivrit-transcriber/` |
| UI | `components/calls/*`, `stores/calls.js` |

Status: `uploaded → queued → transcribing → summarizing → done | failed`.

### Invariants
1. **Audio is never public.** Only the API is exposed. The gateway and transcriber have no public domain, and
   every protected gateway route checks `X-Calls-Secret`.
2. **The API is the only writer of the DB and the only caller of Claude.** `user_id` is always read from the row,
   never from an event.
3. **The gateway is the only owner of files.** Railway volumes attach to ONE service, so the transcriber fetches
   audio over HTTP, never from a shared disk.
4. **Enqueue is exactly-once.** A Lua `SET calls:enq:<id> NX` + `XADD` runs as one atomic step. inotify plus a
   60-second rescan means a missed filesystem event never strands a file.
5. **A job is acked only after its result is durable** (Redis key + gateway `done/<id>.json`). A busy
   transcriber re-`XCLAIM`s its job every 60s (heartbeat). An idle job is `XAUTOCLAIM`ed after 5 minutes.
   More than 3 deliveries sends it to `calls:dead` and marks it `failed`.
6. **Every call ends `done | failed`.** The API fails anything non-terminal after 3 hours. When Claude is down,
   the result is `done` with the transcript and a Hebrew note.
7. **The contract has one source.** Change `contract.py`, then redeploy all three services.
8. **Every source goes through ONE ingest.** `services/calls/ingest.py::ingest_call` creates the row and streams
   to the gateway, for the widget (`POST /api/calls`) and the phone (`POST /phone-forward/{token}/call`) alike.
9. **A call with a non-customer never leaves the phone on its own.** The Android app uploads automatically only
   when the number's hash is in the agent's customer list; anything else waits for an explicit tap in a
   notification. That is the same rule as `OtpFilter` for SMS.

### Speaker labels, categories and what Nifra Agent knows (2026-10-05)
- **Speakers:** the transcriber runs pyannote (`ivrit-ai/pyannote-speaker-diarization-3.1`, ungated, so no HF token is needed)
  in its own process. It assigns a speaker to each WORD and splits whisper segments where the speaker changes
  (`services/ivrit-transcriber/speakers.py`). A diarization error never fails a call: the segments simply have no
  speaker. **If only one voice is heard, the labels are dropped** (`events_consumer.one_voice_unlabelled`); otherwise
  every line would be "agent".
- **The summary gets the names we KNOW:** the agent comes from the account, the customer from the phone match
  (`summarize._who`). A name spoken on the line is as likely to be the agent's as the customer's; one draft greeted the
  customer by the agent's name. Due dates come from a 14-day **lookup calendar** in the prompt (`when_line`), because
  the model mis-added weekdays. `_untag` strips the model's leaked field tags and literal `\n` before anything reaches
  a customer email.
- **Customer quotes are verified in code** against lines labelled as the customer. Unlabelled calls have none.
- **Categories** come from ONE list, `services/calls/categories.py`, stored in the `category` column (`calls_03`). Topics,
  companies mentioned and urgency go in `insights`. Old calls: `scripts/backfill_call_categories.py` (Haiku). It never
  rewrites a summary or a follow-up.
- **Tasks are server state:** `insights.action_items[i]` = `{text, owner, due, due_date, done, done_at}`, ticked via
  `POST /api/calls/{id}/tasks/{i}`. This used to be localStorage, which the agent could not see.
- **Nifra Agent:**
  - tools `search_calls`, `customer_calls`, `get_call`, `open_promises`, `calls_stats`, and `mark_call_task_done`
    (an action, kind `call_task`, approved via `/office-agent/act`)
  - data map pages `calls.md`, `calls/<category>.md`, and a "שיחות" section on every customer page
  - office-agent **promise** cards for agent tasks whose date has come (one action: סימנתי שבוצע)
  - the fast lane never answers a question containing "שיח"

### Semantic search over calls (pgvector, 2026-10-05)
- **What gets indexed:** each finished call is cut into passages of ONE speaker turn (8–30 words), plus one summary
  passage (`services/calls/embeddings.passages`). Long multi-speaker windows let the greeting dominate the vector,
  which was measured to bury the topic.
- **Where the model runs:** in the API process, ONNX on CPU (`onnxruntime` + `tokenizers`, no torch). Nothing leaves our
  servers. It is indexed after the summary (`events_consumer`), best-effort: an embedding failure never fails a call.
- **Storage:** table `call_chunks` (`calls_04`) with `vector(384)` and an HNSW cosine index. The migration is
  **guarded**: if the server lacks the `vector` extension it is a no-op, so a restart can't crash-loop. Railway PG17
  has pgvector 0.8.6. Local `postgres:16-alpine` needs it compiled into the container (`git clone pgvector && make
  with_llvm=no install`), and that is lost if the container is recreated.
- **The model is one setting:** `CALLS_EMBED_MODEL`, from `EMBED_MODELS`. The default is `multilingual-e5-small`
  (~120 MB q8). Measured on 69 real call passages and 8 paraphrased Hebrew questions:

  | model | top-3 | MRR | index time |
  |---|---|---|---|
  | e5-small | 7/8 | 0.74 | 0.8 s |
  | EmbeddingGemma-300m | 6/8 | 0.78 | 22.8 s |
  | bge-m3 | 6/8 | 0.71 | 14.5 s |
  | e5-base | 6/8 | 0.63 | 3.4 s |

  Dicta neodictabert-bilingual-embed returned NaN on CPU torch 2.5 and has no ONNX; revisit it later. To switch
  models: add a migration for the vector size, set the env var, then run `scripts/reindex_calls.py`.
- **`search_calls` is hybrid:** meaning first (pgvector, this user only, call filters applied), then exact words. It
  returns the passages labelled לקוח/סוכן with timestamps. Without the model or pgvector it falls back to words only.
  "מה הלקוח אמר/התלונן…" goes to `search_calls`, not `find_customer`, in both the prompt and the router.

### Self-healing sweep (2026-10-05)
`services/calls/sweep.py` runs inside the calls events consumer about every 2 minutes, plus once at start-up. It fills
in whatever a finished call is missing, newest first and in small batches:
1. **Summary** (2 per pass): the summary when Claude was down (`SUMMARY_UNAVAILABLE`).
2. **Category** (8 per pass): category, topics and task due dates for calls from before categories existed. Uses
   Haiku, and never rewrites a summary or a follow-up.
3. **Search passages** (20 per pass): for any call without passages under the CURRENT `CALLS_EMBED_MODEL`, so new
   calls, calls from before `calls_04`, and a model change all catch up by themselves.

Calls younger than 2 minutes are left to the live pipeline. Each job gets at most 3 tries per call, recorded in
`insights._sweep`. The sweep never raises. Both the live pipeline and the sweep use the same `summarize_into`,
`index_safely` and `categorize`. The scripts `backfill_call_categories.py` and `reindex_calls.py` remain for doing it
all at once. Tests: `tests/test_calls_sweep.py` (20, against the local DB with real pgvector and fake Claude).

### Agent-world suites (live, real model): `tests/agent_world_calls.py` (25), `tests/agent_world_conversations.py` (20), `tests/agent_world_money.py` (26)
Not pytest: each run costs model calls. They spy on `registry.dispatch` (which tools were used), check the answer,
the proposals, and that the DB did not change behind the agent's back. The rate limit and answer cache are off
during the run. Each run plants a prompt-injection call and another user's call, then removes them. Bugs these
suites found (all fixed 2026-10-05):
- raw `<invoke>` tool markup streamed to the screen (`loop.TagScrub`)
- "סמן…" was not an action verb, so the agent claimed it had prepared something it hadn't
- `_proposal_line` crashed on a `call_task` proposal
- `customer_calls` didn't say WHO owes each task, so the customer's task was presented as the agent's promise
  (now `open_agent` / `open_customer` / `done`)
- the fast lane answered "על מה לא שולם עומר עמר" with the all-companies total, ignoring the name AND the thread.
  `_unexplained_words` now sends any question with a non-unpaid word (a person's name) to the agent lane.
  `_company` is word-bound and knows that a company word after a first name is a SURNAME (עומר מור, יניב הראל,
  ברוך מור).
- a false premise ("למה פחות?" when it rose) produced an apology for a correct answer
- "תשלח לו מייל" after a company list assumed the company. It now asks: customer or company?

Money suite (commissions + production) found and fixed:
- **"ומכמה ציפיתי?"** reported a ₪69,926 gap (the real gap is ₪24,136). `expected_by_month` includes companies with no
  report yet. `get_commission_trend` now carries a note with the comparable expected/received/gap.
- **`get_unpaid(company)`** now returns the company's received, expected and unpaid %, plus a "no debt" note when
  expected is ₪0. "כמה התקבל מהראל" and "% of expected" used to fail.
- **The fast lane** answered "כמה קיבלתי במרץ" with June. A named month (`MONTH_RE`) now goes to the agent lane.
  One-letter company typos (מנורא, פנקס) resolve via `_company_typo`. A company with ₪0 expected answers "no debt".
- **Follow-ups:** "ועם הפניקס?" after an agreement question answered unpaid. `router.followup_question` rewrites a
  short "ו…" follow-up as the previous question at the new company, for both prefetch and the prompt. In
  `prefetch.py`, book questions (לקוחות/צבירה/פרמיה…) prefetch `get_portfolio`, not `get_unpaid`.
- **Customer card:** a "לא שולם" section for companies that paid nothing. The agent had answered only a partial Mor
  gap and missed Harel's ₪1,111.
- **Name search** matches words in any order ("גורן גורן" → גיא גורן).
- **New tool `calls_with_unpaid`:** no-payment AND partial gaps for customers you spoke with, from the same sources.
- **OPEN, not fixed (core maths):** Harel "expected commission" is ₪3,071 in `get_portfolio` (production × rates) but
  ₪7,793 in the comparison. These are two definitions that don't reconcile. See the `commission-calculation` skill.

### Calls from the agent's phone (2026-10-05)
Since Android 10, apps can't record calls. The phone's own dialer can (Samsung saves to `Recordings/Call/`), and the
**Nifraim App** (`android/`, the former SMS forwarder) only **collects** those files:

```
dialer saves recording → MediaStore content-URI trigger → CallScanWorker
  → CallSync.matchCall: call-log entry whose end ≈ file mtime (±3 min) → number + direction
     (fallback: a number in the file name)
  → number's sha256(phone_key) ∈ GET /phone-forward/{token}/client-phones ? CallUploadWorker (multipart, Wi-Fi-only option)
                                                                  : CallApproval notification "להעלות?"
  → POST /phone-forward/{token}/call → match_phone() → ingest_call(source=phone_android, phone_number, direction, id_number)
```

- **`phone_key`** = the national number without its 0 (`050-1234567`, `501234567` (Excel), `+972…` all → `501234567`).
  The backend (`ingest.py`) and the app (`CallSync.kt`) must compute it identically. The hash list only keeps the plain
  customer list off the phone. It is not a secret, because the number space is small.
- `id_number` is set only when exactly one customer has that phone. A number shared by a family stays unmatched, and
  `events_consumer` falls back to the names in the transcript.
- Recordings from **3 hours before** the feature was turned on are picked up too (1.3), nothing older.
  `source_ref = ms:<MediaStore id>` makes retries return the existing call.
- **Walk-in customers (לקוח חדש, 1.4, 2026-10-06).** A new customer who isn't in any production file yet is added in
  אנשי קשר (`WalkinFormModal.vue` → `/api/walkin-customers`, table `walkin_customers`: ת.ז, name, phone, email).
  `customer_phones()` merges them, so `/client-phones` and `match_phone` include them, and `office_agent.contacts()`
  lists them as customers, so a call resolves to their name and email for the follow-up letter. The app refreshes
  the customer list on every scan (≥10 min apart, so within one 15-min periodic scan or on opening the app). When
  hashes are **added**, `Skipped.recheck` uploads the recordings from the last 3 hours that it had left out for that
  number (unanswered "להעלות?" or in-app pending). An answered **"לא" is never revisited.**
- **Personal calls + never-upload numbers (1.5, 2026-10-06).** `services/calls/privacy.py`. A call is personal when the
  summary picks category `personal` (family, friends, errands, even with a customer), when the agent marks it (call card
  → אישית), or when its number is on `blocked_phones` (the third app "לא להעלות" in אנשי קשר). Personal = hidden from every
  reader (`visible()` — add it to any new call query), no tasks / follow-up / quotes, no passages, audio deleted from the
  gateway at once; `restore` brings it back. Never-upload: `/client-phones` sends `block` hashes → app 1.5 drops those
  recordings on the device without asking; `/phone-forward/{token}/call` refuses them too (older apps); adding a number
  hides its stored calls.
- **Diagnostics (1.3):** each scan POSTs counts only to `/phone-forward/{token}/calls-diag` → `railway logs | grep CALLS-DIAG`.
- **iPhone (iOS 18.1+)** saves call recordings into Notes, where apps can't reach them. The agent uses a Share-sheet
  Shortcut "שלח לנפרעים" that posts to the same `/call` with `source=phone_ios` (guide in `PhoneForwardModal.vue`). It sends
  no number, so the customer comes from the transcript.
- The dialer's `.amr`/`.3gp` files are accepted (`AUDIO_EXTS`).
- Columns are in `calls_02`: `source, phone_number, direction, started_at, id_number, source_ref`.

### Run locally
`TRANSCRIBER_FAKE=1 docker compose up -d redis calls-gateway ivrit-transcriber` (FAKE returns a canned Hebrew
transcript in about 3s; drop it to load the real model, a one-time download of about 1.6GB into the `ivrit_models` volume).
The host `.env` needs `CALLS_ENABLED=true REDIS_URL=redis://localhost:6379 CALLS_GATEWAY_URL=http://localhost:8090
CALLS_SECRET=dev`. The gateway image binds `HOST=::` for Railway, which is IPv6-only, so compose overrides it to `0.0.0.0`.

### Deploy (Railway) — LIVE since 2026-10-02
Services in project `patient-cat`: `Redis`, `calls-gateway` (volume `/data/calls`, `PORT=8080`), `ivrit-transcriber`
(volume `/models`, `BEAM_SIZE=1`), and `nifraim` with `CALLS_ENABLED=true`. `REDIS_URL=${{Redis.REDIS_URL}}`,
`CALLS_GATEWAY_URL=http://calls-gateway.railway.internal:8080`, and one shared `CALLS_SECRET` across all three.

**Deploying a calls service** (the proven way; the root `railway.toml` and its Config-File-Path trick did NOT work, Railway fell back to Railpack):
1. Stage a folder that mirrors the repo paths it COPYs: `services/<svc>/*` + `backend/app/services/calls/contract.py`.
2. Put `services/<svc>/Dockerfile` at the stage ROOT, plus a root `railway.toml` with `dockerfilePath = "Dockerfile"`.
3. `RAILWAY_TOKEN=… railway up <stage> --path-as-root --service <svc> --detach`.

Other gotchas:
- With the project token, `railway volume add` crashes. Create volumes through GraphQL `volumeCreate`
  (`Project-Access-Token` header).
- Set variables with `--skip-deploys` so no restart re-runs alembic.
- `nifraim` deploys as always: `cd /home/roygi/test && railway up --service nifraim`.

**Speed:** measured real-time factor (RTF) 1.0 on 32 threads (25s of audio in 25s). Railway CPU is slower per call;
`BEAM_SIZE` defaults to 1 (measured 2026-10-02: 2.0–2.3× faster than 5, RTF 0.35–0.38, identical text on the Hebrew sample; raise it only if noisy real calls lose accuracy). Tune `CPU_THREADS`, or move the transcriber to a GPU host. The queue contract does not change.

---

## 19. הר הביטוח + policy documents — the customer's whole insurance file, as Markdown the AI reads (2026-10-07)

הר הביטוח (harb.cma.gov.il, Ministry of Finance) lists every insurance policy a person holds, at every
insurer, not only the agent's book. Nifra Agent fetches it ON DEMAND per customer, and policy PDFs the agent
already has (insurers' העתק פוליסה) join the same store. Both end up as **Markdown** in `policy_documents`,
embedded into `doc_chunks`, and linked from the data map.

```mermaid
sequenceDiagram
    participant A as Agent (Nifra panel)
    participant API as Cloud API
    participant DB as PostgreSQL
    participant W as Local worker (IL)
    participant H as harb.cma.gov.il → login.gov.il
    participant P as Agent's phone
    A->>API: "תביא לי מהר הביטוח 203717186 22/05/1986 10/03/2004"
    API-->>A: proposal {kind: harb} (propose_harb_fetch — gates checked)
    A->>API: click "אישור — יש לי הסכמת הלקוח" → /office-agent/act kind=harb
    API->>DB: harb_requests (pending) + portal_runs (only if none is live)
    W->>DB: claim the run (worker loop, unchanged)
    W->>H: כניסת מורשים → #userId/#userPass → SMS
    H->>P: OTP SMS
    P->>API: phone-forward → otp_inbox
    W->>DB: _wait_for_otp → submit
    loop every pending request of the user (one login)
        W->>H: מבוטח בגיר → #txtId + Kendo dates → צפיה → כל הביטוחים → Excel + policy details
        W->>DB: harb_ingest → insurance_policies + policy_documents (Markdown)
    end
    API->>DB: policies_index_sweep (2 min) → doc_chunks (embeddings)
    A->>API: polls /api/policies/harb-requests/{id} → done → Nifra posts the summary
```

**Where things live**
| Concern | File |
|---|---|
| Portal plugin (login.gov.il SSO, search, Excel, details, queue drain) | `services/portal_automation/companies/harbituach.py` |
| Queue: enqueue / claim / finalize / gates / date parsing | `services/policies/harb_jobs.py` |
| Runner hook (kind-gated: `harb_next`/`harb_done`, skips generic ingest) | `services/portal_automation/runner.py` (`is_harb`) |
| Excel parser (header by name, תחום sections, מתחדש) | `services/policies/harb_parser.py` |
| Markdown (portfolio + detail pages), store, per-customer picture | `services/policies/markdown.py`, `store.py`, `harb_ingest.py` |
| PDF → Markdown (text layer + OCR + native PDF, structured outputs) | `services/policies/pdf_policy.py` |
| Embeddings + hybrid search + sweep | `services/policies/embeddings.py` (reuses `services/calls/embeddings`) |
| API | `api/policies.py` (`/api/policies/*`), `/office-agent/act` kind `harb` |
| Agent tools | `services/agent/tools_policies.py`: `propose_harb_fetch`, `customer_policies`, `search_policies`, `get_policy_document` |
| Data map | `policies.md`, `customers/<id>/policies.md` (active first), customer page fallback |
| UI | Nifra card + live stage (`OfficeAgentPanel.vue`, `stores/officeAgent.js`, `utils/agentHarb.js`); אנשי קשר → פוליסות (`PoliciesDrill.vue`, `utils/mdLite.js`); Settings → אוטומציה → הר הביטוח |
| Tables | `harb_requests`, `insurance_policies`, `policy_documents` (`policies_01`), `doc_chunks` (`policies_02`, guarded), history: `is_current` + `harb_requests.changes` (`policies_03`) |

### Invariants
1. **On demand, worker only, never in the cycle.** `include_in_batch = False`, no "run now" (the card says
   "מופעל מתוך Nifra", `runNow` ignores the kind). A run with no `harb_next` refuses to start.
2. **The click is the consent.** The site's checkbox says the user has the insured's authorization; Nifra only
   proposes, and `/act` re-checks every gate (credential, worker heartbeat ≤ 90s, no open request for the customer).
   The fetch verb (תביא/שלוף/בדוק…) counts as an action only next to "הר הביטוח" (`HARB_ACTION_RE`).
3. **One login per queue.** One active `harbituach` run per user; extra requests wait `pending` and the live run
   drains them ("כניסה לתיק נוסף"). On finalize: leftovers after a success get a fresh run; if the login/OTP
   never got through, they FAIL with that reason (no retry loop). One customer's failure never fails the others.
4. **Never production.** The Excel is every insurer's policies, not the agent's book: no `ingest_file_bytes`, no
   fold into the מאוחד file, separate tables. Don't merge `insurance_policies` into `client_records`.
5. **History, not overwrite (policies_03).** A re-fetch supersedes the previous fetch (`is_current=false`) — rows and
   documents are kept, their passages leave search. `diff_snapshots` stores what changed on `harb_requests.changes`
   (new / removed policies, premium + period changes; duplicate coverage lines are matched as multisets) and writes it
   into the new portfolio Markdown, so Nifra answers "what changed". Everything that answers (picture, data map,
   search, sweep) reads `is_current` only; uploaded PDFs are never superseded.
5b. **Ask before a re-fetch.** A customer fetched within `HARB_REFETCH_ASK_DAYS` (30) gets a question, not a card
   ("נשלף היום ב-15:00 — לשלוף שוב?"); "כן" → `confirm_refetch=true`; "שוב/מחדש" in the request confirms up front.
5c. **Limits** (`harb_jobs.check_limits`, settings): `HARB_DAILY_LIMIT` 30/agent/24h, `HARB_CUSTOMER_DAILY_LIMIT`
   2/customer/24h, `HARB_MAX_QUEUE` 10 open. A fetch that died at login doesn't count.
6. **The worker never embeds.** It writes rows and Markdown only (no 120MB model on the agent's PC); the cloud
   sweep indexes. `doc_chunks` is guarded like `call_chunks`; without pgvector search falls back to words.
7. **Numbers come from the document.** הר הביטוח Markdown is deterministic (no LLM). PDF Markdown copies figures
   verbatim (structured outputs, Sonnet 5.5 → 4.6; 5.x rejects forced `tool_choice`). Tools return active and ended
   policies as separate lists, and the policies page lists active first, so a truncated read never drops a live policy.
8. **Tag the OTP.** The real הר הביטוח SMS wording isn't known yet; until a `portal_kind="harbituach"` template
   is seeded (`api/sms_otp_templates.py`), the device's fail-open rule forwards it and `_wait_for_otp` accepts it untagged.
9. **Dates are never guessed.** Missing/invalid birth or issue date → the tool asks; future dates are rejected.

### Status (2026-10-07)
Built and verified locally: parser + Markdown on the real export (50 coverages, 23 policies), PDF→Markdown on a
scanned Phoenix and a 15-page Harel policy, embeddings + hybrid search, the 4 tools against the real model,
`/act` → queue → finalize, the UI drill (Playwright). **The plugin's post-login screens are unverified live**:
only the login form was recon'd (login.gov.il `#userId/#userPass/#loginSubmit`); the OTP screen, the search
form's Kendo widgets, the not-found message and the policy-detail views need the first live run (it dumps
`<run>_harb_*.png/html/txt` at every step).
