# Skill: Phoenix (הפניקס) Terminal — Hands-Free Auto-Download of Production

**Status:** ✅ Working end-to-end (LIVE-verified 2026-06-25). Logs in hands-free
(OTP via the phone-forward webhook), opens the PowerTerm terminal, and downloads
`MU_NK_HAYV_MOSHE_<period>` to `C:\fnxbox\` — fully automatic.

Phoenix is unlike Migdal/Harel/Menora: its production data lives only in a **native
PowerTerm WebConnect green-screen terminal** (Ericom), not a web download. So this
half runs **on Windows** (driven from WSL via `/mnt/c/Python313/python.exe`), not on
the Linux/Railway server. The OTP, however, can come from the **production Railway
backend**, so the terminal box only needs network + the Windows Python env.

---

## The full chain (4 stages)

```
1. phoenix_browser_win.py   Windows Edge → login → OTP (webhook) → opens terminal
2. phoenix_win_terminal.py  drives the terminal → MU_NK_HAYV_MOSHE_<period> in C:\fnxbox
3. [Phoenix converter]      MU_NK_HAYV → LIFE.MBT / COVRLIFE.MBT / LIFEHLTH.MBT  (user side)
4. services/phoenix_terminal.py   .MBT set → production records → ingest as production/הפניקס
```

### 1. Browser → login → open the terminal (`phoenix_browser_win.py`)
```bash
/mnt/c/Python313/python.exe scripts/windows/phoenix_browser_win.py \
    <username> <password> <phone_forward_token> [backend_base]
# backend_base defaults to http://127.0.0.1:8000 ; use the Railway URL to poll prod.
```
Drives real Microsoft Edge (channel `msedge`) so the native PowerTerm client launches.
Flow: `agent.fnx.co.il/my.policy` → F5 `errorcode=19` recovery (`התחבר מחדש`) → fill
`input[name=username]`/`password`, submit → **HANDS-FREE OTP**: poll
`{base}/api/portal-automation/phone-forward/{token}/next-otp?company=phoenix&after=<ts>`
(the endpoint returns + consumes the newest matching code from `otp_inbox`) → fill it →
dismiss the post-login `cdk-overlay-backdrop` → `img[src*=my-systems.svg]` → menuitem
`ביטוח חיים` → `התחבר` → PowerTerm terminal opens (own window, class `TERM`).

**OTP gotchas (both fixed in the driver):**
- **Clock skew:** backdate the `after` cutoff **15s** (`datetime.utcnow() - 15s`). The
  instant-forward app can deliver the code a fraction of a second "before" the cutoff on a
  differently-skewed clock (Railway vs Windows) and it gets excluded. 15s absorbs skew
  without grabbing stale codes (120s was too much — it pulled old codes → login failed).
- **Phone forwards instantly:** the Android app posts the OTP immediately via `goAsync()`
  (was a deferrable WorkManager job that Doze delayed minutes → codes expired). The phone
  must run the NEW APK. See memory `sms_forward_immediate`.

### 2. Terminal → download (`phoenix_win_terminal.py export`)
Runs **elevated** (UAC). The host answers only in painted characters, so a keystroke that
misses is **silent**. The verified sequence (keyboard-mode aware — the host reads the Windows
layout):
```
WAIT for the menu to PAINT  →  [ENGLISH] "13"  →  Enter  →  Enter ×4
   →  Down-arrow ×1 (newer month row)  →  [HEBREW] 'כ'  →  Enter
