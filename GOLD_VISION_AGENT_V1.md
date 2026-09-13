# GOLD Vision Agent V1

Fourth-agent architecture combining live screen capture, deterministic chart
geometry, candle reconstruction, MTF evidence, and evidence-first signal gating.

## Implemented
- Perception-only OHLC evidence core.
- Read-only TradingView Playwright/CDP capture contract.
- Deterministic pixel-candle -> OHLC mapper requiring two distinct verified scale anchors.
- Regression tests for missing anchors and invalid candle geometry.

## Not yet signal-capable
The system does NOT infer OHLC from arbitrary screenshots yet. A detector for
body/wick pixels and a verified TradingView price-scale anchor source must pass
the screenshot corpus before reconstructed candles are admitted to Signal Engine.

## Safety
No broker/exchange dependency exists in the vision modules. Execution remains OFF.
