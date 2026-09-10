# V56 live KFOO source requirement

The read-only V56 runner requires **real, verified KFOO output** before it can produce a directional result.

## Current state

- TradingView/CDP connectivity: available.
- XAU/USD identity: available.
- MTF OHLC: available from Twelve Data.
- H&S: available from verified OHLC.
- Live KFOO publisher: **not present in the current TradingView page**.

The provider accepts only an explicitly published payload under `window.__GOLDBOT_KFOO__` or the documented `data-goldbot-kfoo` JSON bridge. It does not OCR the chart, infer KFOO from pixels, or synthesize missing values.

## Required recovery

Restore the original KFOO producer that was used by the working local V56 package, then publish its verified analysis to one of the supported bridges. The legacy link test references `live_vision_agent_fixed` plus `kfoo_table`/`kfoo_direction`, but those producer modules are not present in this repository.

Do **not** treat the system as KFOO-ready until the live probe reports a real source and the full 4h/1h/15m/5m/3m payload validates.
