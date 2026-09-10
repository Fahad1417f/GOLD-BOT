@echo off
setlocal
cd /d "%~dp0"
echo GOLD_BOT_AUTO=START
set GOLDBOT_ROOT=%~dp0
set GOLDBOT_MONITOR_LOG=%~dp0v56_monitor.log
set GOLDBOT_REPO=Fahad1417f/GOLD-BOT
set GOLDBOT_STATE_PATH=website_state.json
set GOLDBOT_BRANCH=main
if exist "%~dp0.venv\Scripts\python.exe" (
  set "PYTHON=%~dp0.venv\Scripts\python.exe"
) else if exist "%~dp0..\GOLD-BOT_APPROVED_WINDOWS\.venv\Scripts\python.exe" (
  set "PYTHON=%~dp0..\GOLD-BOT_APPROVED_WINDOWS\.venv\Scripts\python.exe"
) else (
  set "PYTHON=python"
)
echo PYTHON=%PYTHON%
"%PYTHON%" -c "import sys; print('PYTHON_OK='+sys.executable)" || exit /b 10
if exist "%~dp0site_server.py" start "GOLD-BOT SITE" cmd /c ""%PYTHON%" site_server.py"
if not defined GITHUB_TOKEN echo WARNING=GITHUB_TOKEN_NOT_SET_STATE_BRIDGE_CANNOT_PUBLISH
start "GOLD-BOT SUPERVISOR" cmd /k ""%PYTHON%" v56_signal_monitor\auto_supervisor.py"
start "GOLD-BOT STATE BRIDGE" cmd /k ""%PYTHON%" v56_signal_monitor\github_state_bridge.py"
echo SUPERVISOR=STARTED
echo STATE_BRIDGE=STARTED
echo SITE_SERVER=STARTED_IF_PRESENT
echo EXECUTION=OFF
echo SAFE_MODE=ON
endlocal
