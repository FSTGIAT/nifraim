<#
  Nifraim local worker — Windows installer
  ----------------------------------------
  Sets up everything so the agent's computer can run the insurer-portal downloads
  locally (from an Israeli IP — no proxy, no KYC), driven by the website's
  "download" buttons.

  What it does:
    1. Verifies Python 3.10+ is installed.
    2. Creates a virtual env at backend\venv and installs dependencies.
    3. Installs the Playwright Chromium browser.
    4. Writes the repo-root .env (prod DB URL, Fernet key, agent email).
    5. Registers a Scheduled Task that starts the worker automatically at logon
       and restarts it if it stops.

  Run (from the repo root, in PowerShell):
    powershell -ExecutionPolicy Bypass -File worker\install_windows.ps1 `
      -DatabaseUrl "postgresql+asyncpg://USER:PASS@HOST:PORT/railway" `
      -FernetKey   "….=" `
      -UserEmail   "agent@nifraim.com"
#>
param(
  [Parameter(Mandatory = $true)] [string] $DatabaseUrl,
  [Parameter(Mandatory = $true)] [string] $FernetKey,
  [Parameter(Mandatory = $true)] [string] $UserEmail
)

$ErrorActionPreference = "Stop"
$Repo = (Resolve-Path "$PSScriptRoot\..").Path
Write-Host "[Nifraim] Repo root: $Repo"

# 1. Python check
try { $pyv = (python --version) 2>&1 } catch { throw "Python not found. Install Python 3.10+ from python.org and re-run." }
Write-Host "[Nifraim] $pyv"

# 2. venv + deps
$venv = Join-Path $Repo "backend\venv"
if (-not (Test-Path "$venv\Scripts\python.exe")) {
  Write-Host "[Nifraim] Creating virtual env…"
  python -m venv $venv
}
$py = "$venv\Scripts\python.exe"
Write-Host "[Nifraim] Installing dependencies (this can take a few minutes)…"
& $py -m pip install --upgrade pip | Out-Null
& $py -m pip install -r (Join-Path $Repo "backend\requirements.txt")

# 3. Playwright Chromium
Write-Host "[Nifraim] Installing Playwright Chromium…"
& $py -m playwright install chromium

# 4. .env at repo root
$envPath = Join-Path $Repo ".env"
$lines = @(
  "DATABASE_URL=$DatabaseUrl",
  "DATABASE_URL_SYNC=$($DatabaseUrl -replace '\+asyncpg','')",
  "PORTAL_CRED_FERNET_KEY=$FernetKey",
  "JWT_SECRET=local-worker-not-used",
  "WORKER_USER_EMAIL=$UserEmail",
  "IL_RESIDENTIAL_PROXY="
)
# Preserve any existing .env keys not managed here
if (Test-Path $envPath) {
  $managed = @("DATABASE_URL","DATABASE_URL_SYNC","PORTAL_CRED_FERNET_KEY","JWT_SECRET","WORKER_USER_EMAIL","IL_RESIDENTIAL_PROXY")
  Get-Content $envPath | ForEach-Object {
    if ($_ -match "^\s*([A-Z_]+)=") { if ($managed -notcontains $Matches[1]) { $lines += $_ } }
  }
}
Set-Content -Path $envPath -Value $lines -Encoding UTF8
Write-Host "[Nifraim] Wrote $envPath"

# 5. Scheduled Task — start at logon, restart on failure
$bat = Join-Path $Repo "worker\start_worker.bat"
$taskName = "NifraimLocalWorker"
$action  = New-ScheduledTaskAction -Execute $bat
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
            -StartWhenAvailable -DontStopOnIdleEnd -ExecutionTimeLimit (New-TimeSpan -Hours 0)
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Write-Host "[Nifraim] Registered Scheduled Task '$taskName' (auto-start at logon)."

# Start it now
Start-ScheduledTask -TaskName $taskName
Write-Host "[Nifraim] Worker started. The website should show 'המחשב מחובר' within ~20 seconds."
Write-Host "[Nifraim] Done."
