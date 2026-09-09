@echo off
setlocal
cd /d "%~dp0"
start "GOLD-BOT SITE" cmd /c "python site_server.py"
timeout /t 2 >nul
start "GOLD-BOT MONITOR" cmd /c "cd v56_build && run_v56_overnight_readonly.bat"
timeout /t 1 >nul
start "GOLD-BOT WEB" http://127.0.0.1:3000/
echo SITE_SERVER=STARTED
echo SITE_URL=http://127.0.0.1:3000
endlocal
