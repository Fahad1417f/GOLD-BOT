# V56 Automatic Supervisor

The GOLD-BOT supervisor provides a guarded unattended control loop around the existing local V56 monitor.

## Automatic repair
- restarts an exited monitor;
- detects stale monitor output;
- diagnoses known runtime/import/connection failures;
- quarantines code-integration failures instead of editing source blindly;
- records repair and validation state;
- keeps EXECUTION=OFF and SAFE_MODE=ON.

## Automatic development
`auto_developer.py` evaluates live monitor output and creates improvement proposals when it detects:
- KFOO coverage/confidence degradation;
- gravity/leader disagreement;
- runtime exceptions;
- connection failures.

Development is proposal-only. It does not self-modify source code.

Every future code change must pass:
BACKUP_OR_BRANCH -> SYNTAX_TEST -> UNIT_TEST -> INTEGRATION_TEST -> LIVE_READ_TEST -> QUALITY_CHECK -> POST_DEPLOY_WATCH -> ROLLBACK_ON_REGRESSION

## Build discovery
The supervisor accepts GOLDBOT_BUILD_PATH. If it is not set, it first checks v56_build, then safely searches sibling GOLD_BOT_V56* folders for v56_build\\run_v56_overnight_readonly.bat.

## Website state
The GitHub state bridge publishes read-only website_state.json for the website. No GitHub token is stored in the repository.

## Run
From the repository root:

    run_gold_bot_auto.bat

The launcher selects a project .venv first, then the approved sibling V56 environment, then falls back to python.

Trading execution remains OFF.
