@echo off
cd /d "%~dp0"
if exist "%~dp0release\CursorSessionBackup.exe" (
  start "" "%~dp0release\CursorSessionBackup.exe"
  exit /b 0
)
where pythonw >nul 2>&1
if %errorlevel%==0 (
  start "" pythonw "%~dp0run_gui.py"
  exit /b 0
)
python "%~dp0run_gui.py"
if errorlevel 1 pause
