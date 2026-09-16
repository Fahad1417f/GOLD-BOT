# GOLD-BOT

Legacy production/research workspace for the KFOO-based multi-market monitor.

## Scope

- Gold
- Cryptocurrency
- Shared KFOO rules across both markets
- Multi-timeframe analysis
- Risk/Reward (R:R)
- Read-only monitoring

## Cleanup policy

This branch is a conservative cleanup branch. Active module paths and runtime contracts are preserved. Cleanup removes only verified redundancy or documentation clutter; functional consolidation is deferred until dependency references are mapped.

## Core direction

The future `gold-monitor-core` repository will extract tested, canonical components from this workspace. Gold and Crypto will share the KFOO analysis core while keeping market-specific adapters separate.

## Safety

Execution remains OFF. No API secrets or credentials belong in the repository.
