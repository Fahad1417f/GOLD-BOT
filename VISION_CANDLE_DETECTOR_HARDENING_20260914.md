# Vision + KFOO hardening — 2026-09-14

## KFOO research findings

KFOO AI documentation describes independent controls for the number of candles used in historical/backward reading for blocks, trends, and liquidity analysis, plus selectable wave-monitoring modes (scalp/swing/investment) and smart-target/risk systems. It also describes KFOO Smart Candles and analytical tables. The product documentation does not publish one universal optimal candle count for every chart/frequency.

The supplied KFOO guidance further defines the continuation-average semantics:
- candles above the continuation average are positive; below are negative;
- a touch is treated as a possible bounce/retest rather than an automatic trend reversal;
- a real break requires candles to open and close on the opposite side of the average;
- thick continuation averages imply shorter/more oscillatory waves, while thin averages imply stronger waves;
- swing monitoring is intended to distinguish the main wave from corrections, while lightning monitoring is intended for faster corrective/bounce observations;
- the risk-ratio bar uses wave age (example: 5 candles from the wave start) and volatility/risk context, with red as the high-risk zone, green as the preferred zone, and blue as low-liquidity/choppy context.

## Implementation decision

The live pixel detector is intentionally not responsible for interpreting these semantics from unlabeled canvas pixels. It first isolates a compact price-pane candle series, then limits the returned history to 24 candles by default.

Configuration:
- `min_series_pitch=16px`
- `max_series_pitch=48px`
- `x_merge_distance=11px`
- `max_returned_candles=24`
- conservative `price_pane_ratio=0.55`

Nearby same-x fragments are merged before series detection, which targets the live failure where KFOO/indicator overlays produced many false candle candidates.

## Safety

- Pixel candidates remain geometry-only.
- No price/OHLC value is inferred from screenshot pixels.
- KFOO trade readiness is never inferred from unlabeled numbers.
- `ohlc_verified` remains fail-closed until distinct verified price-scale anchors are available.
- Execution/trading remains OFF.
