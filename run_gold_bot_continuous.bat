@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem Select the Python executable without parenthesized-block expansion pitfalls.
if exist "%~dp0.venv\Scripts\python.exe" goto HAVE_VENV
if defined PYTHON_EXE goto HAVE_BOOTSTRAP_PYTHON
set "PYTHON_EXE=python"
:HAVE_BOOTSTRAP_PYTHON

echo ========================================
echo GOLD-BOT PYTHON ENVIRONMENT
echo ========================================
echo Python bootstrap source=%PYTHON_EXE%
"%PYTHON_EXE%" -m venv "%~dp0.venv"
if errorlevel 1 goto VENV_CREATE_FAILED
set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
echo VENV_CREATED=%PYTHON_EXE%
goto ENV_READY

:VENV_CREATE_FAILED
echo ERROR=VENV_CREATE_FAILED
echo Python bootstrap source was: %PYTHON_EXE%
pause
exit /b 3

:HAVE_VENV
set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
:ENV_READY
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
if errorlevel 1 goto INSTALL_DEPS

goto CHECK_CHROMIUM

:INSTALL_DEPS
echo PLAYWRIGHT=MISSING
echo Installing project dependencies...
"%PYTHON_EXE%" -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 goto DEPENDENCY_INSTALL_FAILED
"%PYTHON_EXE%" -c "import playwright; print('PLAYWRIGHT=AVAILABLE')" >nul 2>&1
if errorlevel 1 goto PLAYWRIGHT_STILL_MISSING

goto CHECK_CHROMIUM

:DEPENDENCY_INSTALL_FAILED
echo ERROR=DEPENDENCY_INSTALL_FAILED
pause
exit /b 4

:PLAYWRIGHT_STILL_MISSING
echo ERROR=PLAYWRIGHT_NOT_INSTALLED_AFTER_PIP
pause
exit /b 5

:CHECK_CHROMIUM
"%PYTHON_EXE%" -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.executable_path; p.stop(); import os; raise SystemExit(0 if os.path.exists(b) else 1)" >nul 2>&1
if errorlevel 1 goto INSTALL_CHROMIUM

goto START_MONITORS

:INSTALL_CHROMIUM
echo CHROMIUM=MISSING
echo Installing Playwright Chromium runtime...
"%PYTHON_EXE%" -m playwright install chromium
if errorlevel 1 goto CHROMIUM_INSTALL_FAILED

goto START_MONITORS

:CHROMIUM_INSTALL_FAILED
echo ERROR=CHROMIUM_INSTALL_FAILED
pause
exit /b 6

:START_MONITORS
echo PLAYWRIGHT=AVAILABLE
echo PLAYWRIGHT_RUNTIME=AVAILABLE
echo.

start "GOLD-BOT VISION" cmd /k "cd /d "%~dp0" && set GOLDBOT_VISION_INTERVAL_SECONDS=%GOLDBOT_VISION_INTERVAL_SECONDS% && set GOLDBOT_VISION_CANDLE_LIMIT=%GOLDBOT_VISION_CANDLE_LIMIT% && set GOLDBOT_REAL_TRADING=OFF && set GOLDBOT_DEMO_TRADING=OFF && set GOLDBOT_FAST_TRADE=OFF && "%PYTHON_EXE%" -m kfoo_linked_work.vision_live_capture_v1 --loop --interval %GOLDBOT_VISION_INTERVAL_SECONDS% --output-dir artifacts\vision"

start "GOLD-BOT SUPERVISOR" cmd /k "cd /d "%~dp0" && set GOLDBOT_REAL_TRADING=OFF && set GOLDBOT_DEMO_TRADING=OFF && set GOLDBOT_FAST_TRADE=OFF && set GOLDBOT_SUPERVISOR_INTERVAL=%GOLDBOT_SUPERVISOR_INTERVAL% && set GOLDBOT_STALE_SECONDS=%GOLDBOT_STALE_SECONDS% && set GOLDBOT_MAX_RESTARTS=%GOLDBOT_MAX_RESTARTS% && "%PYTHON_EXE%" v56_signal_monitor\auto_supervisor.py"

echo.
echo CONTINUOUS_MODE=STARTED
echo Execution remains OFF.
endlocal
