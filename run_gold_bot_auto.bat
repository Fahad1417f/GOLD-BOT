@echo off
setlocal
cd /d "%~dp0"
echo GOLD_BOT_AUTO=START
set GOLDBOT_ROOT=%~dp0
set GOLDBOT_MONITOR_LOG=%~dp0v56_monitor.log
set GOLDBOT_REPO=Fahad1417f/GOLD-BOT
set GOLDBOT_STATE_PATH=website_state.json
set GOLDBOT_BRANCH=main
if not defined GITHUB_TOKEN echo WARNING=GITHUB_TOKEN_NOT_SET_STATE_BRIDGE_WILL_NOT_PUBLISH
start "GOLD-BOT SUPERVISOR" cmd /k "python v56_signal_monitor\auto_supervisor.py"
start "GOLD-BOT STATE BRIDGE" cmd /k "python v56_signal_monitor\github_state_bridge.py"
echo SUPERVISOR=STARTED
echo STATE_BRIDGE=STARTED
echo EXECUTION=OFF
echo SAFE_MODE=ON
endlocal