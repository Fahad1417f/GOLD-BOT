# GOLD BOT — KFOO Chart Control + Strategy Roles

- Gravity: 4H + 1H only.
- Leader: 15M.
- Entry: 5M + 3M.
- 2M: excluded.

Chart control is intended for Playwright/CDP, chart-only, with verification after actions. Navigation, tab switching, order clicks and production execution are blocked.

The Rule Engine is deterministic and fail-closed. It requires 4H/1H agreement, 15M alignment, at least 3/4 KFOO components on 15M, and both 5M and 3M aligned before ready=True.

This package does not claim complete visual extraction of KFOO indicators from TradingView; it provides the chart-control and decision-gating layer.
