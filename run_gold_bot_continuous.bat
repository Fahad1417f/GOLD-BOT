@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem Use the project venv when present; otherwise use python from PATH.
set "PYTHON_EXE=python"
if exist "%~dp0.venv\Scripts\python.exe" goto use_existing_venv
goto bootstrap_venv

:use_existing_venv
set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
goto environment_ready

:bootstrap_venv
echo ========================================
echo GOLD-BOT PYTHON ENVIRONMENT
echo ========================================
echo Python bootstrap source=%PYTHON_EXE%
"%PYTHON_EXE%" -m venv "%~dp0.venv"
if errorlevel 1 goto venv_failed
set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
echo VENV_CREATED=%PYTHON_EXE%

environment_ready:
set "GOLDBOT_VISION_INTERVAL_SECONDS=15"
set "GOLDBOT_VISION_CANDLE_LIMIT=24"
set "GOLDBOT_REAL_TRADING=OFF"
set "GOLDBOT_DEMO_TRADING=OFF"
set "GOLDBOT_FAST_TRADE=OFF"
set "GOLDBOT_SUPERVISOR_INTERVAL=15"
set "GOLDBOT_STALE_SECONDS=180"
set "GOLDBOT_MAX_RESTARTS=3"

if not exist "%~dp0artifacts\vision" mkdir "%~dp0artifacts\vision"

echo ========================================
echo GOLD-BOT CONTINUOUS MONITOR
echo ========================================
echo PYTHON=%PYTHON_EXE%
echo VISION=ON
echo V56_SUPERVISOR=ON
echo READ_ONLY=YES
echo EXECUTION=OFF
echo.

"%PYTHON_EXE%" -c "import playwright; print('PLAYWRIGHT=AVAILABLE')" >nul 2>&1
if not errorlevel 1 goto playwright_ready

echo PLAYWRIGHT=MISSING
echo Installing project dependencies...
"%PYTHON_EXE%" -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 goto dependency_failed

:playwright_ready
"%PYTHON_EXE%" -c "import playwright; print('PLAYWRIGHT=AVAILABLE')" >nul 2>&1
if errorlevel 1 goto playwright_failed

echo PLAYWRIGHT=AVAILABLE

"%PYTHON_EXE%" -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.executable_path; p.stop(); import os; raise SystemExit(0 if os.path.exists(b) else 1)" >nul 2>&1
if not errorlevel 1 goto runtime_ready

echo CHROMIUM=MISSING
echo Installing Playwright Chromium runtime...
"%PYTHON_EXE%" -m playwright install chromium
if errorlevel 1 goto chromium_failed

:runtime_ready
echo PLAYWRIGHT_RUNTIME=AVAILABLE
echo.

start "GOLD-BOT VISION" cmd /k "cd /d "%~dp0" && set GOLDBOT_VISION_INTERVAL_SECONDS=%GOLDBOT_VISION_INTERVAL_SECONDS% && set GOLDBOT_VISION_CANDLE_LIMIT=%GOLDBOT_VISION_CANDLE_LIMIT% && set GOLDBOT_REAL_TRADING=OFF && set GOLDBOT_DEMO_TRADING=OFF && set GOLDBOT_FAST_TRADE=OFF && "%PYTHON_EXE%" -m kfoo_linked_work.vision_live_capture_v1 --loop --interval %GOLDBOT_VISION_INTERVAL_SECONDS% --output-dir artifacts\vision"

start "GOLD-BOT SUPERVISOR" cmd /k "cd /d "%~dp0" && set GOLDBOT_REAL_TRADING=OFF && set GOLDBOT_DEMO_TRADING=OFF && set GOLDBOT_FAST_TRADE=OFF && set GOLDBOT_SUPERVISOR_INTERVAL=%GOLDBOT_SUPERVISOR_INTERVAL% && set GOLDBOT_STALE_SECONDS=%GOLDBOT_STALE_SECONDS% && set GOLDBOT_MAX_RESTARTS=%GOLDBOT_MAX_RESTARTS% && "%PYTHON_EXE%" v56_signal_monitor\auto_supervisor.py"

echo.
echo CONTINUOUS_MODE=STARTED
echo Execution remains OFF.
exit /b 0

:venv_failed
echo ERROR=VENV_CREATE_FAILED
pause
exit /b 3

:dependency_failed
echo ERROR=DEPENDENCY_INSTALL_FAILED
pause
exit /b 4

:playwright_failed
echo ERROR=PLAYWRIGHT_NOT_INSTALLED_AFTER_PIP
pause
exit /b 5

:chromium_failed
echo ERROR=CHROMIUM_INSTALL_FAILED
pause
exit /b 6
