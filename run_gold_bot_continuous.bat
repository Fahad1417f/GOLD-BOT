@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=%PYTHON_EXE%"
if not defined PYTHON_EXE set "PYTHON_EXE=python"
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
echo VISION=ON
echo V56_SUPERVISOR=ON
echo READ_ONLY=YES
echo EXECUTION=OFF
echo.

start "GOLD-BOT VISION" cmd /k "cd /d "%~dp0" && set GOLDBOT_VISION_INTERVAL_SECONDS=%GOLDBOT_VISION_INTERVAL_SECONDS% && set GOLDBOT_VISION_CANDLE_LIMIT=%GOLDBOT_VISION_CANDLE_LIMIT% && set GOLDBOT_REAL_TRADING=OFF && set GOLDBOT_DEMO_TRADING=OFF && set GOLDBOT_FAST_TRADE=OFF && "%PYTHON_EXE%" -m kfoo_linked_work.vision_live_capture_v1 --loop --interval %GOLDBOT_VISION_INTERVAL_SECONDS% --output-dir artifacts\vision"

start "GOLD-BOT SUPERVISOR" cmd /k "cd /d "%~dp0" && set GOLDBOT_REAL_TRADING=OFF && set GOLDBOT_DEMO_TRADING=OFF && set GOLDBOT_FAST_TRADE=OFF && set GOLDBOT_SUPERVISOR_INTERVAL=%GOLDBOT_SUPERVISOR_INTERVAL% && set GOLDBOT_STALE_SECONDS=%GOLDBOT_STALE_SECONDS% && set GOLDBOT_MAX_RESTARTS=%GOLDBOT_MAX_RESTARTS% && "%PYTHON_EXE%" v56_signal_monitor\auto_supervisor.py"

echo.
echo CONTINUOUS_MODE=STARTED
echo Close either monitor window to stop that component.
echo Execution remains OFF.
endlocal
