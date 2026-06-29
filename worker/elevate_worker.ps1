<#
  Nifraim local worker — ELEVATE
  ------------------------------
  The worker drives the Phoenix PowerTerm green-screen terminal with synthetic
  keystrokes (SendInput). Windows UIPI silently DROPS keystrokes sent from a
  non-elevated process to a higher-integrity window (PowerTerm), so the export
  step ("13" -> Enter x5 -> Down -> Hebrew 'כ' -> KERMIT) does nothing when the
  worker runs at medium integrity.

  The original installer fell back to a non-admin Startup .vbs (Register-
  ScheduledTask hit "Access is denied"). This script — run ONCE as admin —
  replaces that with a Scheduled Task at **RunLevel Highest** in the user's
  interactive session, so every future run (incl. the "הורדה אוטומטית" button)
  is elevated and the keystrokes reach PowerTerm. Hands-free afterwards.

  It is invoked elevated by elevate_worker.bat (which triggers the single UAC).
#>
$ErrorActionPreference = "Stop"

$Bundle  = Join-Path $env:LOCALAPPDATA "Nifraim"
$py      = Join-Path $Bundle "venv\Scripts\python.exe"
$script  = Join-Path $Bundle "backend\local_worker.py"
$workdir = Join-Path $Bundle "backend"
$taskName = "NifraimLocalWorker"

if (-not (Test-Path $py))     { throw "worker python not found at $py — is the worker installed?" }
if (-not (Test-Path $script)) { throw "local_worker.py not found at $script" }
Write-Host "[Nifraim] Elevating worker: $py $script"

# 1. Stop any running NON-elevated worker (python running local_worker.py).
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -like "*local_worker.py*" } |
  ForEach-Object {
    Write-Host "  stopping running worker pid $($_.ProcessId)"
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
  }

# 2. Remove the non-elevated Startup .vbs so it can't relaunch a medium-integrity
#    worker at the next logon (which would race the elevated task).
$vbs = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup\NifraimWorker.vbs"
if (Test-Path $vbs) { Remove-Item $vbs -Force; Write-Host "  removed non-elevated Startup launcher" }

# 3. Register the ELEVATED task. Interactive logon type + Highest run level =
#    runs in the user's desktop session (session 1, can drive the GUI) AND
#    elevated (keystrokes pass UIPI into PowerTerm). AtLogOn so it auto-starts.
$action    = New-ScheduledTaskAction -Execute $py -Argument "`"$script`"" -WorkingDirectory $workdir
$trigger   = New-ScheduledTaskTrigger -AtLogOn
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
             -LogonType Interactive -RunLevel Highest
$settings  = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
             -StartWhenAvailable -DontStopOnIdleEnd -ExecutionTimeLimit (New-TimeSpan -Hours 0)
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
  -Principal $principal -Settings $settings -Force | Out-Null
Write-Host "[Nifraim] Registered '$taskName' at RunLevel Highest (interactive)."

# 4. Start it now — elevated, in this interactive session.
Start-ScheduledTask -TaskName $taskName
Write-Host "[Nifraim] Elevated worker started. The website chip should show 'המחשב מחובר'"
Write-Host "[Nifraim] within ~20s, and PowerTerm keystrokes will now land."
