# GOLD-BOT Auto-Repair / Auto-Development

This layer is intentionally fail-closed.

## Automatic repair
The supervisor may automatically recover operational failures by restarting an exited or stale monitor and reconnecting/retesting after connection failures.

A known source-code defect is not silently edited in production. It is quarantined and converted into an improvement proposal.

## Automatic development
Observed failures and quality regressions become structured proposals. A candidate change must pass:
1. backup or isolated branch;
2. syntax validation;
3. unit tests;
4. integration tests;
5. live read test;
6. quality gate;
7. deployment;
8. post-deployment watch;
9. automatic rollback on regression.

Trading execution remains OFF throughout this pipeline.

## Current known defect
analyze_timeframe() missing 1 required positional argument: 'tf' is classified as a code integration defect. Safe behavior is quarantine + proposal, not an unsafe blind source edit.
