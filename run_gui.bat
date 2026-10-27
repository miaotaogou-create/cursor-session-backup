@echo off
cd /d "%~dp0"
REM 开发用：pythonw 无黑框；若已有便携 exe 则优先启动 exe
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
