# KFOO Evidence Adapter V1

The adapter is a read-only perception boundary between TradingView visible text and the KFOO rule layer.

## Evidence states

- PRESENT: the configured KFOO label/phrase is explicitly visible.
- UNREADABLE: the source is available, but no verifiable KFOO label was found.
- DATA_UNAVAILABLE: visible text was not supplied or is empty.
- ABSENT: reserved for future explicit negative observations; a missing label is never treated as ABSENT.

## Fail-closed rules

The adapter does not infer KFOO evidence from RSI, generic volume, price direction, candles, or other non-KFOO indicators. For example, a bullish RSI does not become continuity_average, and volume does not become liquidity.

Aliases are configurable because the repository does not establish one fixed KFOO on-screen layout. No undocumented screen coordinates are assumed.

This layer does not create trade signals and does not enable execution.