```

**Never type into a screen the host has not painted** (this is the whole ballgame). The `TERM`
window exists the moment PowerTerm creates it, but the host paints the menu seconds later and
every key sent into that gap is **swallowed** — the `13` is lost, nothing is selected, no
transfer starts. `wait_for_menu()` polls the pixels instead of guessing:

| screen | ink | bright green |
|---|---|---|
| painted main menu | ~21% | ~11% |
| black pre-menu gap | ~2% | ~0.3% |

Gate at `green ≥ 5%` (`MENU_GREEN_MIN`) **and** two identical samples — a half-drawn screen
loses keys too. A fixed sleep is a guess at a race: an 8s guess is exactly what let the `13`
vanish on some days and not others.

- **Prove the `13` registered.** Selecting option 13 must replace the menu screen; if the
  screen is unchanged the keys went nowhere → retype once, then `SystemExit(4)`. The digits and
  their Enter are typed as **separate** steps, so `export_1_typed13.png` answers "did the 13
  land?" on its own.
- **Enters: 5, not 6** — one submits the `13`, then 4 more (`MENU_EXTRA_ENTERS`).
- **Down-arrow, not F4** — F3/F4 only PAGE (`לדפדוף`). Use the **extended** arrow
  (`_press_arrow_down()`); a naive VK_DOWN is read as numpad-`2` under NumLock and the
  highlight never leaves row 1 (the older month).
- `כ` (scancode `0x21`, the physical כ/f key) triggers a **KERMIT** receive of the selected file
  to `C:\fnxbox\`, and **does nothing until Enter submits it**. The layout must be Hebrew for
  the scancode to render as `כ` (not `f`): set it **deterministically** via `_ensure_hebrew()`
  (LoadKeyboardLayout + WM_INPUTLANGCHANGEREQUEST), **never** a blind `Alt+Shift` toggle — the
  screen is already Hebrew, so a toggle flips it to English and types `f` (live bug 2026-06-30).

**Two things that make KERMIT actually COMPLETE (it stalled at block 6 before):**
- **Drive the LIVE terminal, not a zombie.** PowerTerm can leave a stale `TERM` window;
  `find_term()` returns the first in z-order, which may be the dead one (it kept driving the
  stale `hwnd` while the fresh login opened a different `hwnd`). Close stale terminals / target
  the newest before driving.
- **Keep PowerTerm FOREGROUND during the transfer and DO NOT `grab()`.** `grab()`
  force-foregrounds + toggles topmost + PrintWindow: between the `כ` and its Enter that steals
  the command-field focus (the Enter misses — the original bug), and during the receive it
  stalls KERMIT at block 6 / 0 B/s. Windows also throttles a backgrounded window's message loop
  and starves the receive, so the wait loop calls `SetForegroundWindow(hwnd)` every ~4s, polls
  the **filesystem** only, and waits for the file size to stabilize.
  Need evidence in that window? Use **`_shot()`** — passive, reads screen pixels and touches
  neither focus nor z-order (it saves `export_3_kaf_typed.png`, the `כ` sitting un-submitted in
  the command field).

**"Success" is not evidence of freshness — the dangerous failure.** When the keystrokes silently
do nothing, no MU file is written, and the naive next step ingests the *newest MU on disk* =
**last run's**. Live 2026-07-14: two runs reported green while serving **yesterday's 261 records
as today's production**. Hence: no file change → `SystemExit(4)`, never exit 0; `_parse_and_ingest`
refuses any MU older than `_MU_MAX_AGE_S` (45 min); and every run logs the chosen file's real
mtime + age (`MU file: … written 2026-07-14 14:31:58 (1.3 min ago)`).

### 3. Parse MU_NK_HAYV → production (`backend/app/services/phoenix_mu.py`)
**There is NO MU→.MBT converter step — do not reintroduce one.** `parse_phoenix_mu` reads the
downloaded `MU_NK_HAYV_*` (CP862) straight into production-schema records
(`company_source="הפניקס"`; `יצרן/סטטוס מוצר/סה"כ פרמיה` signature so `detect_format`→production),
mirroring `phoenix_terminal.py`'s `PRODUCTION_COLUMNS`. Traps: accumulation is `[70:75]` **whole
shekels (no /100)** — the trailing 2 bytes are a product code; the file carries **no customer
names**; `premium` is left `None`, never fabricated. `_period_from_mu` maps
`MU_NK_HAYV_MOSHE_2026_07` → `07-2026` so `detect_period_month` (filename-first) resolves the
reporting month. `_newest_mu()` picks by **mtime**, i.e. the file this run just wrote — which is
only safe because of the freshness guard above. See memory `phoenix_terminal_production`.

---

## Run it (end to end, local backend)
```bash
cd /home/roygi/test/backend
# 1) login + open terminal (hands-free OTP — forward the SMS from the phone)
PYTHONUNBUFFERED=1 /mnt/c/Python313/python.exe -u scripts/windows/phoenix_browser_win.py \
    <user> <pw> <token> https://nifraim-production.up.railway.app
# 2) drive the terminal (elevated — accept UAC). Best to ARM this FIRST so it waits:
powershell.exe -Command "Start-Process -FilePath 'C:\Python313\python.exe' \
  -ArgumentList 'C:\fnxbox\phoenix_win_terminal.py','export' -Verb RunAs"
# result + log: C:\fnxbox\term_action.log ; file: C:\fnxbox\MU_NK_HAYV_*
```
Copy the driver to `C:\fnxbox\` first (`cp scripts/windows/phoenix_win_terminal.py /mnt/c/fnxbox/`).

**Prereqs:** Windows Python `/mnt/c/Python313/python.exe` with `pywin32`, `Pillow`,
`playwright` (channel `msedge`); PowerTerm WebConnect 5.8 client installed.

**Edge relaunch race:** if the browser driver hangs at launch, kill orphaned playwright
`node.exe` + automation `msedge.exe` and settle ~7s before relaunching.

**No-UAC / unattended:** register a Windows **Scheduled Task** (highest privileges) running
`phoenix_win_terminal.py export` to avoid the per-run UAC prompt.

---

## Sub-actions (debugging)
`grab` (screenshot the TERM window), `send "13\n"` (send keys), `export` (full sequence).
All write to `C:\fnxbox\term_action.log` + `export_*.png` step captures.
