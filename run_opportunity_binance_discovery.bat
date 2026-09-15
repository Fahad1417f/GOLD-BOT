@echo off
setlocal
set "PYTHONUNBUFFERED=1"
python -m kfoo_linked_work.binance_market_discovery --output opportunity_market_discovery.json --limit 20
endlocal
