# GOLD-BOT Cleanup Audit — V56

Date: 2026-09-16

## Objective

Reduce the existing GOLD-BOT codebase before migrating proven components into `gold-monitor-core`.

This branch is intentionally non-destructive at first. Deletions are grouped by confidence and dependency risk.

## Findings

### A. Duplicate / redundant paths

1. `v56_signal_monitor/signal_engine_v56.py`
   - Thin re-export of `kfoo_linked_work.signal_engine_v56`.
   - Recommendation: remove after all imports are canonicalized to the authoritative engine.

2. `backend/main.py` and `site_server.py`
   - Both expose public state and a TradingView webhook.
   - They implement overlapping runtime contracts.
   - Recommendation: choose one transport layer; do not maintain two state authorities.

3. Opportunity Scanner V1/V2
   - V2 imports/extends V1.
   - Recommendation: keep the common domain model only; collapse V1/V2 into one scanner in the new core.

4. Multiple launcher BAT files
   - `run_gold_bot_auto.bat`
   - `run_gold_bot_continuous.bat`
   - `run_gold_bot_site_and_monitor.bat`
   - `run_v56_connected.bat`
   - `run_v56_fast_signal_lane.bat`
   - Recommendation: one canonical launcher plus optional diagnostic commands.

5. Multiple GitHub workflows
   - `validate.yml`
   - `v56-linkage.yml`
   - `v56-validation.yml`
   - `package-main.yml`
   - `vision-agent-v1.yml`
   - Recommendation: consolidate overlapping validation into one required CI workflow and one optional packaging workflow.

### B. Valuable components to preserve

- `kfoo_linked_work/signal_engine_v56.py`
- `kfoo_linked_work/verified_candle_source_v56.py`
- `kfoo_linked_work/verified_mtf_candle_pipeline_v56.py`
- `kfoo_linked_work/verified_hns_mtf_v56.py`
- `kfoo_linked_work/head_shoulders_v56.py`
- `kfoo_linked_work/vision_agent_v1.py`
- `kfoo_linked_work/vision_candle_detector_v1.py`
- `kfoo_linked_work/vision_screen_reconstructor_v1.py`
- relevant regression tests
- deterministic KFOO rule/evidence logic

### C. Isolate from Core

- broker/exchange code
- Binance market discovery
- opportunity scanner
- Telegram/device agent
- self-healing/auto-supervisor
- web UI/backend
- deployment scripts
- experimental auto-development
- TradingView browser control

These can become adapters or operational tooling later.

## Critical technical issue

`kfoo_linked_work/e2e_monitor_v56.py` currently requires verified TradingView identity before it proceeds to MTF/H&S/signal stages. The live failure:

`TRADINGVIEW_IDENTITY_NOT_VERIFIED: DOM_METADATA_READ`

therefore blocks the entire E2E chain.

The new core must not make DOM metadata the source of truth for KFOO evidence.

## Target reduction

The new core should converge toward:

`input -> normalized evidence -> KFOO hard rules -> MTF context -> signal state -> outcome`

with no broker execution and no browser-control dependency.

## Deletion policy

- HIGH confidence: safe to remove after import/CI reference check.
- MEDIUM confidence: consolidate only after dependency graph verification.
- LOW confidence: retain as legacy/reference until replacement passes tests.

## Next mechanical cleanup

1. Build import/reference graph.
2. Canonicalize signal engine imports.
3. Consolidate state/webhook transport.
4. Consolidate CI.
5. Consolidate launchers.
6. Remove dead modules only after tests pass.
7. Copy only the surviving tested components into `gold-monitor-core`.

Execution remains OFF.
