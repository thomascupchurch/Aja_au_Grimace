@echo off
REM Wrapper to run sync_github_to_onedrive.py with the correct Python environment
REM Usage: Double-click or schedule this .bat file in Task Scheduler

set PYTHON_EXE="%~dp0.venv\Scripts\python.exe"
set SCRIPT_PATH="%~dp0sync_github_to_onedrive.py"

REM Run the sync script
%PYTHON_EXE% %SCRIPT_PATH%

pause
