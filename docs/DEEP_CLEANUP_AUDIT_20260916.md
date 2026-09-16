# Deep Cleanup Audit — No Structural Changes

Date: 2026-09-16
Branch: refactor/cleanup-v1

## Constraint

This pass intentionally does NOT change module boundaries, import paths, runtime contracts, or directory layout. The goal is to reduce obvious clutter and identify safe future removals without destabilizing V56.

## Verified dependency findings

### 1. Signal engine
- Authoritative implementation: `kfoo_linked_work/signal_engine_v56.py`.
- The former `v56_signal_monitor/signal_engine_v56.py` wrapper was redundant.
- Multiple tests still intentionally compare/import the two paths in the historical/main tree, so no further signal-engine consolidation is performed in this pass.

### 2. TradingView perception
The following are live dependencies and are retained:
- `playwright_chart_reader.py`
- `chart_controller.py`
- `verified_chart_controller.py`
- `vision_live_capture_v1.py`
- `vision_candle_detector_v1.py`
- `vision_screen_reconstructor_v1.py`
- `vision_identity_v1.py`
- their regression tests

They are not interchangeable: reader, controller, capture, detector, reconstruction, and identity checks have different responsibilities.

### 3. Verified signal pipeline
Retained:
- `verified_candle_source_v56.py`
- `verified_mtf_candle_pipeline_v56.py`
- `verified_hns_mtf_v56.py`
- `verified_signal_integration_v56.py`
- `head_shoulders_v56.py)
- related tests

These form a dependency chain; deleting one based only on filename similarity would be unsafe.

### 4. Runtime bridge
`github_state_bridge.py` is operational glue, not signal logic. It is retained because the current website state path depends on it.

`virtual_trade_tracker.py` is also retained. It is virtual/read-only accounting and must not be confused with order execution.

### 5. Web surface
There are two UI surfaces:
- root `index.html/app.js/style.css`
- `website/index.html/app.js/style.css`

They are similar but NOT identical. Root `app.js` reads published GitHub state, while `website/app.js` reads `/api/public-state`. Therefore they must not be merged/deleted without first deciding which transport is canonical.

### 6. Backend/server
`backend/main.py` and `site_server.py` both exist. Search confirms `site_server.py` is directly referenced by launch/CI documentation. This is a consolidation candidate, not a safe deletion.

### 7. Crypto scope
Crypto functionality is required. Binance discovery and Opportunity Scanner remain in this branch and are marked for future refactoring, not deletion. Their role should be preserved while reducing duplication.

## Safe hygiene actions

- Runtime/generated files are already ignored by `.gitignore`:
  - `.env*`
  - Python cache
  - logs
  - `virtual_trades.json`
  - temporary website state
- No credentials or API keys are added.
- No execution path is enabled.
- No directory or import structure is changed.

## High-confidence cleanup candidates for the next pass

These require reference verification before deletion:
1. stale/duplicate documentation for old scanner versions
2. duplicate launcher BAT files
3. overlapping CI workflows
4. duplicated UI surface
5. obsolete test probes and historical artifacts

## Explicitly NOT removed

No active Python module was removed in this pass. This preserves the current code structure and minimizes regression risk.

## Acceptance condition

Before any structural consolidation:
- all import references must be mapped
- all launchers/CI references must be mapped
- tests must be runnable in a local clone
- the resulting branch must keep Execution=OFF

