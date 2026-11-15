$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "      CALORIEBOT // NUTRITION & CALORIE TRACKER" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path ".\.venv")) {
    Write-Host "[*] Creating virtual environment with uv..." -ForegroundColor Yellow
    uv venv .venv --python 3.11
    uv pip install --python .venv\Scripts\python.exe -r requirements.txt
}

Write-Host "[*] Launching CalorieBot server and Telegram bot..." -ForegroundColor Green
& ".\.venv\Scripts\python.exe" run.py
