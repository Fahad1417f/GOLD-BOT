@echo off
setlocal
set "PYTHONUNBUFFERED=1"
if "%GOLDBOT_FAST_POLL_MS%"=="" set "GOLDBOT_FAST_POLL_MS=500"
if "%GOLDBOT_WEBHOOK_URL%"=="" set "GOLDBOT_WEBHOOK_URL=http://127.0.0.1:3000/api/webhooks/tradingview"
python kfoo_linked_work\fast_signal_monitor_v56.py --poll-ms %GOLDBOT_FAST_POLL_MS% --webhook %GOLDBOT_WEBHOOK_URL%
endlocal
