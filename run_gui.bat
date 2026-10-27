@echo off
cd /d "%~dp0"
python "%~dp0run_gui.py"
if errorlevel 1 pause
