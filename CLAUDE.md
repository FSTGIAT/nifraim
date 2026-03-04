# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# InsureFlow — Insurance Reconciliation Dashboard

Read `.xlsx` files, parse Hebrew columns, reconcile production vs. commission records, and present insights through a Hebrew RTL interface. Before writing code, plan the architecture and document it in `.claude/plans/`.

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
            └── <main>
                 ├── ProductionTab
                 │    ├── ProductionUploader   (drag-drop upload)
                 │    └── ProductionFileInfo   (file metadata)
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
                 │    └── RecruitComparisonResults
                 ├── CommissionRatesTab
                 │    └── CommissionRateTable
                 └── CompanyEmailsTab  (self-contained CRUD)
```

### Routing & Auth

```
/login    → LoginView    (public)
/register → RegisterView (public)
/         → WorkspaceView (requiresAuth)
/dashboard → DashboardView (requiresAuth)
/analytics → AnalyticsView (requiresAuth)
```

- `router/index.js` uses `beforeEach` guard checking `localStorage.getItem('token')`
- Unauthenticated users redirect to `/login`; authenticated users redirect away from login/register

### API Client (`api/client.js`)

- Axios instance with `baseURL: '/api'` (Vite proxy to backend:8000)
- **Request interceptor:** adds `Authorization: Bearer ${token}` from localStorage
- **Response interceptor:** on 401 → remove token + redirect to `/login`
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
- **Z-index stacking**: Drop overlay: 9999, Detail modal: 1010, Filter modal: 1000, Header: 100, Tabs: 90.
- **Charts**: ApexCharts with Heebo font. Chart click → filter modal → customer drill-down.

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
| `production` | Agent production | xlsx | `{"תאריך הצטרפות", "סטטוס מוצר"}` |

---

## Agent Instructions

- **Read before writing.** Never modify a file you haven't read first.
- **Check `hebrew_mappings.py`** before touching any parser code. Check `App.vue` for CSS variables before styling.
- **Preserve patterns.** Every parser, modal, and store follows the same structure. Don't break it.
- **Hebrew is primary.** All UI text is Hebrew. Numbers use `.ltr-number` class.
- **Check `.claude/plans/`** for active plans before starting new work.
- **Key entry points**: `parser_service.py`, `comparison_service.py`, `ComparisonDashboard.vue`, `App.vue`
- **Review checklist**: pandas Timestamp conversion, string sanitization, `user_id` scoping, z-index stacking, Hebrew column names match actual Excel files.
- **Excel test files** may be in project root or `/mnt/c/Users/roygi/Desktop/KIKO/`
