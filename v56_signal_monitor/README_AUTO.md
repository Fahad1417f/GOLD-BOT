# V56 Automatic Supervisor

The supervisor is the operational watchdog for the existing local V56 monitor.

It automatically:
- starts the V56 monitor;
- restarts an exited monitor;
- detects stale monitor output;
- diagnoses the known analyze_timeframe integration error;
- enters SAFE_MODE instead of performing an unsafe source edit;
- records an improvement proposal for later validated development.

The GitHub state bridge publishes read-only state to website_state.json.

Run from the repository root:
    run_gold_bot_auto.bat

The existing V56 build is expected at:
    v56_build\run_v56_overnight_readonly.bat

Execution remains OFF.