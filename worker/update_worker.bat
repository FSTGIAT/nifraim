@echo off
REM ── Nifraim worker — one-click UPDATE + RESTART ──
REM Double-click this file to pull the latest code and restart the worker.
REM No git knowledge needed: restarting the Scheduled Task re-runs start_worker.bat,
REM which auto-downloads the latest code before launching.
title Nifraim - Update Worker

echo ================================================
echo    Updating the Nifraim worker to latest code
echo ================================================
echo.
echo Stopping the worker...
schtasks /End /TN "NifraimLocalWorker" >nul 2>&1
timeout /t 2 /nobreak >nul

echo Starting the worker (it auto-downloads the latest code)...
schtasks /Run /TN "NifraimLocalWorker" >nul 2>&1
if errorlevel 1 (
  echo.
  echo Could not start via the Scheduled Task. Launching directly instead...
  start "" "%~dp0start_worker.bat"
)

echo.
echo Done. The worker is updating and restarting.
echo Open the website - the status chip should show "מחובר" within ~30 seconds.
echo You can close this window now.
echo.
pause
