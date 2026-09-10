@echo off
setlocal
cd /d "%~dp0"
call "%~dp0run_gold_bot_auto.bat"
start "GOLD-BOT WEB" http://127.0.0.1:3000/
endlocal
