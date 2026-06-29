@echo off
REM ── Nifraim local worker launcher (used by the Scheduled Task) ──
REM Runs the portal automation on this Israeli machine. On every start it FIRST
REM auto-updates the code from git (so the user never has to "git pull"), then
REM launches the worker. Output is appended to worker\worker_console.log so a
REM crash is never invisible (the task runs hidden). No `pause` here — a pause
REM would hang the hidden task. For interactive troubleshooting use worker_debug.bat.

cd /d "%~dp0\.."
set "REPO=%cd%"
set "LOG=%REPO%\worker\worker_console.log"
set "BRANCH=claude/automate-otp-login-fCKdi"

if not exist "%REPO%\backend\venv\Scripts\python.exe" (
  echo [%date% %time%] venv missing - run worker\install_windows.ps1 first >> "%LOG%"
  exit /b 1
)

REM ── Auto-update to the latest code (NON-FATAL: if git/network is unavailable the
REM    worker still starts with whatever code is already on disk). .env, backend\venv
REM    and data\ are gitignored, so reset --hard never touches credentials/downloads.
echo [%date% %time%] checking for code updates on %BRANCH% ... >> "%LOG%"
git -C "%REPO%" fetch origin >> "%LOG%" 2>&1
git -C "%REPO%" checkout %BRANCH% >> "%LOG%" 2>&1
git -C "%REPO%" reset --hard origin/%BRANCH% >> "%LOG%" 2>&1

echo [%date% %time%] starting local worker >> "%LOG%"
"%REPO%\backend\venv\Scripts\python.exe" "%REPO%\backend\local_worker.py" >> "%LOG%" 2>&1
echo [%date% %time%] worker exited code %errorlevel% >> "%LOG%"
