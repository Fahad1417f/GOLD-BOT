# GOLD-BOT Automatic Operations Policy

## Goals
- Continuous read-only monitoring.
- Automatic operational recovery.
- Automatic validation after recovery.
- Automatic improvement proposals based on observed failures.
- Experimental deployment must have an explicit validation and rollback mechanism.

## Safety boundaries
- TRADE_EXECUTION remains OFF.
- Production Binance execution remains BLOCKED.
- The supervisor never edits Python source code automatically.
- A code-level defect is diagnosed and quarantined, not silently patched.
- Future auto-development candidates must be tested before deployment.

## Automatic recovery
1. Detect monitor exit.
2. Restart the monitor up to GOLDBOT_MAX_RESTARTS.
3. Detect stale monitor output.
4. Restart a stale monitor.
5. Detect the known analyze_timeframe integration failure.
6. Enter SAFE_MODE and write auto_improvement_proposal.json instead of making an unsafe source edit.

## Validation gate
BACKUP/BRANCH -> SYNTAX TEST -> UNIT TEST -> INTEGRATION TEST -> LIVE READ TEST -> QUALITY CHECK -> DEPLOY -> POST-DEPLOY WATCH -> ROLLBACK ON REGRESSION.
