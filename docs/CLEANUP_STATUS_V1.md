# Cleanup Status — V1

## Applied
- Removed duplicate `v56_signal_monitor/signal_engine_v56.py` wrapper. The authoritative implementation remains under `kfoo_linked_work/signal_engine_v56.py`.
- Removed `backend/WRITE_TEST.txt`, a non-runtime write probe.

## Deliberately retained for now
- TradingView/Playwright components: still required for current V56 experiments and must be dependency-audited before removal.
- Opportunity scanner V1/V2: not deleted until import/test references are resolved.
- Backend/site server/UI: overlapping, but deleting one without a dependency graph could break the current monitor.
- CI workflows: consolidation deferred until workflow references and test commands are compared.
- Auto-supervisor/self-healing: operational code, not Core; retained as legacy until migration.

## Rule
No destructive cleanup without reference verification. The new `gold-monitor-core` receives only canonical, tested components.
