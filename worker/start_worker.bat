@echo off
REM ── Nifraim local worker launcher (Windows) ──
REM Runs the portal automation on this Israeli machine. Started automatically at
REM logon by the Scheduled Task that install_windows.ps1 registers; you can also
REM double-click it to run in a visible window.

cd /d "%~dp0\.."
set "REPO=%cd%"

if not exist "%REPO%\backend\venv\Scripts\python.exe" (
  echo [Nifraim] Virtual env not found. Run worker\install_windows.ps1 first.
  pause
  exit /b 1
)

echo [Nifraim] Starting local worker... (keep this window open; minimize it)
"%REPO%\backend\venv\Scripts\python.exe" "%REPO%\backend\local_worker.py"
