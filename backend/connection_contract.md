# Backend Connection Contract

Status: WRITE_TEST PASS / READ_BACK PASS

Flow: Website -> authenticated Backend -> local Agent -> TradingView observation.

Protected endpoints require X-GB-Token.
Allowed commands only: status, health, test, log, stop.
Execution default: OFF.
Production Binance: BLOCKED.
2m timeframe: excluded.
