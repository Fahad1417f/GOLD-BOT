# Cleanup Scope — Gold + Crypto

Date: 2026-09-16

The cleanup branch preserves cryptocurrency functionality. Crypto is a required product capability, but it must be separated from the Gold Monitor Core rather than deleted.

## Product scope

- Gold monitoring: required.
- Cryptocurrency monitoring: required.
- Read-only by default.
- No automatic order execution in Core.

## Architecture boundary

Gold and Crypto share:
- normalized market data contracts
- multi-timeframe context
- evidence model
- signal state
- outcome tracking
- alert contracts

They may use separate adapters:
- TradingView / KFOO for Gold
- exchange/data adapters for Crypto

## Cleanup rule

Remove duplication and self-modifying infrastructure, not required crypto capability.

Opportunity Scanner and Binance discovery remain legacy candidates for refactoring into a dedicated Crypto module rather than deletion.

Execution remains OFF.
