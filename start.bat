@echo off
title FocusForge Launcher
color 0B

echo.
echo ===============================================
echo   ⚡ FocusForge - Productivity Made Simple
echo ===============================================
echo.

REM Navigate to script directory
cd /d "%~dp0"

REM Check if UV is installed
where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] UV not found. Please install UV first:
    echo     https://astral.sh/uv/install
    echo.
    pause
    exit /b 1
)

echo [+] Syncing dependencies...
uv sync --quiet

echo [+] Starting FocusForge...
echo.
echo Tips:
echo   - Install browser extension from /extension/chrome
echo   - API available at http://localhost:8765
echo   - Press Ctrl+C to stop
echo.

uv run python -m focusforge.main

pause
