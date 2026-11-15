@echo off
title CalorieBot Launcher
cd /d "%~dp0"

echo ========================================================
echo       CALORIEBOT // NUTRITION & CALORIE TRACKER
echo ========================================================
echo.

if not exist .venv (
    echo [!] Virtual environment not found. Creating with uv...
    uv venv .venv --python 3.11
    uv pip install --python .venv\Scripts\python.exe -r requirements.txt
)

echo [*] Starting CalorieBot Server and Telegram Bot...
.venv\Scripts\python.exe run.py
pause
