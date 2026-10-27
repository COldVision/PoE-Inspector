@echo off
rem Rebuilds "PoE Inspector.exe" (a small launcher: starts the server and opens the app window) from launcher.pyw.
rem The exe looks for run.py next to itself, so keep it in this folder. Needs PyInstaller (pip package, asked before installing).
cd /d "%~dp0"
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
  echo PyInstaller is not installed.
  choice /m "Install it now with pip (downloads about 3 MB)"
  if errorlevel 2 exit /b 1
  python -m pip install pyinstaller || (pause & exit /b 1)
)
taskkill /f /im "PoE Inspector.exe" >nul 2>nul
python -m PyInstaller --noconfirm --clean --onefile --noconsole --name "PoE Inspector" --icon "%~dp0web\app.ico" --distpath "%~dp0." --workpath "%~dp0cache\pyi" --specpath "%~dp0cache\pyi" "%~dp0launcher.pyw" || (pause & exit /b 1)
echo.
echo Built: %~dp0PoE Inspector.exe
pause
