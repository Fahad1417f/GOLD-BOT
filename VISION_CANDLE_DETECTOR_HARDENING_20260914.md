# Vision candle detector hardening — 2026-09-14

The detector was hardened against the failure observed in the live TradingView capture.

## Change
- Do not aggregate every saturated pixel into one chart-wide group.
- Inspect each x-column independently and keep its longest contiguous red/green/cyan vertical run.
- Group only nearby columns with vertically compatible runs.
- Require body geometry and at least one wick extension.
- Horizontal gridlines, dashed trendlines, and unrelated plot lines no longer weld the ROI into one candidate.

## Safety
- Pixel candidates remain geometry-only.
- No price/OHLC value is inferred from screenshot pixels.
- `ohlc_verified` remains fail-closed until distinct verified price-scale anchors are available.
- Execution/trading remains OFF.
