# GOLD BOT Telegram Device Agent

Local Telegram gateway with an allowlist only.

Allowed: /status /health /test /log /stop

No arbitrary CMD/PowerShell/shell execution.
No Binance execution. Trading remains OFF.

Install:
python -m pip install requests

Set in Windows CMD:
set GOLDBOT_TELEGRAM_BOT_TOKEN=YOUR_TOKEN
set GOLDBOT_TELEGRAM_CHAT_ID=YOUR_CHAT_ID
set GOLDBOT_PROJECT_DIR=C:\Users\...\GOLD_BOT_...

Run:
python telegram_device_agent.py

Test:
python test_telegram_device_agent.py

Never commit Bot Tokens, API keys, API secrets, or .env files.