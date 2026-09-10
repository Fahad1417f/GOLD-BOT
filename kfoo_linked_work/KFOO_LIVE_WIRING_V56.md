# V56 LIVE KFOO wiring

This release keeps the existing V56 READONLY safety contract:
- TRADE_EXECUTION remains OFF.
- No timeframe clicks, browser navigation, order entry, Telegram actions, webhook actions, OpenAI actions, or Binance actions are enabled by this bridge.
- KFOO values are accepted only from the real visual KFOO table produced by the existing live vision agent.
- Missing/unknown required cells and missing aggregates fail closed.
- Neutral KFOO is a valid observed state and does not become a directional trade signal.

## Architecture

TradingView (existing browser/CDP)
  -> existing live_vision_agent_fixed.py
  -> live_kfoo_agent_launcher_v56.py
  -> POST http://127.0.0.1:8765/publish
  -> tradingview_kfoo_publisher_v56.py
  -> window.__GOLDBOT_KFOO__ + data-goldbot-kfoo
  -> V56 readonly provider
  -> verified signal engine

The launcher is intentionally a wrapper: it monkey-patches the existing agent's publish hook at runtime, so the original visual agent file does not need to be edited.

## Windows run order

Do not paste Markdown fences such as ```bat into CMD. Paste only the command lines.

1. Update the V56 repository:

cd /d "C:\Users\thinkpad\Downloads\GOLD-BOT-V56-READONLY"
git pull origin release/v56-readonly-integrated-verified

2. Copy the launcher beside the existing live agent:

copy /Y "C:\Users\thinkpad\Downloads\GOLD-BOT-V56-READONLY\kfoo_linked_work\live_kfoo_agent_launcher_v56.py" "C:\Users\thinkpad\Downloads\GOLD_BOT_V56_LIVE_KFOO_WIRED\GOLD_BOT_V56_LIVE_KFOO_WIRED\"

3. Verify the TradingView CDP endpoint before starting the publisher:

curl http://127.0.0.1:9222/json/version

The response must be JSON. If it fails, the TradingView browser is not exposed on CDP port 9222 yet.

4. Start the verified publisher in CMD window A:

cd /d "C:\Users\thinkpad\Downloads\GOLD-BOT-V56-READONLY"
set PYTHONIOENCODING=utf-8
"C:\Users\thinkpad\Downloads\GOLD-BOT_APPROVED_WINDOWS\.venv\Scripts\python.exe" kfoo_linked_work\tradingview_kfoo_publisher_v56.py

Keep this window running.

5. Start the existing visual agent through the new wiring wrapper in CMD window B:

cd /d "C:\Users\thinkpad\Downloads\GOLD_BOT_V56_LIVE_KFOO_WIRED\GOLD_BOT_V56_LIVE_KFOO_WIRED"
set PYTHONIOENCODING=utf-8
set GOLDBOT_LIVE_AGENT_DIR=C:\Users\thinkpad\Downloads\GOLD_BOT_V56_LIVE_KFOO_WIRED\GOLD_BOT_V56_LIVE_KFOO_WIRED
"C:\Users\thinkpad\Downloads\GOLD-BOT_APPROVED_WINDOWS\.venv\Scripts\python.exe" live_kfoo_agent_launcher_v56.py

6. The live agent must produce KFOO_PUBLISH=PASS in v56_monitor.log after a real table is detected. The publisher window must also show PUBLISHED.

7. Only after the publisher and live agent are running, run the V56 readonly verifier in CMD window C:

cd /d "C:\Users\thinkpad\Downloads\GOLD-BOT-V56-READONLY"
set PYTHONIOENCODING=utf-8
"C:\Users\thinkpad\Downloads\GOLD-BOT_APPROVED_WINDOWS\.venv\Scripts\python.exe" v56_build\run_v56_overnight_readonly.py

Expected KFOO lines after the live table is actually published:
KFOO_PROBE_SOURCE=window.__GOLDBOT_KFOO__ (or dom)
KFOO_PROBE=FOUND
KFOO_SOURCE=TRADINGVIEW_LIVE_PROVIDER
V56_READONLY=PASS

If the real table is not detected, the system must stay fail-closed. Do not replace it with synthetic JSON or manual values.

## Important

The first failure was not a Python dependency problem. It was the missing live KFOO publisher. The release now contains the publisher and the launcher that wires the existing visual KFOO producer to that publisher. The remaining runtime dependency is the user's actual TradingView page being available through CDP and the real KFOO table being visibly detected.
