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

if not exist "%~dp0artifacts\vision" mkdir "%~dp0artifacts\vision"

echo ========================================
echo GOLD-BOT CONTINUOUS VISION MONITOR
 echo ========================================
echo MODE=READ_ONLY
echo EXECUTION=OFF
echo INTERVAL=%GOLDBOT_VISION_INTERVAL_SECONDS%s
echo CANDLE_LIMIT=%GOLDBOT_VISION_CANDLE_LIMIT%
echo STATE=%~dp0artifacts\vision\live_state.json
echo.
echo Start TradingView with remote debugging on port 9222 before continuing.
echo.

"%PYTHON_EXE%" -m kfoo_linked_work.vision_live_capture_v1 --loop --interval %GOLDBOT_VISION_INTERVAL_SECONDS% --output-dir artifacts\vision

set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo VISION_MONITOR_EXIT=%EXIT_CODE%
endlocal & exit /b %EXIT_CODE%
