# Opportunity Scanner V1

The scanner is analysis-only and fail-closed.

## Ranking logic

1. Reject high/extreme Risk Ratio.
   - default rejection threshold: >=60%
   - extreme: >=80%
2. Require Reward/Risk >= 2.0R.
3. Prefer 4H + 1H gravity aligned with direction.
4. Prefer 15M leader alignment.
5. Prefer 5M + 3M timing alignment.
6. Prefer KFOO TF >=62.5% and indicators >=75%.
7. Prefer positive liquidity and continuity-average agreement.

Missing values are never fabricated. A missing Reward/Risk blocks a candidate from TRADEABLE.

## Telegram

Set:
- GOLDBOT_TELEGRAM_BOT_TOKEN
- GOLDBOT_TELEGRAM_CHAT_ID
- GOLDBOT_TELEGRAM_ALERTS=1

The webhook sends a Telegram alert only for TRADEABLE opportunities and keeps execution OFF.

For live multi-symbol scanning, the upstream process should provide GOLDBOT_OPPORTUNITY_CANDIDATES_JSON.

Example shape:
{"candidates":[{"symbol":"ABCUSDT","direction":"long","risk_ratio_pct":20,"entry":100,"stop":98,"target":106}]}

No exchange order is placed by this module.
