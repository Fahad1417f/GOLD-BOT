# Binance Market Discovery -> Opportunity Scanner

Uses public Binance USDⓈ-M endpoints for discovery only:
- exchangeInfo: tradable USDT perpetual symbols
- 24hr ticker: price change and quote volume

The output uses TradingView-style perpetual display symbols: XXXUSDT.P.

Important: this layer does NOT invent KFOO, continuity, liquidity-table, or
Risk Ratio values. It marks candidates as requiring KFOO enrichment. The
Opportunity Scanner remains fail-closed until those fields are supplied.

Execution remains OFF.
