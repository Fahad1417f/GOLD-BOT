from __future__ import annotations

"""V56 end-to-end monitor harness.

Stages:
  TradingView/Playwright identity -> verified MTF OHLC -> verified MTF H&S
  -> KFOO analysis input -> V56 Signal Engine -> local webhook.

The harness is read-only and fail-closed. It never enables or executes trades.
For a real run, provide KFOO analysis as JSON via GOLDBOT_KFOO_ANALYSIS_JSON
and optionally GOLDBOT_TIMING_JSON. Use --smoke for a deterministic downstream
contract test when live KFOO output is not yet wired into this process.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from playwright_chart_reader import read_tradingview_chart  # noqa: E402
from verified_signal_integration_v56 import VerifiedSignalIntegrationV56  # noqa: E402
from signal_engine_v56 import promote  # noqa: E402


REQUIRED_TFS = ("4h", "1h", "15m", "5m", "3m")


def _direction(v: object) -> str | None:
    if v in ("long", "bullish"):
        return "long"
    if v in ("short", "bearish"):
        return "short"
    return None


def smoke_analysis(direction: str = "long") -> dict:
    def frame(bias: str = direction) -> dict:
        return {
            "samples": [{"active_kfoo": bias}] * 3,
            "active_kfoo": bias,
            "analysis": {
                "direction": bias,
                "kfoo_table_detected": True,
                "kfoo_table_direction": {"bias": bias},
                "kfoo_table": {
                    "aggregates": {
                        "timeframes": {"bullish_pct": 75.0, "bearish_pct": 25.0},
                        "indicators": {"bullish_pct": 80.0, "bearish_pct": 20.0},
                    },
                    "timeframes": {"15m": {"signal": bias}},
                },
            },
        }

    return {tf: frame() for tf in REQUIRED_TFS}


def smoke_hns(direction: str = "long") -> dict:
    return {
        "verified": True,
        "aligned": True,
        "direction": direction,
        "frames": {
            "4h": {"verified": True, "detected": True, "confirmed": True},
            "1h": {"verified": True, "detected": True, "confirmed": True},
            "15m": {"verified": True, "detected": True, "confirmed": True},
        },
    }


def post_json(url: str, payload: dict, timeout: float = 10.0) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def load_json_env(name: str) -> dict:
    raw = os.getenv(name, "").strip()
    if not raw:
        raise RuntimeError(f"{name} is required for live E2E")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise RuntimeError(f"{name} must contain a JSON object")
    return value


def assert_execution_off() -> None:
    forbidden = {
        "GOLDBOT_REAL_TRADING", "GOLDBOT_DEMO_TRADING", "GOLDBOT_FAST_TRADE",
    }
    for key in forbidden:
        if os.getenv(key, "").strip().lower() in {"1", "true", "yes", "on"}:
            raise RuntimeError(f"FAIL_CLOSED_EXECUTION_FLAG={key}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="deterministic downstream contract test")
    parser.add_argument("--webhook", default=os.getenv("GOLDBOT_WEBHOOK_URL", "http://127.0.0.1:3000/api/webhooks/tradingview"))
    args = parser.parse_args()

    assert_execution_off()
    print("E2E_EXECUTION=OFF")

    chart = read_tradingview_chart()
    if not chart.get("verified") or chart.get("symbol") != "XAU/USD":
        raise RuntimeError(f"TRADINGVIEW_IDENTITY_NOT_VERIFIED: {chart}")
    if not chart.get("timeframe"):
        raise RuntimeError("TRADINGVIEW_TIMEFRAME_NOT_VERIFIED")
    print(f"E2E_TRADINGVIEW=PASS symbol={chart['symbol']} timeframe={chart['timeframe']}")

    integration = VerifiedSignalIntegrationV56(
        api_key=os.getenv("TWELVE_DATA_API_KEY") or os.getenv("TWELVEDATA_API_KEY")
    )
    verified_inputs = integration.read_verified_inputs(outputsize=int(os.getenv("GOLDBOT_CANDLE_OUTPUTSIZE", "100")))
    mtf = verified_inputs["mtf"]
    hns = verified_inputs["hns"]
    if not mtf.get("verified") or not mtf.get("all_required_available"):
        raise RuntimeError(f"MTF_NOT_VERIFIED: {mtf.get('reason')}")
    missing = [tf for tf in REQUIRED_TFS if not (mtf.get("frames", {}).get(tf, {}).get("verified"))]
    if missing:
        raise RuntimeError(f"MTF_MISSING={','.join(missing)}")
    print("E2E_MTF_OHLC=PASS 4h,1h,15m,5m,3m")

    if not hns.get("verified"):
        raise RuntimeError(f"HNS_NOT_VERIFIED: {hns.get('reason')}")
    print(f"E2E_HNS=PASS aligned={hns.get('aligned')} direction={hns.get('direction')}")

    if args.smoke:
        analysis = smoke_analysis("long")
        timing = {"leader_closed": True}
        hns_for_promotion = smoke_hns("long")
        print("E2E_KFOO=SMOKE_FIXTURE")
    else:
        analysis = load_json_env("GOLDBOT_KFOO_ANALYSIS_JSON")
        timing = load_json_env("GOLDBOT_TIMING_JSON") if os.getenv("GOLDBOT_TIMING_JSON") else {}
        hns_for_promotion = hns
        print("E2E_KFOO=LIVE_INPUT")

    sig = promote(analysis, timing=timing, verified_hns_mtf=hns_for_promotion)
    sig_data = sig.to_dict()
    print(f"E2E_SIGNAL=PASS level={sig.level} direction={sig.direction} score={sig.score:.2f} entry_ready={sig.entry_ready}")

    payload = {
        "eventKey": sig.event_key or f"e2e-{sig.level}-{sig.direction}",
        "eventType": sig.level,
        "level": sig.level,
        "direction": sig.direction,
        "confidence": sig.score,
        "score": sig.score,
        "symbol": "XAUUSD",
        "timeframe": chart.get("timeframe", "15m"),
        "gravity": {"4h": "stable", "1h": "stable"},
        "leader": {"15m": sig.direction},
        "timing": timing,
        "kfoo": {"source": "upstream", "live": not args.smoke},
        "head_shoulders": hns,
        "chart_reader": chart,
        "reasons": sig.reasons or [],
        "execution": "OFF",
    }
    try:
        response = post_json(args.webhook, payload)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"WEBHOOK_NOT_REACHABLE: {exc}") from exc
    if response.get("execution") != "OFF":
        raise RuntimeError(f"WEBHOOK_EXECUTION_GUARD_FAILED: {response}")
    if not response.get("ok"):
        raise RuntimeError(f"WEBHOOK_REJECTED: {response}")
    print(f"E2E_WEBHOOK=PASS url={args.webhook}")
    print("E2E_MONITOR_V56=PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"E2E_MONITOR_V56=FAIL {exc}", file=sys.stderr)
        raise SystemExit(1)
