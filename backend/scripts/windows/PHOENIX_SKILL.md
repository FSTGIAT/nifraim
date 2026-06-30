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
Runs **elevated** (UAC). From the MAIN MENU, the operator's EXACT sequence, keyboard-mode
aware (the host reads the Windows layout):
```
[ENGLISH] "13" + Enter  →  Enter ×5  →  F4 (select newest file)  →  [HEBREW] 'כ'
```
- `13` reaches the file-list (`MU_NK_HAYV_MOSHE_05`, `_06`, …).
- **Select the file with F4, NOT the arrow key** — the down-arrow registers as numpad-`2`
  (NumLock on) and types into the field instead of moving the selection, so it downloads the
  wrong (top) row. The on-screen hint literally says `(F3/F4)בחירה`. F4 = next/down.
- `כ` (scancode `0x21`, the physical כ/f key) triggers a **KERMIT** receive of the selected
  file to `C:\fnxbox\`. The layout must be Hebrew for the scancode to render as `כ` (not `f`):
  set it **deterministically** via `_ensure_hebrew()` (LoadKeyboardLayout + WM_INPUTLANGCHANGEREQUEST),
  **never** a blind `Alt+Shift` toggle — the file-list screen is already Hebrew, so a toggle flips
  it to English and types `f` (live bug 2026-06-30).

**Two things that make KERMIT actually COMPLETE (it stalled at block 6 before):**
- **Drive the LIVE terminal, not a zombie.** PowerTerm can leave a stale `TERM` window;
  `find_term()` returns the first in z-order, which may be the dead one (it kept driving the
  stale `hwnd` while the fresh login opened a different `hwnd`). Close stale terminals / target
  the newest before driving.
- **Keep PowerTerm FOREGROUND during the transfer and DO NOT screenshot.** Windows throttles a
  backgrounded window's message loop → starves the KERMIT receive → stall at block 6 / 0 B/s.
  The wait loop calls `SetForegroundWindow(hwnd)` every ~4s and takes NO `grab()`/`PrintWindow`
  (those interrupt the receive). Wait for the file size to stabilize (transfer done).

### 3. Convert MU_NK_HAYV → .MBT
The agent's Phoenix/Mimshak desktop tool turns `MU_NK_HAYV` into the standard
`LIFE.MBT`/`COVRLIFE.MBT`/`LIFEHLTH.MBT` set (Mimshak production format). Currently a manual
step on the agent's side; not yet automated.

### 4. Parse .MBT → production (`backend/app/services/phoenix_terminal.py`)
`parse_phoenix_mbt_set(folder)` / `build_phoenix_production_xlsx(folder, out)` reuse
`services/mimshak/mbt.py` to assemble the `.MBT` set into production-schema records
(`company_source="הפניקס"`; `יצרן/סטטוס מוצר/סה"כ פרמיה` signature so `detect_format`→production).
Verified: 80 records with names/IDs/premium/accumulation → ingest → aggregate. See memory
`phoenix_terminal_production`.

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
