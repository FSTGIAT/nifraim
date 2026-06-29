@echo off
REM Nifraim worker — one-click ELEVATE. Double-click this; approve the single UAC
REM prompt. It re-registers the local worker as an elevated Scheduled Task so its
REM keystrokes reach the Phoenix PowerTerm terminal (UIPI). Hands-free afterwards.

REM Self-elevate: if not already admin, relaunch THIS .bat via UAC, then exit.
net session >nul 2>&1
if %errorlevel% NEQ 0 (
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

REM Elevated from here on.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0elevate_worker.ps1"
echo.
echo Done. You can close this window.
pause
