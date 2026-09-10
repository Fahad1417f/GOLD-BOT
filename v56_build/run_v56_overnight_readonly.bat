@echo off
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
if not defined TWELVEDATA_API_KEY if defined TWELVE_DATA_API_KEY set TWELVEDATA_API_KEY=%TWELVE_DATA_API_KEY%
if not defined GOLDBOT_MONITOR_LOG set GOLDBOT_MONITOR_LOG=%~dp0..\v56_monitor.log
if exist "%~dp0..\.venv\Scripts\python.exe" (
  "%~dp0..\.venv\Scripts\python.exe" "%~dp0run_v56_overnight_readonly.py"
) else (
  python "%~dp0run_v56_overnight_readonly.py"
)
endlocal
