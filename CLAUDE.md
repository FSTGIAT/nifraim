# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Nifraim — Insurance Reconciliation Dashboard

Read `.xlsx` files, parse Hebrew columns, reconcile production vs. commission records, and present insights through a Hebrew RTL interface. Before writing code, plan the architecture and document it in `.claude/plans/`.

> **🗺️ Read [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) first.** It is the machine-readable
> map of how the app is wired — the two-plane cloud/worker topology, Mermaid data-flow graphs,
> a "where do I look for X" navigation index, and the OTP / comparison / AI **invariants you must
> not break**. This CLAUDE.md covers conventions and how-tos; that file covers the graph.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│  Frontend (Vue 3 + Pinia + Vite 5)              │
│  Port 5173 → proxy /api → backend              │
│  Hebrew RTL, Heebo font, Salesforce Lightning   │
├─────────────────────────────────────────────────┤
│  Backend (FastAPI + SQLAlchemy async)            │
│  Port 8000, JWT auth, Excel parsing pipeline    │
├─────────────────────────────────────────────────┤
│  PostgreSQL 16 (Docker)                         │
│  Port 5432, Alembic migrations                  │
└─────────────────────────────────────────────────┘
```

## Tech Stack

| Layer    | Technology                                           |
|----------|------------------------------------------------------|
| Backend  | FastAPI 0.115, SQLAlchemy 2.0 (async), asyncpg, Alembic |
| Frontend | Vue 3.5, Pinia 3.0, Vue Router 4.6, Vite 5.4, ApexCharts 5.3 |
| Database | PostgreSQL 16 Alpine (Docker)                        |
| Excel    | pandas, openpyxl (xlsx), xlrd (xls), msoffcrypto (passwords) |
| Auth     | JWT + bcrypt, HTTPBearer dependency                  |
| UI       | Heebo font, RTL layout, Salesforce Lightning Design vars |

---

## Running the Project

```bash
docker-compose up -d                                                          # PostgreSQL
cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000  # API
cd frontend && npm run dev                                                    # UI (port 5173, proxies /api → :8000)
```

Note: There is also a root-level `.venv/` — backend's own `venv/` is at `backend/venv/`.

```bash
# Database migrations
cd backend && alembic upgrade head                    # Apply all migrations
cd backend && alembic revision --autogenerate -m "description"  # Create new migration
```

Test credentials: `test@test.com` / `test123`

No test suite or linter is configured. No `pytest`, `eslint`, or `ruff`.

---

## Project Structure

### Backend: `backend/app/`

- **`api/`** — Thin route handlers (9 routers). Auth via `Depends(get_current_user)` on every route.
- **`services/`** — Business logic: `parser_service.py` (Excel parsing, 7 formats), `comparison_service.py` (production vs commission matching), `reconciliation_service.py` (queries/analytics), `auth_service.py` (JWT/bcrypt).
- **`models/`** — SQLAlchemy ORM. `record.py` (ClientRecord, 80+ columns) is the main data table.
- **`schemas/`** — Pydantic request/response models.
- **`utils/hebrew_mappings.py`** — The Rosetta Stone: Hebrew→English column maps + format detection signatures.
- **`utils/sanitize.py`** — Truncates strings to MAX_LENGTHS, converts pandas Timestamps to Python `date`.

### Frontend: `frontend/src/`

- **`views/WorkspaceView.vue`** — Main app: 5-tab interface (Production, Comparison, Recruits, Rates, Emails)
- **`stores/`** — Pinia stores. Components use stores for API access, never call API directly.
  - Exception: `CommissionRateTable.vue` and `CompanyEmailsTab.vue` call API directly (intentional for self-contained CRUD).
- **`components/comparison/`** — The most complex area: `ComparisonDashboard.vue` → `ComparisonTable` → `ComparisonDetail` + `CustomerDetailModal`
- **`api/client.js`** — Axios with `/api` base, Bearer token interceptor, 401 → redirect to login.
- **`App.vue`** — CSS design system variables (Salesforce Lightning tokens), RTL root, global animations.

---

## Frontend Architecture

### Layout & Rendering Hierarchy

```
<App.vue>                          ← RTL root, Heebo font, CSS variables
  └── <router-view>
       ├── LoginView / RegisterView ← public routes
       ├── DashboardView             ← legacy reconciliation
       ├── AnalyticsView             ← chart-based analytics
       └── WorkspaceView             ← main app (5-tab interface)
            ├── WorkspaceHeader      ← sticky top: 0, z-index: 100
            ├── WorkspaceTabs        ← sticky top: 56px, z-index: 90
            ├── OnboardingTour       ← first-run guided tour (z-index: 5000–5002)
            └── <main>
                 ├── ProductionTab
                 │    ├── ProductionUploader   (drag-drop upload)
                 │    ├── ProductionDashboard  (KPIs, analytics charts)
                 │    └── ProductionComparison (file comparison)
                 │         ├── Summary KPI strip (new/removed/changed/unchanged)
                 │         ├── Main donut chart (התפלגות שינויים)
                 │         ├── Company breakdown donuts (חדשים/הוסרו לפי חברה)
                 │         ├── Changed insights section (שונו — תובנות)
                 │         │    ├── KPI cards (premium/accumulation diffs + type counts)
                 │         │    ├── Change type donut (שונו לפי סוג שינוי)
                 │         │    └── Top changers bar chart (גדולי השינויים)
                 │         └── FilterModal + detail view (z-index: 1010)
                 ├── ComparisonTab
                 │    ├── CommissionUploader   (drag-drop multi-file)
                 │    └── ComparisonDashboard  (charts + filter modal)
                 │         ├── ComparisonSummaryCards
                 │         ├── ApexCharts (donut, treemap)
                 │         ├── FilterModal (z-index: 1000)
                 │         ├── CustomerDetailModal (z-index: 1010)
                 │         └── ComparisonTable
                 │              └── ComparisonDetail (expandable row)
                 ├── RecruitsTab
                 │    ├── RecruitForm
                 │    ├── RecruitComparisonResults
                 │    └── PortalLinksManager (collapsible)
                 │         └── PortalGenerateModal
                 ├── CommissionRatesTab
                 │    └── CommissionRateTable
                 └── CompanyEmailsTab  (self-contained CRUD)

  └── CustomerPortalView          ← public /portal/:token
       ├── PortalPasswordForm     ← password entry
       └── PortalDashboard        ← after auth
            ├── PortalKPIStrip
            ├── PortalCompanyChart (ApexCharts donut)
            └── PortalProductTable (sortable)
