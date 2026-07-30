# הפניקס (Phoenix) — `phoenix_nifraim` / `phoenix_nifraim_gemel` / `phoenix_terminal` / SFE vault

Multiple planes — Phoenix is the most fragmented insurer.

| Plane | Kind | Notes |
|---|---|---|
| Agent portal SPA (נפרעים) | `phoenix_nifraim`, `phoenix_nifraim_gemel` | חא"ט/בריאות → production reshape. `07-24: הפניקס נפרעים חאט ובריאות.xlsx` ✓ |
| **Terminal (PRODUCTION)** | `phoenix_terminal` | Native Ericom **PowerTerm** green-screen — NOT the DOM. `WORKER_ONLY_PORTALS`. `07-24: הפניקס פרודוקציה 07-2026.xlsx` ✓ |
| SFE כספת (production) | `phoenix_sfe` | OTP-less ExtJS vault, newest `.DAT` = production |

## Terminal — the hard one (memory `phoenix_terminal_production`, `phoenix_terminal_other_workers`)
- Windows-native: WSL orchestrator shells GUI sub-steps to **Windows Python** (`PHOENIX_WIN_PYTHON`).
- **Never type into a screen the host hasn't painted** — `wait_for_menu()` gates on pixels, then
  verifies the `13` advanced the screen. A fixed sleep is a race.
- **A silent no-op must never look like a download** — no file change → `SystemExit(4)`; MU older than
  45 min → refuse to ingest (avoids serving yesterday's file).
- MU parses directly to production: accumulation `[70:75]` whole shekels (no /100); no names; premium None.
- Needs an **ELEVATED** worker for SendInput; PowerTerm only on the right machine (DESKTOP-M443DUC).

## Status: WORKING (07-24 batch: both נפרעים and terminal production succeeded)
See `docs/ARCHITECTURE.md` §11.

## ⛔ "הפניקס: 262 מופקים / 0 תואמו" is EXPECTED — do not chase it as a bug

The comparison's *סיכום לפי חברה* shows Phoenix producing 262 rows and matching **zero**.
Investigated 2026-07-29 and it is **not** a policy-format bug. Three transform hypotheses
were tested against live data and all died:

| Hypothesis | Result |
|---|---|
| Prefix truncation (the מנורה `[4:11]` bug) | no prefix relationship |
| Dashed policy carries the real number in its last segment (`664-934-691529` → `691529`) | **0/587** |
| Production policy embedded as a substring of the נפרעים one | **0/384** same-customer pairs |

**The two sides cover disjoint product lines.** Production (terminal MU) is 261× `ביטוח חיים`
with 6-digit policies (`100324`). נפרעים under `הפניקס חברה לביטוח` is 52 rows of
`בריאות`/`משכנתאות`/`ריסק פרט`/`אכ"ע` with 10-digit policies (`0599410008`) — **no life rows at all.**

**Why, and when it changes:** Phoenix **חיים נפרעים comes from the מסלקה**, which is not connected
(`MASLAKA_ENABLED=false` — see `docs/ARCHITECTURE.md` §12). Until the clearinghouse vault is open
there is no counterpart for those 261 policies and 0-matched is arithmetically correct. Same reason
מור / מיטב / ילין / אנליסט show `0 / 0 / 0` — gemel/pension houses whose production is מסלקה
territory. (הכשרה is unrelated: its production arrives by **email**.)

Two side observations from the same investigation:
- Phoenix production is financially empty regardless — 262 rows, **1 name**, **premium 0 on all 262**,
  accumulation all NULL (inherent to the MU source). Even a perfect match would compare nothing.
- The 594 dashed rows (`006-204-092754`) belong to **הפניקס אקסלנס פנסיה וגמל** — a different legal
  entity, no production, also מסלקה territory.
- One cross-contaminated row: policy `3469898088` with `receiving_company=הפניקס` but
  `product='מגדל - חיים'`.
