from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "kfoo_linked_work") not in sys.path:
    sys.path.insert(0, str(ROOT / "kfoo_linked_work"))

from playwright_chart_reader import PlaywrightChartReader
from verified_signal_integration_v56 import VerifiedSignalIntegrationV56

REQUIRED_TFS = ("4h", "1h", "15m", "5m", "3m")
LOG = Path(os.getenv("GOLDBOT_MONITOR_LOG", ROOT / "v56_monitor.log"))

def emit(message: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8", errors="ignore") as f:
        f.write(message + "\n")
    print(message, flush=True)

def safe_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def load_kfoo() -> tuple[dict | None, dict]:
    raw = os.getenv("GOLDBOT_KFOO_ANALYSIS_JSON", "").strip()
    timing_raw = os.getenv("GOLDBOT_TIMING_JSON", "").strip()
    if not raw:
        return None, {}
    analysis = json.loads(raw)
    if not isinstance(analysis, dict):
        raise RuntimeError("GOLDBOT_KFOO_ANALYSIS_JSON must be a JSON object")
    timing = json.loads(timing_raw) if timing_raw else {}
    if not isinstance(timing, dict):
        raise RuntimeError("GOLDBOT_TIMING_JSON must be a JSON object")
    return analysis, timing

def main() -> int:
    safe_stdout()
    emit("V56_READONLY=START")
    emit("TRADE_EXECUTION=OFF")
    emit("TELEGRAM_ACTIONS=OFF")
    emit("WEBHOOK_ACTIONS=OFF")
    emit("OPENAI_ACTIONS=OFF")
    emit("BINANCE_ACTIONS=OFF")
    emit("2M_POLICY=BLOCKED")

    reader = PlaywrightChartReader()
    chart = reader.connect()
    emit(f"PAGE={'PASS' if chart.connected else 'FAIL'}")
    emit(f"TRADINGVIEW_SYMBOL={'PASS' if chart.symbol == 'XAU/USD' else 'FAIL'} value={chart.symbol}")
    emit(f"TRADINGVIEW_TIMEFRAME={'PASS' if chart.timeframe else 'FAIL'} value={chart.timeframe}")
    if not chart.connected or chart.symbol != "XAU/USD":
        emit("V56_READONLY=FAIL TRADINGVIEW_IDENTITY_NOT_VERIFIED")
        return 2

    integration = VerifiedSignalIntegrationV56(
        api_key=os.getenv("TWELVEDATA_API_KEY") or os.getenv("TWELVE_DATA_API_KEY")
    )
    inputs = integration.read_verified_inputs(
        outputsize=int(os.getenv("GOLDBOT_CANDLE_OUTPUTSIZE", "100"))
    )
    mtf = inputs["mtf"]
    hns = inputs["hns"]

    if not mtf.get("verified"):
        emit("MTF_OHLC=FAIL " + str(mtf.get("reason")))
        return 3
    emit("MTF_OHLC=PASS 4h,1h,15m,5m,3m")

    if not hns.get("verified"):
        emit("HNS=FAIL " + str(hns.get("reason")))
        return 4
    emit(f"HNS=PASS aligned={hns.get('aligned')} direction={hns.get('direction')}")

    # Prefer the live, explicitly verified provider exposed by the TradingView
    # page. Environment JSON remains available only as an upstream integration
    # fallback and is never synthesized by this process.
    try:
        analysis, timing = reader.read_live_kfoo()
        emit("KFOO_SOURCE=TRADINGVIEW_LIVE_PROVIDER")
    except Exception as live_exc:
        analysis, timing = load_kfoo()
        if analysis is None:
            emit("KFOO_SOURCE=FAIL " + str(live_exc))
            emit("KFOO_MARKERS=NOT_PUBLISHED_SYNTHETIC_DATA_FORBIDDEN")
            emit("V56_READONLY=FAIL KFOO_SOURCE_NOT_CONFIGURED")
            return 5
        emit("KFOO_SOURCE=VERIFIED_UPSTREAM_INPUT")
        emit("KFOO_LIVE_PROVIDER=UNAVAILABLE reason=" + type(live_exc).__name__)

    from signal_engine_v56 import promote
    sig = promote(analysis, timing=timing, verified_hns_mtf=hns)

    for tf in REQUIRED_TFS:
        frame = analysis.get(tf) or {}
        info = frame.get("analysis") or {}
        table = info.get("kfoo_table") or {}
        aggs = table.get("aggregates") or {}
        tfagg = aggs.get("timeframes") or {}
        indagg = aggs.get("indicators") or {}
        active = ((table.get("timeframes") or {}).get("15m") or {}).get("signal", frame.get("active_kfoo", "unknown"))
        direction = frame.get("active_kfoo") or info.get("direction") or "unknown"
        emit(f"DIRECTION_{tf.upper()}={direction}")
        if tf == "15m":
            emit(f"KFOO_TF_AGG_15M={tfagg}")
            emit(f"KFOO_IND_AGG_15M={indagg}")
            emit(f"KFOO_ACTIVE_15M={active}")
            emit("KFOO_SOURCE=VERIFIED_UPSTREAM_INPUT")

    emit(f"V56_SIGNAL=PASS level={sig.level} direction={sig.direction} score={sig.score:.2f} entry_ready={sig.entry_ready}")
    emit("V56_READONLY=PASS")
    reader.close()
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        emit(f"V56_READONLY=FAIL {type(exc).__name__}:{exc}")
        raise
