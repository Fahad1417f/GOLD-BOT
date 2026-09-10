# GOLD BOT — KFOO + Playwright Chart Reader + V56 Signal Roles

- Gravity: 4H + 1H only.
- Leader: 15M.
- Entry: 5M + 3M.
- 2M: excluded.

## Playwright chart reader

The chart layer now attaches to an existing TradingView Chromium session through Playwright/CDP. It reads page metadata and visible chart text and can capture a chart screenshot without navigating, switching tabs, clicking orders, or executing trades.

The reader accepts OHLC candles only from an explicit verified provider (`window.__GOLDBOT_CANDLES__`). It never reconstructs OHLC from pixels. Therefore H&S confirmation is only promoted when verified candles are available.

## H&S rule

- Bearish head-and-shoulders: require a closed candle below the neckline and the candle high must remain below the neckline (no touch/straddle).
- Bullish inverse head-and-shoulders: require a closed candle above the neckline and the candle low must remain above the neckline (no touch/straddle).
- H&S direction conflicts with 4H/1H gravity => signal is blocked to WAIT.

## Signal gate

The Rule Engine is deterministic and fail-closed. It requires 4H/1H agreement, stable gravity, 15M alignment, KFOO quality thresholds, 15M candle close, then 5M + 3M alignment for STRONG_ENTRY.

## Site connection

`site_server.py` now exposes `chart_reader` and `head_shoulders` in `/api/health`, `/api/public-state`, and the TradingView webhook state. Execution remains OFF.

This repository does not claim complete OHLC extraction from TradingView until a verified candle provider is present in the live browser session.
