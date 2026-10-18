@echo off
REM Rebase All to Main - Windows Launcher
REM
REM This batch file launches the Python script for Windows users.
REM Place this next to rebase_all_to_main.py and config.json
REM
REM Usage:
REM   rebase_all_to_main.bat              # Run with default config.json
REM   rebase_all_to_main.bat --list       # List configured projects
REM   rebase_all_to_main.bat --dry-run    # Show what would be done
REM   rebase_all_to_main.bat -p ims-ui    # Process only specific project(s)

setlocal enabledelayedexpansion

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    exit /b 1
)

REM Run the Python script with all arguments passed through
cd /d "%SCRIPT_DIR%"
python "%~dp0rebase_all_to_main.py" %*

REM Preserve the exit code
exit /b %errorlevel%
