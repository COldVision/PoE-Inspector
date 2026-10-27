@echo off
rem Starts the PoE Inspector server (http://127.0.0.1:8765) in this window. Close the window or press Ctrl+C to stop it.
cd /d "%~dp0"
powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue) { exit 1 }"
if errorlevel 1 (
  echo Server is already running on port 8765.
  start "" http://127.0.0.1:8765/
  pause
  exit /b
)
start "" /b cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:8765/"
python run.py
pause
