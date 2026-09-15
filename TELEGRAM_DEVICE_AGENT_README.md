# GOLD BOT Telegram Device Agent

Local Telegram gateway with an allowlist only.

Allowed: /status /health /test /log /opportunity /stop

Opportunity Scanner alerts are sent automatically by the local webhook only when a candidate is classified as TRADEABLE.

Required environment variables:
python -m pip install requests
set GOLDBOT_TELEGRAM_BOT_TOKEN=YOUR_TOKEN
set GOLDBOT_TELEGRAM_CHAT_ID=YOUR_CHAT_ID
set GOLDBOT_TELEGRAM_ALERTS=1
set GOLDBOT_PROJECT_DIR=C:\\Users\\...\\GOLD_BOT_...

Run:
python telegram_device_agent.py

Test:
python test_telegram_device_agent.py

The notifier is fail-closed: missing credentials, disabled alerts, missing Reward/Risk, or high Risk Ratio do not send an opportunity alert.

Never commit Bot Tokens, API keys, API secrets, or .env files.
Trading execution remains OFF.
