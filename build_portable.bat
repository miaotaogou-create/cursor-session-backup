@echo off
cd /d "%~dp0"
python "%~dp0build_portable.py"
if errorlevel 1 exit /b 1
exit /b 0
