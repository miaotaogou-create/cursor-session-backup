@echo off
cd /d "%~dp0"
set EXE=%~dp0release\CursorSessionBackup\CursorSessionBackup.exe
if exist "%EXE%" goto run
echo Building portable package...
python "%~dp0build_portable.py"
if errorlevel 1 (
  echo Build failed. Try: pip install -r requirements.txt pyinstaller
  pause
  exit /b 1
)
:run
start "" "%~dp0release\CursorSessionBackup\CursorSessionBackup.exe"
exit /b 0
