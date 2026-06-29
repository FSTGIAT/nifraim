@echo off
REM ── Nifraim local worker launcher ──
REM Runs the portal automation on this Israeli machine. Output is appended to
REM worker\worker_console.log so a crash is never invisible. No `pause` (would hang
REM a hidden launch). For interactive troubleshooting use worker_debug.bat.
REM
REM UPDATES: the worker self-updates by DOWNLOADING the code bundle from the server
REM (the "עדכן עובד" button → local_worker.py re-downloads /worker/bundle + re-execs).
REM No git here — the worker is a downloaded bundle, not a git checkout.

cd /d "%~dp0\.."
set "REPO=%cd%"
set "LOG=%REPO%\worker\worker_console.log"

set "PY=%REPO%\venv\Scripts\python.exe"
if not exist "%PY%" set "PY=%REPO%\backend\venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [%date% %time%] venv missing - run worker\install_windows.ps1 first >> "%LOG%"
  exit /b 1
)

echo [%date% %time%] starting local worker >> "%LOG%"
"%PY%" "%REPO%\backend\local_worker.py" >> "%LOG%" 2>&1
echo [%date% %time%] worker exited code %errorlevel% >> "%LOG%"
