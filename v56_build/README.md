# V56 Readonly Integrated Verified

This release branch wires the repository's verified components into one fail-closed readonly runner.

Flow:
1. TradingView identity via existing Chromium CDP and Playwright.
2. Verified XAU/USD MTF OHLC from Twelve Data: 4h, 1h, 15m, 5m, 3m.
3. Verified MTF head-and-shoulders confirmation.
4. Live KFOO analysis is accepted only from GOLDBOT_KFOO_ANALYSIS_JSON.
5. V56 signal promotion consumes that upstream KFOO input plus verified H&S.
6. No trade execution, Telegram action, webhook action, OpenAI action, or Binance action is enabled.

Important: the runner deliberately refuses to fabricate KFOO markers when the live KFOO source is absent.
