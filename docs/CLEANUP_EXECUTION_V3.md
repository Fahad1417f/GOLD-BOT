# Cleanup Execution V3

Date: 2026-09-16
Branch: refactor/cleanup-v1

## Scope

Deep hygiene only. Runtime module boundaries and import paths are unchanged.

## Findings

- Crypto modules are retained because Crypto is required product scope.
- V56 perception, candle verification, MTF, H&S and signal modules are retained.
- Opportunity Scanner and Binance discovery are retained as legacy Crypto capability; they are candidates for later internal cleanup, not deletion.
- Both root and website UI surfaces are retained because they use different state transports.
- Both backend and site_server are retained because launch/CI references have not been fully canonicalized.
- Runtime-generated state/log/cache files are excluded by .gitignore.
- Auto-development/self-healing files are retained on this legacy branch to avoid structural changes; they are explicitly excluded from future Core migration.

## Safety

No runtime Python module, import path, UI transport, launcher, or workflow was changed in V3. No execution capability was enabled.

## Migration boundary

Only tested, canonical KFOO/MTF/evidence/R:R components are eligible for gold-monitor-core. Crypto capability will migrate through a separate market adapter/domain boundary while sharing KFOO rules.
