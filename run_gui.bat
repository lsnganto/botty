@echo off
:: ============================================================
:: Botty GUI Launcher
:: Double-click this file to open the configuration interface.
:: ============================================================
title Botty Client Launcher

:: Change to project root (same folder as this .bat)
cd /d "%~dp0"

:: Activate conda environment if it exists
where conda >nul 2>&1
if %ERRORLEVEL% == 0 (
    call conda activate sword 2>nul
)

:: Launch the GUI
python src\main.py --gui

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Failed to start GUI. Make sure PyQt6 is installed:
    echo   pip install PyQt6
    echo.
    pause
)
