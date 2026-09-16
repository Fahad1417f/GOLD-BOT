# Deep Proof Report — Cleanup Safety

Date: 2026-09-16
Branch: refactor/cleanup-v1

## Proven facts

1. The branch tree is intact and contains the required Gold + Crypto components.
2. KFOO, MTF, H&S, Vision, Binance and Opportunity Scanner remain present.
3. The previous duplicate signal-engine wrapper is absent; the canonical `kfoo_linked_work/signal_engine_v56.py` remains.
4. The current workflows test different scopes:
   - `v56-linkage.yml`: KFOO/V56 linkage, H&S, market context, fast lane, Playwright reader.
   - `v56-validation.yml`: runtime bridge/self-healing test surface.
   - `validate.yml`: runtime monitor + Opportunity Scanner + Telegram.
   - `vision-agent-v1.yml`: vision regression.
   - `package-main.yml`: packaging only.
   They are therefore not safe to collapse blindly.
5. Launcher scripts are not equivalent:
   - `run_gold_bot_continuous.bat` provisions dependencies and starts vision + supervisor.
   - `run_gold_bot_auto.bat` starts site + supervisor.
   - `run_v56_connected.bat` starts a state bridge and an external V56 build.
   - `run_v56_fast_signal_lane.bat` runs the fast webhook lane.
   - `run_opportunity_binance_discovery.bat` is Crypto discovery.
   - `run_gold_bot_site_and_monitor.bat` is a wrapper around the auto launcher.
6. `TEST_RESULTS.json` records deterministic integration tests as PASS and explicitly records execution OFF; its live CDP connection was not run in that environment.

## Safe conclusion

No further launcher/workflow deletion can be justified from static evidence alone without first executing the relevant tests in a Windows clone. Deleting or merging them now would violate the no-structure-change constraint.

## Required next proof

Run, in the user's Windows clone:
- project test suite
- launcher smoke tests where practical
- compile/import check
- V56 read-only E2E
- Crypto discovery/scanner tests

Record outputs before any functional refactor.

## Current status

CLEANUP_STATIC_PROOF = PASS
RUNTIME_PROOF = PENDING_USER_WINDOWS_ENVIRONMENT
EXECUTION = OFF
