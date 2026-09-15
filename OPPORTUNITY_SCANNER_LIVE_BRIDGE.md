# Opportunity Scanner V2 — Live Multi-Symbol Bridge

The bridge watches a JSON snapshot from the upstream KFOO/market collector.
It does not scrape TradingView and does not place exchange orders.

Expected file:
GOLDBOT_OPPORTUNITY_SNAPSHOT=opportunity_candidates.json

Run once:
python -m kfoo_linked_work.opportunity_scanner_live_bridge --once

Continuous:
python -m kfoo_linked_work.opportunity_scanner_live_bridge --poll-ms 500

The snapshot can contain multiple perpetual symbols such as BTCUSDT.P,
ETHUSDT.P, SOLUSDT.P and SUIUSDT.P. The scanner ranks them and emits at most
one SELECTED opportunity. Telegram is only called for SELECTED.

Execution remains OFF.