```

### Routing & Auth

```
/login    → LoginView    (public)
/register → RegisterView (public)
/         → WorkspaceView (requiresAuth)
/dashboard → DashboardView (requiresAuth)
/analytics → AnalyticsView (requiresAuth)
/portal/:token → CustomerPortalView (public, no auth)
```

- `router/index.js` uses `beforeEach` guard checking `localStorage.getItem('token')`
- Unauthenticated users redirect to `/login`; authenticated users redirect away from login/register

### API Client (`api/client.js`) + Portal Client (`api/portalClient.js`)

- `client.js`: Axios with `baseURL: '/api'`, Bearer token from localStorage, 401 → redirect to /login
- `portalClient.js`: Separate axios for portal, Bearer token from **sessionStorage**, no 401 redirect
- All API calls go through Pinia stores, never from components directly

### Pinia Stores — State Management

| Store | Key State | API Endpoints | Notes |
|-------|-----------|---------------|-------|
| `useAuthStore` | `token`, `user`, `isAuthenticated` | `/auth/login`, `/auth/register`, `/auth/me` | Token persisted to localStorage |
| `useComparisonStore` | `results` (per category), `activeCategory`, `filterStatus`, `searchQuery` | `/comparison/dual-upload`, `/comparison/compute`, `/comparison/compare-with-production` | Category-scoped caching: גמל/ביטוח results stored separately |
| `useProductionStore` | `currentFile` | `/production/current`, `/production/upload` | Single active production file shared across comparisons |
| `useUploadsStore` | `uploads[]` | `/uploads` | Auto-refetch after upload/delete |
| `useRecordsStore` | `records[]`, `summary`, `pagination`, `filters` | `/records`, `/records/summary`, `/records/client/{id}` | Tightly coupled filter/pagination state |
| `useRecruitsStore` | `recruits[]`, `comparisonResult` | `/recruits`, `/recruits/bulk`, `/recruits/compare` | Full CRUD with optimistic local updates |
| `useAnalyticsStore` | `data` | `/records/analytics` | Read-only data loader |
| `usePortalStore` | `links[]`, `dashboardData`, `authenticated` | `/portal/*` | Agent-side link CRUD + customer-side portal access |

### Component Communication

| Pattern | Usage |
|---------|-------|
| **Props down** | Parent → child data flow (`customers`, `categoryLabel`, `commissionRates`) |
| **Emits up** | Child → parent events (`@logout`, `@close`, `@drill-customer`, `@rates-changed`) |
| **v-model** | Two-way binding for tabs (`WorkspaceTabs` ↔ `WorkspaceView.activeTab`) |
| **Provide/Inject** | `WorkspaceView` provides `droppedFiles` → `CommissionUploader` watches it |
| **Pinia stores** | Shared state — all components access stores directly, never call API |

### Tab System & Fullscreen Mode

- **5 tabs:** production, comparison, recruits, commission-rates, company-emails
- **Tab indicator:** animated underline using `getBoundingClientRect()` — RTL-aware (anchors from right)
- **Fullscreen mode:** activates when `activeTab === 'comparison' && comparisonStore.result` exists
  - Hides tabs, shows back bar, expands `max-width` to 100%
  - Exit via `comparisonStore.resetCategory()`

### ComparisonTab State Machine

```
1. No production file       → warning banner
2. Has production, no cat   → category selector (גמל vs ביטוח cards)
3. Category selected        → CommissionUploader + recent files grid
4. Has result               → ComparisonDashboard (fullscreen)
```

### Full-Page Drag & Drop

- `WorkspaceView` attaches `dragenter/dragleave/dragover/drop` on `document`
- `dragCounter` ref prevents false negatives from nested drag events
- Shows overlay (`z-index: 9999`) with marching-ants SVG border + bounce animation
- Dropped files stored in `shallowRef(droppedFiles)` → provided to children
- Auto-resets after 100ms so watchers can fire again for same files

### CSS & RTL Architecture

- **Design system**: All CSS variables defined in `App.vue :root` — check there before adding any colors, radii, or shadows.
- **RTL**: `direction: rtl` on `body`. Use `.ltr-number` class for numeric values. Use `gap` instead of directional margins.
- **Modal pattern**: All modals use `<Teleport to="body">` with `<Transition name="modal">`, overlay + card structure.
- **Z-index stacking**: Drop overlay: 9999, Onboarding tour: 5000–5002, Detail modal: 1010, Filter modal: 1000, Header: 100, Tabs: 90.
- **Charts**: ApexCharts with Heebo font. Chart click → filter modal → customer drill-down.

### Onboarding Tour (First-Time User Guide)

Interactive 8-step guided tour that runs once per user on first login. No backend changes — flag `onboarding_completed` is stored in localStorage **scoped per user** via `utils/userFlags.js` (key becomes `onboarding_completed:<jwt-sub>`; same for the activation checklist's `activation_closed`/`activation_completed`). Browser-global keys caused new accounts on a shared browser to silently skip onboarding.

**Architecture: Composable + Component**

| File | Role |
|------|------|
| `composables/useOnboardingTour.js` | Step definitions, state machine, spotlight positioning, tab switching, keyboard nav |
| `components/workspace/OnboardingTour.vue` | Renders overlay, spotlight cutout, tooltip cards, center modals via `<Teleport to="body">` |

**Tour Steps (8 steps)**

| # | ID | Type | Target | Title |
|---|----|------|--------|-------|
| 1 | welcome | center | — | ברוכים הבאים ל-Nifraim |
| 2 | production | spotlight | `[data-tour="production-uploader"]` | העלאת פרודוקציה |
| 3 | automation | spotlight | `[data-tour="tab-portal-automation"]` | הורדה אוטומטית |
| 4 | comparison | spotlight | `[data-tour="tab-comparison"]` | השוואת נפרעים |
| 5 | commission-rates | spotlight | `[data-tour="tab-commission-rates"]` | טבלת עמלות |
| 6 | company-emails | spotlight | `[data-tour="tab-company-emails"]` | אימיילים לחברות |
| 7 | settings | spotlight | `[data-tour="settings-gear"]` | הגדרות |
| 8 | done | center | — | !הכל מוכן |

**Spotlight mechanism:** Box-shadow cutout technique — a transparent `<div>` over the target with `box-shadow: 0 0 0 9999px rgba(0,0,0,0.55)`. Pulsing `::after` border draws attention. Overlay stays dimmed (`tour-overlay--dimmed`) until spotlight is ready, preventing visual flash during transitions.

**`data-tour` attributes** on target elements (minimal changes to existing components):
- `WorkspaceTabs.vue` — `:data-tour="'tab-' + tab.id"` on each tab button
- `WorkspaceHeader.vue` — `data-tour="settings-gear"` on settings button
- `ProductionUploader.vue` — `data-tour="production-uploader"` on drop zone

**Integration in `WorkspaceView.vue`:**
- Composable receives `activeTab` ref to auto-switch tabs during tour
- Tour starts 800ms after mount if `shouldShowTour()` returns true
- Keyboard: `Escape` = skip, `ArrowLeft` = next (RTL), `ArrowRight` = prev (RTL)

**Edge cases handled:**
- Target not in DOM (e.g., production store still loading): retries 6x at 300ms intervals, falls back to center-style card
- Window resize: debounced reposition at 100ms
- Tab animation timing: 450ms delay after tab switch before measuring target

**Testing:**
```js
// Keys are per-user: `onboarding_completed:<jwt-sub>`. Reset for the logged-in user:
Object.keys(localStorage).filter(k => k.startsWith('onboarding_completed')).forEach(k => localStorage.removeItem(k))  // Reset tour → reload page
```

---

## Critical Data Flow

### 1. Upload & Parse Pipeline
```
User drops Excel file
  → CommissionUploader.vue → POST /api/uploads
  → uploads.py: save file → parser_service.detect_format()
  → parser_service: decrypt if needed → map Hebrew columns → parse rows
  → sanitize_record() each row (truncate strings, convert dates)
  → bulk INSERT into client_records
  → Return upload metadata
```

### 2. Comparison Pipeline
```
User has production file + uploads commission file
  → POST /api/comparison/dual-upload
  → comparison_service.compute_comparison():
     1. Group production records by id_number
     2. Group commission records by id_number
     3. Match: both files → "matched" (compare products by fund_policy_number)
     4. Only production → "only_production"
     5. Only commission → "only_commission"
     6. For matched: classify products as paid/unpaid
  → Return ComparisonResponse { customers[], summary }
```

### 3. Frontend Display
```
ComparisonTab receives result
  → ComparisonDashboard: donut charts, bar charts, top unpaid list
     → Chart click → filter modal popup (customer list)
     → Customer click → CustomerDetailModal (product details)
     → "Open in table" → drill to ComparisonTable
  → ComparisonTable: sortable customer list with expandable details
     → Expand row → ComparisonDetail (side-by-side products)
```

### 4. Production Comparison (file-to-file diff)
```
User uploads new production file (replaces old)
  → POST /api/production/compare { current_upload_id, previous_upload_id }
  → Groups records by id_number, diffs premium/accumulation/products_count
  → Returns { summary, new_clients[], removed_clients[], changed_clients[] }

ProductionComparison.vue displays:
  1. Summary KPI strip (new/removed/changed/unchanged counts)
  2. Main donut (התפלגות שינויים) — click slice → filter modal
  3. Company breakdown donuts (חדשים/הוסרו לפי חברה)
  4. Changed insights section (שונו — תובנות):
     - KPI cards: total premium/accumulation diffs + counts by change type
     - Donut: change type distribution (פרמיה/צבירה/מוצרים)
     - Horizontal bar: top 10 changers with premium/accumulation toggle
  5. All charts drill into shared FilterModal → detail view

changed_clients[] structure per client:
  { id_number, name, company, premium_diff, accumulation_diff,
    changes: [{ field: "פרמיה"|"צבירה"|"מוצרים", old_val, new_val }] }
```

### 5. Customer Portal (Shareable Link)
```
Agent generates portal link (POST /api/portal/generate)
  → token_urlsafe(48), bcrypt password, 30-day expiry
  → Agent shares URL + password via WhatsApp/email

Customer opens /portal/:token
  → PortalPasswordForm → POST /api/portal/{token}/access (PUBLIC)
  → Verify: active + not expired + rate limit (5 fails/15min) + bcrypt
  → Returns portal JWT (4h, type:"portal", sessionStorage)

Authenticated customer → GET /api/portal/{token}/dashboard
  → Query ClientRecord WHERE user_id (agent) + id_number + active production
  → Returns: products[], KPIs (premium/accumulation/count), company_breakdown[]

Agent manages links in RecruitsTab → PortalLinksManager (collapsible section)
  → Generate modal: auto-fill name+email from production records
  → Copy URL, send email (SMTP), revoke per link
```

**Security**: Portal JWTs have `type: "portal"` — rejected by `decode_token()` (agent auth). Rate limiting stored in DB (`failed_attempts`, `last_failed_at`). Data doubly scoped: agent's `user_id` + customer's `id_number`.

**Key files**: `models/portal_link.py`, `services/portal_service.py`, `api/portal.py`, `CustomerPortalView.vue`, `stores/portal.js`, `components/portal/*`, `components/workspace/PortalLinksManager.vue`

---

## Hands-Free OTP: Android SMS Forwarder + Template Filter

Portal automation needs the SMS OTP an insurer sends to the agent's phone. The
agent installs the **Nifraim SMS** Android app (`android/`, native Kotlin) which
forwards qualifying SMS to a per-user webhook; the runner consumes the code.

**Chain**: insurer SMS → `SmsReceiver` → `OtpFilter` → `TemplateFetchWorker`-cached
templates → `WorkManager` HTTPS POST → `POST /api/portal-automation/phone-forward/{token}`
→ `otp_inbox` row → `runner._wait_for_otp()` polls (1s, 240s timeout) → `submit_otp`.

**Which SMS get forwarded** — `OtpFilter.shouldForward(sender, body, templates)`:
`BLOCK match → drop · ALLOW match → forward · fail-open (any 4-8 digit code) →
forward · else drop`. No templates cached yet → built-in keyword fallback. Personal
SMS without a code, and SMS matching a BLOCK template, never leave the device.

**Templates** are GLOBAL (one insurer's OTP wording is the same for every agent),
table `sms_otp_templates`, managed via `/api/sms-otp-templates` (CRUD + `/seed`)
and the "תבניות זיהוי SMS" manager in `PhoneForwardModal.vue`. The app fetches them
via `GET /api/portal-automation/phone-forward/{token}/templates` (token-auth) and
caches to Prefs. Patterns are plain regex (no inline flags), compiled
IGNORE_CASE + DOT_MATCHES_ALL on both device (Kotlin) and the JS test box, so one
stored pattern is portable. **Real insurer OTP text often omits the company name**
(Harel & Phoenix share `סיסמתך למכלול שלי`; Migdal uses `apmaccess`) — anchor on
the real wording, not the brand. Default patterns: `api/sms_otp_templates.py`.

**Tagging is for correctness, not just labels.** External drivers (the Windows
Phoenix-terminal flow) pull a code via `GET /phone-forward/{token}/next-otp?company=<base>`,
which returns the NEWEST unconsumed code preferring an exact `portal_kind` tag over an
untagged (NULL) one. An untagged real OTP shares the bucket with junk SMS (e.g. a
clearinghouse welcome whose phone number `OTP_REGEX` extracts as a fake code) → newest junk
wins. If a run grabs the wrong code with no cross-company race, seed the missing company
template (Phoenix's terminal SMS is brand-less `הסיסמה:NNNNNN`).

**Key files**: `android/app/src/main/java/com/nifraim/smsforwarder/{OtpFilter,TemplateFetchWorker,SmsReceiver,Prefs,MainActivity}.kt`,
`models/sms_otp_template.py`, `api/sms_otp_templates.py`, `api/portal_automation.py`
(webhook + templates endpoint), `models/otp_inbox.py`, `PhoneForwardModal.vue`.

**Testing**: see the `android-sms-test` skill for the Docker-emulator setup and the
proven live-run procedure. E2E: `backend/tests/test_template_filter_otp.py` (ALLOW/
FAIL-OPEN/BLOCK) and `test_full_otp_automation.py`. Build the APK via
`android/emulator-docker/build-apk.sh`; the Railway APK predates the filter and
must be re-uploaded.

---

## Mail Intake — הכשרה production arrives by EMAIL, not a portal

`companies/hachshara.py` downloads **נפרעים only**. הכשרה emails production as
`Ild_prod_<n>_<agent>_<DDMMYYYY>.zip`. Don't look for (or add) a Hachshara production
portal — there isn't one. **See `docs/ARCHITECTURE.md` §10 for the invariants.**

- **Parser**: `services/hachshara_prod/` — CP862 visual Hebrew, 2000-char fixed-width
  `SP`/`SB`/`RM`. Traps: ID is at `[6:15]` (SP/SB) / `[0:9]` (RM); **never gate on the TZ
  check digit** (half the real IDs fail it); the visual-Hebrew reverse must protect numeric
  runs or `בסט פרט 02/16` becomes `61/20`; SP accumulation is **whole shekels**, RM funds are
  agorot. `premium` and `fund_policy_number` do not exist in the file — leave them `None`.
- **Intake**: `services/mail_intake/` — the agent types only their email; `detect.py` resolves
  the MX and routes to Graph OAuth (M365) / IMAP app-password (personal Gmail only) /
  forwarding via Resend (everything else, incl. Google Workspace). All three converge on
  `ingest_mail_attachment`, the only seam onto `upload_ingest`.
- **Local e2e without any provider account**: `backend/scripts/simulate_hachshara_mail.py`.
- Tests: `tests/test_hachshara_prod_parser.py`, `tests/test_mail_intake.py`.

---

## Windows-Native Terminal Production (Phoenix `phoenix_terminal`)

Most portals are Playwright plugins (`services/portal_automation/companies/`), but Phoenix
production lives in a native Ericom **PowerTerm** green-screen, not the DOM. It is a
`WORKER_ONLY_PORTALS` entry (not in `REGISTRY`); the local worker subprocesses
`backend/scripts/windows/phoenix_terminal_run.py` to run it. Flow: close stale TERM windows →
`phoenix_browser_win.py` (Edge login + hands-free OTP) → `phoenix_win_terminal.py export`
(SendInput: **wait for the menu to PAINT** → `13` → Enter → Enter×4 → down-arrow×1 to pick the
month → Hebrew `כ` + **Enter** → KERMIT download to `C:\fnxbox`) → `phoenix_mu.parse_phoenix_mu`
→ ingest as production/הפניקס.

- **Never type into a screen the host hasn't painted.** The `TERM` window exists before the host
  paints the menu, and keys sent into that gap are swallowed — the `13` is lost and nothing
  downloads. `wait_for_menu()` gates on the pixels (menu ≈ 11% green, blank gap ≈ 0.3%), then the
  code *verifies* the `13` advanced the screen. A fixed sleep is a guess at a race.
- **A silent no-op must never look like a download.** With no transfer, the naive next step ingests
  the newest MU on disk = **last run's** (live: yesterday's 261 records served as today's). No file
  change → `SystemExit(4)`; MU older than 45 min → refuse to ingest. **See `docs/ARCHITECTURE.md`
  §11 for the full invariants.**

- **Two-Python split (WSL box).** The orchestrator runs on the **WSL venv** (app/DB deps) and
  shells the GUI sub-steps to **Windows Python** (`PHOENIX_WIN_PYTHON`, auto-detected
  `/mnt/c/Python313`), translating `C:\…`→`/mnt/c`. On a native-Windows worker one venv has
  both, so it's a no-op.
- **MU file parses directly to production** — no external MU→.MBT converter. `phoenix_mu.py`:
  accumulation is `[70:75]` **whole shekels (no /100)**; the file has NO customer names; premium
  left None (not fabricated). Mirrors `phoenix_terminal.py`'s `PRODUCTION_COLUMNS`.
- **Key files**: `scripts/windows/{phoenix_terminal_run,phoenix_browser_win,phoenix_win_terminal}.py`,
  `services/phoenix_mu.py`, `services/phoenix_terminal.py`. See memory `phoenix_terminal_production`.

---

## Score-Gated Portals (מור, מיטב) — the browser must look like a human's

Mor and Meitav are refused by a **reCAPTCHA score**, not by anything wrong in the request.
Mor answers `400 {"resultCode":"Bad Request"}` (shown to the agent as `אירעה שגיאה`) to a
perfectly formed login. **See `docs/ARCHITECTURE.md` §4c for the proven configuration, the
disproven list, and the invariants** — that section was rewritten 2026-07-20 after ~9
hypotheses died, and the version it replaced asserted a cause that is now refuted.

The short version, all measured (Mor reproduced green twice from a dev box, then live on the
agent's worker: 490 records):

- **Config that passes**: headed · real Chrome/Edge (never bundled Chromium) ·
  `--disable-blink-features=AutomationControlled` always · **no** `navigator.webdriver` JS
  patch (that one IS detectable) · `no_viewport` + `--start-maximized` on headed runs ·
  a fresh, **unwarmed** profile.
- **A poisoned profile beats every downstream fix.** The `_GRECAPTCHA` cookie is the
  accumulated reputation, so each rejection makes the next attempt worse — correct fixes stay
  invisible underneath it. Cold profiles are FINE; repeatedly-failed ones are not.
- **The captcha token is an HTTP HEADER**, not a body field
  (`logIn() → HttpHeaders({recaptcha: tok})`). Body-only instrumentation shows a flawless
  payload while the request is refused — the misreading that cost days.
- **Mor's licence is 8 digits, NOT zero-padded** (only ת"ז→9, phone→10).
- **Debug by reproducing locally first**: Windows Python (`/mnt/c/Python313`) driving real
  Edge/Chrome runs the same flow in minutes, and `curl` the portal's own JS bundle to see what
  it really sends. Both beat live-run guessing — that is what finally cracked Mor.
- **Meitav inherits the runner-level fixes automatically** (same three flags) but is a
  DIFFERENT mechanism: reCAPTCHA **Enterprise** (`grecaptcha.enterprise.*`, not
  `grecaptcha.execute`) plus an **Akamai Bot Manager** sensor. Reproduced green locally
  (form paints, submit enables, OTP screen reached), so `לא נמצאו שדות` is the ~19% hydration
  race — not a login bug. Its probe read Mor's API surface and therefore blamed the agent's
  antivirus on a healthy page; corrected.

---

## Local Worker & Self-Update (`local-worker` skill)

Israeli insurer WAFs geo-block Railway's foreign IP, so the portal automation runs on the
agent's **local Windows machine in Israel** (the "worker"), which points its DB at prod and
ingests there. The website button only *creates* the batch; if a worker is online
(`worker_heartbeats.last_seen` ≤ 90s) Railway leaves it pending for the worker to claim, else it
runs inline and the IL portals fail.

**The worker is a DOWNLOADED BUNDLE, not a git checkout.** Code lives at
`C:\Users\<user>\AppData\Local\Nifraim\` (no `.git`), delivered by
`GET /api/portal-automation/worker/bundle/{token}` (zip of `backend/app/**` + `local_worker.py` +
`requirements.txt` + `scripts/windows/**`). **Never `git pull` the worker** — updates mean
**re-downloading the bundle**, which reflects Railway's deployed code (so `railway up` first).

**"עדכן עובד" self-update button** (`PortalActivityPanel.vue` → `POST /worker/request-update`):
sets `worker_heartbeats.update_requested_at`; the worker's `_maybe_self_update` (each heartbeat,
≤15s) sees a flag newer than its start, downloads+extracts the bundle in-process, and `os.execv`
re-execs. The download is in-memory → it never lands in the browser Downloads folder (by design;
users handle nothing). A stale flag self-clears so the UI doesn't stick on מתעדכן…. Debug via
`railway logs | grep WORKER-LOG` (the worker POSTs progress to `/worker/log/{token}`) and the
worker's file mtimes. A worker can be **online but on stale code** — verify after updates.

See the **`local-worker` skill** for the full architecture, the bootstrap path (updating a
pre-self-update worker), and gotchas (Phoenix terminal needs an ELEVATED worker for SendInput).

---

## Patterns & Conventions

### Backend

| Pattern | How |
|---------|-----|
| **Async everywhere** | All DB operations use `AsyncSession`, `await session.execute()` |
| **User scoping** | Every query filters by `user_id` — strict multi-tenancy |
| **Dependency injection** | `Depends(get_db)`, `Depends(get_current_user)` on every route |
| **Service layer** | Routes are thin (validate + call service). Logic lives in `services/` |
| **Format detection** | `detect_format()` checks column names against signature sets |
| **Hebrew column mapping** | Centralized in `hebrew_mappings.py`, never hardcoded in parsers |
| **Data sanitization** | `sanitize_record()` runs on every row before DB insert |

### Frontend

| Pattern | How |
|---------|-----|
| **Composition API** | `<script setup>`, `ref()`, `computed()`, no Options API |
| **Store-driven API** | Components access API through Pinia stores (except self-contained CRUD tables) |
| **Teleport modals** | All modals use `<Teleport to="body">` with overlay + card pattern |
| **CSS variables** | Salesforce Lightning Design tokens in `App.vue` root styles — never hardcode colors |
| **Conditional amounts** | Only show financial values when > 0, never show dashes for empty |
| **Empty state decoration** | Pre-upload / empty states use floating orange blur circles (`position: fixed`, `border-radius: 50%`, `rgba(245,124,0,...)`, `floatBob` animation) + animated SVG waves at page bottom (`position: fixed; bottom: 0`, 3 layers with gradient fills + shimmer sweep masked to wave shape). See `ProductionUploader.vue` and `CommissionUploader.vue` as reference. Use unique SVG gradient IDs per component (e.g. `wg1` vs `cwg1`). |

### Naming Conventions

| Context | Convention | Example |
|---------|-----------|---------|
| Python functions/vars | snake_case | `parse_excel()`, `id_number` |
| Python classes | PascalCase | `ClientRecord`, `FileUpload` |
| Vue components | PascalCase files | `ComparisonDashboard.vue` |
| Vue props/methods | camelCase | `drillCustomerId`, `onDrillCustomer()` |
| CSS classes | kebab-case | `.chart-card`, `.fm-overlay` |
| Pinia stores | camelCase with `use*Store` | `useComparisonStore()` |
| API routes | kebab-case paths | `/api/commission-rates` |
| DB columns | snake_case | `fund_policy_number`, `reconciliation_status` |

---

## How to Add a New Insurance Company Parser

This is the most common task. Follow this exact pattern:

### 1. Inspect the Excel file first
```python
import pandas as pd
df = pd.read_excel("file.xlsx")
print(df.columns.tolist())  # Get actual Hebrew column names
print(df.head())             # See data shape
```

### 2. Add to `hebrew_mappings.py`
```python
NEW_COMPANY_COLUMNS = {
    "Hebrew Column": "db_field_name",
    # ... map each relevant column
}
NEW_COMPANY_SIGNATURE = {"unique_col_1", "unique_col_2"}  # 2+ columns unique to this format
# Add new keywords to HEADER_SCAN_KEYWORDS if needed
```

### 3. Add to `parser_service.py`
- Import new mappings
- Add detection in `detect_format()` (order matters — more specific signatures first)
- Add routing in `parse_excel()`
- Add `_parse_new_company(df)` function following existing patterns:
  - Map columns, parse types, clean id_number, split names if needed
  - Hardcode `receiving_company`, set `reconciliation_status = "no_data"`
  - Skip rows without id_number

### 4. If new DB columns needed
- Add to `models/record.py`
- Create Alembic migration
- Add to `schemas/record.py` (RecordOut)
- Add to `utils/sanitize.py` (MAX_LENGTHS)

### 5. Frontend — usually no changes needed
Company names are dynamic. New companies appear automatically in filters and charts.

---

## Common Pitfalls

| Issue | Solution |
|-------|----------|
| **pandas Timestamps in asyncpg** | Convert to Python `date` via `sanitize_record()` |
| **String too long for VARCHAR** | `sanitize_record()` truncates to MAX_LENGTHS |
| **Excel "Unnamed" columns** | Check row 0 for real headers, reassign if needed |
| **Hebrew column name mismatch** | Always inspect actual file columns, never assume |
| **Password-protected .xls** | Use `decrypt_xls()` with msoffcrypto |
| **Vite orphaned `-webkit-` CSS** | Old dark-theme artifacts — delete standalone `-webkit-` lines |
| **Node 18 compatibility** | Use Vite 5, not Vite 7+ (requires Node 20) |
| **Leading zeros in IDs** | Volume reports have `058661554`, production stores `58661554`. Always `lstrip('0')` |
| **Multi-sheet Excel files** | Volume reports have multiple sheets per company. Use `pd.ExcelFile` + iterate `sheet_names` |

---

## Supported Company Formats

| Format Key | Company | File Type | Detection Signature |
|------------|---------|-----------|---------------------|
| `agent_tracking` | אקסלנס (Excellence) | xlsx | `{"חברה מקבלת", "סוג מכשיר"}` |
| `company_report` | הפניקס (Phoenix) | xls (pw) | `{"חברה מנהלת", "סוג מוצר"}` |
| `nifraim` | מור (Mor) | xlsx | `{"עמלת סוכן", "מספר מפיק"}` |
| `hachshara_nifraim` | הכשרה (Hachshara) | xlsx | `{"סכום עמלה סוכן ללא מעמ", "יתרת צבירה"}` |
| `menora_nifraim` | מנורה (Menora) | xlsx | `{"שם סוכן ראשי", "דמי ניהול מצבירה"}` |
| `altshuler_nifraim` | אלטשולר (Altshuler) | xlsx | `{"שיעור עמלה", "דמי ניהול"}` |
| `clal_life_nifraim` | כלל חיים (Clal Life) | xlsx | `{"ת.ז/מזהה מבוטח ראשי", "סך עמלה מפרמיה"}` |
| `clal_health_nifraim` | כלל בריאות (Clal Health) | xlsx | `{"זיהוי מבוטח", "תשלום עמלה בפועל - נפרעים"}` |
| `migdal_nifraim` | מגדל (Migdal) | xlsx | `{"פרמיה משולמת", "ת.ז מבוטח"}` |
| `ayalon_nifraim` | איילון (Ayalon) | xlsx | `{"פרמיה נפרעת", "סך עמלת סוכן"}` |
| `harel_nifraim` | הראל חיים ובריאות (Harel life/health) | xlsx | `{"סכום תשלום", 'אופי חו"ז'}` |
| `harel_savings_nifraim` | הראל גמל / מגוון (Harel savings/pension) | xlsx | `{"צבירה/צבירה פרט/דמי ניהול", "הסכם סוכן"}` |
| `production` | Agent production | xlsx | `{"תאריך הצטרפות", "סטטוס מוצר"}` |
| `volume_report` | דוח היקפים (multi-sheet) | xlsx | `{"תפוקה לאחר ביטולי שנה א", "רמת גורם"}` |

---

## Period Detection (`period_month` on every upload)

Every `FileUpload` row carries a nullable `period_month` (first-of-month `date`)
representing **which reporting month the file is FOR** — not when it was uploaded.
Israeli insurers report commission ~30 days late, so a file uploaded in May
usually contains April data. The dashboard, AI service, and trend chart all
depend on this being right.

Resolution order (`detect_period_month` in `backend/app/services/parser_service.py:87`):

| # | Source | Example | Notes |
|---|--------|---------|-------|
| 1 | Hebrew month name + year in filename | `הפניקס גמל מרץ 26.xlsx` → 2026-03 | Most files match here |
| 2 | Numeric MM/YY or MM/YYYY in filename | `03-26.xlsx`, `12_2025` | |
| 3 | Hebrew month only in filename | `הכשרה נפרעים אפריל.xlsx` uploaded May 2026 → 2026-04 | Year inferred from `uploaded_at`, capped at upload month (Dec uploaded in Jan → previous year) |
| 4 | Record data dates: `sign_date` → `transfer_date` → `rights_assignment_date` → `processing_date` | | `processing_date` LAST — it's the report-generation date and drifts into the next month |
| 5 | `uploaded_at` | | Least reliable fallback |
| 6 | `None` | | No period — excluded from period-aware aggregations |

**Filename-first rationale (flipped 2026-05-18):** data-date inference was
demoting April production files to May because some `processing_date` values
landed in early May.

**Symptoms when this goes wrong:**
- A trend column appears for a month the agent never uploaded → a file without
  a month in its filename fell to step 4 or 5. Likely culprits: files named with
  opaque numeric codes (`הראל נפרעים מגוון 9345.xlsx`, `עמלות כלל חיים.xlsx`).
- Dashboard "עמלות שהתקבלו" undercounts → period_month=NULL files are excluded
  from the per-company-latest-period sum.

**Fixes:**
- Add the missing month to the filename (`... מרץ 26.xlsx`) and re-upload — the
  upload pipeline replaces on `(user, filename, category)`.
- Extend `detect_period_month` for new naming patterns rather than touching
  callers — every commission/production endpoint depends on this one function.

---

## Volume Report (דוח היקפים) — Multi-Sheet Parsing

Volume reports are **multi-sheet Excel files**. Each sheet is a different company with a different column layout. The parser reads ALL sheets.

### Sheet Structure
- **Sheet 1 (e.g., "פניקס גמל")**: Standard format with `רמת גורם` column. Has agent+agency duplicate rows — filter by `רמת גורם == 'סוכן'`. Detected via `VOLUME_REPORT_SIGNATURE`.
- **Other sheets (e.g., "הראל", "מור קופג", "מנורה", "ילין גמל")**: Each has unique columns. Parsed by `_parse_volume_sheet_other()` which auto-detects ID/name/deposit columns.

### Column Detection for Other Sheets
ID columns: `ת.ז עמית`, `ת.ז. עמית`, `תז עמית`, `זהות לקוח`, `מס.זהות`, `ת.ז לקוח`, `תז לקוח`, `ת.ז מבוטח`
Name columns: `שם עמית`, `שם לקוח`, `שם מבוטח`
Deposit columns: `סכום פעולה ב-₪`, `סכום תנועת הפקדה`, `סכום העברה בפועל`, `נטו`, `סהכ תפוקה לתגמול`, `הפקדה חד פעמית`, `פרמיה נמדדת`, `סהכ פרמיה לתגמול`, `תנועות העברה פנימה לפי תאריך הצטרפות`
Product columns: `סוג מוצר`, `סוג קופה`, `שם מוצר`, `סוג קופה מעבירה`

The **sheet name** is used as `product_type` for non-standard sheets (e.g., "מור קופג", "מנורה").

### Data Flow
```
Volume file uploaded → parse_excel() detects volume_report from sheet 0
  → _parse_volume_report(df, file_bytes, engine)
     → _parse_volume_sheet_standard(df)  — sheet 0 (אקסלנס format)
     → _parse_volume_sheet_other(df, sheet_name)  — sheets 1..N
  → Returns combined { clients[], agency_rates, summary }

Comparison: compare_volume() matches volume clients vs production by id_number
Bonus: calculate_bonus() groups by product_type, looks up rates in DB
```

### Key Files
| File | Role |
|------|------|
| `parser_service.py` | `_parse_volume_report()`, `_parse_volume_sheet_standard()`, `_parse_volume_sheet_other()` |
| `volume_service.py` | `compare_volume()`, `calculate_bonus()` |
| `api/volume.py` | Upload+compare, calculate bonus, bonus payment CRUD |
| `models/volume_commission_rate.py` | Per-company rates (rate_per_million, payment_frequency) |
| `models/volume_bonus_payment.py` | Paid/unpaid tracking per company+year |
| `VolumeComparison.vue` | Upload, KPI strip, donut chart, drill-down modal |
| `VolumeBonus.vue` | Bonus table with paid status dropdown |
| `stores/volume.js` | API calls, state management |

### Standard Sheet: Agent vs Agency Rows
The standard sheet (אקסלנס format) has `רמת גורם` column. Rows are either `סוכן` (agent) or `סוכנות` (agency).
- **Important**: `ן` (nun sofit) ≠ `נ` (nun), so `"סוכן" in "סוכנות"` is **False** in Python.
- If agent rows exist → use only agent rows (avoid double-counting).
- If only agency rows exist (e.g., 2024 format with `סוכנות ראשית`) → use those.

### Multi-Sheet Detection
- `parse_excel()` first tries sheet 0 for the volume_report signature.
- If sheet 0 doesn't match, scans other sheets. When found, passes `standard_sheet_idx` so all other sheets are parsed as "other" format.
- Example: 2024 file has אלטשולר on sheet 0, אקסלנס on sheet 3 — parser correctly finds sheet 3 as standard and parses all 8 sheets.

### ID Number Handling
**Critical**: Volume reports may have IDs with leading zeros (e.g., `058661554`). Production stores without (e.g., `58661554`). All parsers and comparison functions must strip leading zeros: `id_str.lstrip('0') or '0'`.

---

## Agent Instructions

- **Read `docs/ARCHITECTURE.md` first** for the wiring map, data-flow graphs, and the invariants you must not break.
- **Read before writing.** Never modify a file you haven't read first.
- **Check `hebrew_mappings.py`** before touching any parser code. Check `App.vue` for CSS variables before styling.
- **Preserve patterns.** Every parser, modal, and store follows the same structure. Don't break it.
- **Hebrew is primary.** All UI text is Hebrew. Numbers use `.ltr-number` class.
- **Check `.claude/plans/`** for active plans before starting new work.
- **Key entry points**: `parser_service.py`, `comparison_service.py`, `ComparisonDashboard.vue`, `App.vue`
- **Review checklist**: pandas Timestamp conversion, string sanitization, `user_id` scoping, z-index stacking, Hebrew column names match actual Excel files.
- **Excel test files** may be in project root or `/mnt/c/Users/roygi/Desktop/KIKO/`
