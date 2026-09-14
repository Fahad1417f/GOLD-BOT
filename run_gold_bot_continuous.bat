@echo off
setlocal
cd /d "%~dp0"

rem Prefer the project's local virtual environment; otherwise honor a caller-supplied
rem PYTHON_EXE, then fall back to python on PATH.
if exist "%~dp0.venv\Scripts\python.exe" (
  set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
) else if not defined PYTHON_EXE (
  set "PYTHON_EXE=python"
)

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

rem Fail early with the actual interpreter selected above instead of allowing
rem the monitor to loop forever with PLAYWRIGHT_NOT_INSTALLED.
"%PYTHON_EXE%" -c "import playwright; print('PLAYWRIGHT=AVAILABLE')" >nul 2>&1
if errorlevel 1 (
  echo ERROR=PLAYWRIGHT_NOT_INSTALLED
  echo Python interpreter selected: %PYTHON_EXE%
  echo Install the project dependencies with: "%PYTHON_EXE%" -m pip install -r requirements.txt
  echo If Chromium is not installed yet, run: "%PYTHON_EXE%" -m playwright install chromium
  echo Continuous monitoring NOT started.
  pause
  exit /b 4
)

echo PLAYWRIGHT=AVAILABLE
echo.

start "GOLD-BOT VISION" cmd /k "cd /d "%~dp0" && set GOLDBOT_VISION_INTERVAL_SECONDS=%GOLDBOT_VISION_INTERVAL_SECONDS% && set GOLDBOT_VISION_CANDLE_LIMIT=%GOLDBOT_VISION_CANDLE_LIMIT% && set GOLDBOT_REAL_TRADING=OFF && set GOLDBOT_DEMO_TRADING=OFF && set GOLDBOT_FAST_TRADE=OFF && "%PYTHON_EXE%" -m kfoo_linked_work.vision_live_capture_v1 --loop --interval %GOLDBOT_VISION_INTERVAL_SECONDS% --output-dir artifacts\vision"

start "GOLD-BOT SUPERVISOR" cmd /k "cd /d "%~dp0" && set GOLDBOT_REAL_TRADING=OFF && set GOLDBOT_DEMO_TRADING=OFF && set GOLDBOT_FAST_TRADE=OFF && set GOLDBOT_SUPERVISOR_INTERVAL=%GOLDBOT_SUPERVISOR_INTERVAL% && set GOLDBOT_STALE_SECONDS=%GOLDBOT_STALE_SECONDS% && set GOLDBOT_MAX_RESTARTS=%GOLDBOT_MAX_RESTARTS% && "%PYTHON_EXE%" v56_signal_monitor\auto_supervisor.py"

echo.
echo CONTINUOUS_MODE=STARTED
echo Execution remains OFF.
endlocal
