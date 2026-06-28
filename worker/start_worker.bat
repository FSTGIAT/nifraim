@echo off
REM ── Nifraim local worker launcher (used by the Scheduled Task) ──
REM Runs the portal automation on this Israeli machine. Output is appended to
REM worker\worker_console.log so a crash is never invisible (the task runs hidden).
REM No `pause` here — a pause would hang the hidden task. For interactive
REM troubleshooting use worker_debug.bat instead.

cd /d "%~dp0\.."
set "REPO=%cd%"
set "LOG=%REPO%\worker\worker_console.log"

if not exist "%REPO%\backend\venv\Scripts\python.exe" (
  echo [%date% %time%] venv missing - run worker\install_windows.ps1 first >> "%LOG%"
  exit /b 1
)

echo [%date% %time%] starting local worker >> "%LOG%"
"%REPO%\backend\venv\Scripts\python.exe" "%REPO%\backend\local_worker.py" >> "%LOG%" 2>&1
echo [%date% %time%] worker exited code %errorlevel% >> "%LOG%"
