# KFOO visual monitoring rules — 2026-09-14

This note records the integration contract derived from the KFOO material supplied for the project and public KFOO product information.

## Monitoring priorities
- Continuation is read from the continuity average relative to the candles/wave: above is positive, below is negative, contact is treated as consolidation/oscillation.
- A confirmed break requires the candle to open beyond the continuity average and close on that side.
- Thick continuity average is treated as shorter/oscillatory waves; thin continuity average as stronger waves.
- Swing monitoring is for identifying the primary wave versus correction; Lightning monitoring is for faster correction/rebound observations.
- Risk-ratio monitoring uses the displayed wave-candle count and volatility/risk band as context; it is not treated as a standalone trade signal.

## GOLD-BOT contract
- KFOO UI text is the primary source for KFOO-labelled state when exposed in the page DOM.
- Screenshot pixels are used only for geometry/visual confirmation and must not invent KFOO marker values.
- Candle monitoring defaults to a small recent window (24) and is capped in code.
- `ohlc_verified` remains false until price-scale anchors are independently verified.
- Execution remains OFF.
