@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "PYTHON_EXE=python"
if exist "%~dp0.venv\Scripts\python.exe" set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
set "GOLDBOT_VISION_INTERVAL_SECONDS=15"
set "GOLDBOT_VISION_CANDLE_LIMIT=24"
set "GOLDBOT_VISION_CYCLE_TIMEOUT=12"
set "GOLDBOT_VISION_TRACE=ON"
set "GOLDBOT_REAL_TRADING=OFF"
set "GOLDBOT_DEMO_TRADING=OFF"
set "GOLDBOT_FAST_TRADE=OFF"
set "GOLDBOT_VISION_OUTPUT_DIR=artifacts\vision"
if not exist "%~dp0artifacts\vision" mkdir "%~dp0artifacts\vision"
if not exist "%~dp0.venv\Scripts\python.exe" "%PYTHON_EXE%" -m venv "%~dp0.venv"
set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
"%PYTHON_EXE%" -c "import playwright" >nul 2>&1
if errorlevel 1 "%PYTHON_EXE%" -m pip install -r "%~dp0requirements.txt"
"%PYTHON_EXE%" -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.executable_path; p.stop(); import os; raise SystemExit(0 if os.path.exists(b) else 1)" >nul 2>&1
if errorlevel 1 "%PYTHON_EXE%" -m playwright install chromium
start "GOLD-BOT VISION V5" cmd /k "cd /d "%~dp0" && set GOLDBOT_VISION_INTERVAL_SECONDS=15 && set GOLDBOT_VISION_CANDLE_LIMIT=24 && set GOLDBOT_VISION_CYCLE_TIMEOUT=12 && set GOLDBOT_VISION_TRACE=ON && set GOLDBOT_VISION_OUTPUT_DIR=artifacts\vision && set GOLDBOT_REAL_TRADING=OFF && set GOLDBOT_DEMO_TRADING=OFF && set GOLDBOT_FAST_TRADE=OFF && "%PYTHON_EXE%" -u -m kfoo_linked_work.vision_cycle_watchdog_v2"
echo VISION_WATCHDOG=v2
echo VISION_CAPTURE=v5
echo EXECUTION=OFF
exit /b 0
