@echo off
setlocal
cd /d "%~dp0"
echo GOLD_BOT_CONNECTED=START
if not defined GITHUB_TOKEN (
  echo ERROR=GITHUB_TOKEN_NOT_SET
  echo Set a GitHub fine-grained token with Contents: Read and write, then run again.
  exit /b 2
)
if not exist "v56_build\run_v56_overnight_readonly.bat" (
  echo ERROR=V56_BUILD_NOT_FOUND
  echo Place this repository root beside your existing v56_build folder, or copy this bridge into the V56 project.
  exit /b 3
)
set GOLDBOT_MONITOR_LOG=%~dp0v56_monitor.log
set GOLDBOT_REPO=Fahad1417f/GOLD-BOT
set GOLDBOT_STATE_PATH=website_state.json
set GOLDBOT_BRANCH=main
start "GOLD-BOT STATE BRIDGE" cmd /k "python v56_signal_monitor\github_state_bridge.py"
start "GOLD-BOT V56 MONITOR" cmd /k "cd /d %~dp0v56_build && run_v56_overnight_readonly.bat > ..\v56_monitor.log 2>&1"
echo CONNECTED_MODE=READY
echo STATE_CHANNEL=https://raw.githubusercontent.com/Fahad1417f/GOLD-BOT/main/website_state.json
echo EXECUTION=OFF
endlocal
