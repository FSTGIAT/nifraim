@echo off
REM ── Nifraim worker — VISIBLE troubleshooting launcher ──
REM Double-click this to run the worker in a window you can read. It prints all
REM output AND keeps the window open on exit so you can see any error/traceback.

cd /d "%~dp0\.."
set "REPO=%cd%"

if not exist "%REPO%\backend\venv\Scripts\python.exe" (
  echo [Nifraim] venv missing. Run worker\install_windows.ps1 first.
  pause & exit /b 1
)

echo [Nifraim] Running worker in DEBUG mode. Ctrl+C to stop.
echo [Nifraim] (also logged to worker\worker_console.log and worker.log)
echo.
"%REPO%\backend\venv\Scripts\python.exe" "%REPO%\backend\local_worker.py"
echo.
echo [Nifraim] Worker exited with code %errorlevel%. Read the lines above for the cause.
pause
