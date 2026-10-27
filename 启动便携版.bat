@echo off
cd /d "%~dp0"
if exist "%~dp0release\CursorSessionBackup.exe" goto run
echo Building portable exe...
python "%~dp0build_portable.py"
if errorlevel 1 (
  echo Build failed. Try: pip install pyinstaller
  pause
  exit /b 1
)
:run
start "" "%~dp0release\CursorSessionBackup.exe"
exit /b 0
