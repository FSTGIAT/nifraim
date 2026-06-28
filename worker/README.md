# Nifraim Local Worker (Windows)

Runs the insurer-portal downloads on the agent's **own Israeli computer** instead
of on Railway's foreign server. This avoids the geo-block and the Bright Data
no-KYC POST block entirely — the agent's home/office IP reaches every insurer
directly.

The website stays the brain: the agent clicks **"הורדה אוטומטית מכל החברות"**
(or a single company), which *enqueues* the job. This worker, running in the
background, picks it up and executes it locally. OTPs still arrive hands-free via
the phone-forward app. The site shows a green **"המחשב מחובר"** chip when the
worker is online.

## How it works

```
Web UI button ──► Railway API (WORKER_MODE=true → just enqueues, status=pending)
                       │
                       ▼  (prod DB)
        ┌──────────────────────────────────┐
        │  local_worker.py on agent's PC    │  ← polls DB, claims pending jobs
        │  • run_batch / run_automation     │  ← Playwright, direct Israeli IP
        │  • heartbeat → worker_heartbeats  │  ← drives the online/offline chip
        └──────────────────────────────────┘
                       │
   phone SMS OTP ──► prod /phone-forward webhook ──► otp_inbox ──► consumed here
```

## One-time setup (per agent machine)

1. Install **Python 3.10+** from <https://python.org> (check "Add to PATH").
2. Copy/clone this repo to the machine (e.g. `C:\nifraim`).
3. Open **PowerShell** in the repo root and run:

   ```powershell
   powershell -ExecutionPolicy Bypass -File worker\install_windows.ps1 `
     -DatabaseUrl "postgresql+asyncpg://USER:PASS@HOST:PORT/railway" `
     -FernetKey   "<PORTAL_CRED_FERNET_KEY>" `
     -UserEmail   "agent@nifraim.com"
   ```

   It creates the venv, installs deps + Chromium, writes `.env`, and registers a
   **Scheduled Task** that auto-starts the worker at every logon (and restarts it
   if it stops).

4. On Railway, set **`WORKER_MODE=true`** on the `nifraim` service (so Railway
   enqueues jobs instead of trying to run them itself).

## Day-to-day (the agent)

- Keep the **computer on** and the **phone forwarder app running**.
- Use the website's download buttons as usual. The green chip confirms the
  computer is connected; if it's red, the worker/computer is off.

## Manual control

- Run in a visible window: double-click `worker\start_worker.bat`.
- Stop/disable: Task Scheduler → `NifraimLocalWorker` → End / Disable.
- Logs print to the worker console window.

## Notes / tuning (env vars, optional)

- `WORKER_USER_EMAIL` — which agent this worker serves (set by the installer).
- `WORKER_POLL_SECONDS` — job poll interval (default 5).
- The worker forces `IL_RESIDENTIAL_PROXY=""` (direct connection) — no proxy is
  used or needed locally.
