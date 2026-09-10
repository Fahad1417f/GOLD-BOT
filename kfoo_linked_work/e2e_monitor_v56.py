from __future__ import annotations

"""V56 end-to-end monitor harness.

Stages:
  TradingView/Playwright identity -> verified MTF OHLC -> verified MTF H&S
  -> live KFOO analysis -> V56 Signal Engine -> local webhook.

The harness is read-only and fail-closed. It never enables or executes trades.
Live KFOO is read from the actual V56 monitor log markers through the
live_kfoo_source_v56 adapter; no synthetic KFOO is created for a live run.
Use --smoke only for a deterministic contract test.
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

from live_kfoo_source_v56 import parse_live_kfoo  # noqa: E402
from playwright_chart_reader import PlaywrightChartReader  # noqa: E402
from verified_signal_integration_v56 import VerifiedSignalIntegrationV56  # noqa: E402
from signal_engine_v56 import promote  # noqa: E402

REQUIRED_TFS = ("4h", "1h", "15m", "5m", "3m")


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


def load_live_kfoo() -> tuple[dict, dict, str]:
    raw = os.getenv("GOLDBOT_KFOO_ANALYSIS_JSON", "").strip()
    if raw:
        from_payload = json.loads(raw)
        if not isinstance(from_payload, dict):
            raise RuntimeError("GOLDBOT_KFOO_ANALYSIS_JSON must contain a JSON object")
        candidate = from_payload.get("analysis") if isinstance(from_payload.get("analysis"), dict) else from_payload
        if not all(isinstance(candidate.get(tf), dict) for tf in REQUIRED_TFS):
            raise RuntimeError("GOLDBOT_KFOO_ANALYSIS_JSON missing required timeframe objects")
        timing = from_payload.get("timing", {}) if isinstance(from_payload.get("timing"), dict) else {}
        return candidate, timing, "env:GOLDBOT_KFOO_ANALYSIS_JSON"

    log_path = Path(os.getenv("GOLDBOT_MONITOR_LOG", ROOT / "v56_monitor.log")).expanduser()
    build_path = os.getenv("GOLDBOT_BUILD_PATH", "").strip()
    candidates = [log_path]
    if build_path:
        candidates.append(Path(build_path) / "v56_monitor.log")
    candidates.extend(sorted(ROOT.parent.glob("GOLD_BOT_V56*/v56_monitor.log")))

    errors: list[str] = []
    seen: set[Path] = set()
    for path in candidates:
        path = path.resolve()
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
            analysis, timing = parse_live_kfoo(text)
            return analysis, timing, f"log:{path}"
        except Exception as exc:
            errors.append(f"{path}:{type(exc).__name__}:{exc}")

    # Keep the existing state-file fallback, but only for a complete normalized
    # KFOO object. Scalar website aggregates must never be promoted to fake input.
    for path in (ROOT / "website_state.json",):
        if not path.is_file():
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            candidate = value.get("analysis") if isinstance(value, dict) and isinstance(value.get("analysis"), dict) else value
            if isinstance(candidate, dict) and all(isinstance(candidate.get(tf), dict) for tf in REQUIRED_TFS):
                timing = value.get("timing", {}) if isinstance(value.get("timing"), dict) else {}
                return candidate, timing, f"file:{path}"
        except Exception as exc:
            errors.append(f"{path.name}:{type(exc).__name__}:{exc}")

    detail = "; ".join(errors[-6:]) if errors else "no monitor log found"
    raise RuntimeError(
        "LIVE_KFOO_SOURCE_NOT_FOUND: running monitor must publish verified KFOO "
        f"markers for {','.join(REQUIRED_TFS)}; {detail}"
    )


def assert_execution_off() -> None:
    for key in ("GOLDBOT_REAL_TRADING", "GOLDBOT_DEMO_TRADING", "GOLDBOT_FAST_TRADE"):
        if os.getenv(key, "").strip().lower() in {"1", "true", "yes", "on"}:
            raise RuntimeError(f"FAIL_CLOSED_EXECUTION_FLAG={key}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="deterministic downstream contract test")
    parser.add_argument("--webhook", default=os.getenv("GOLDBOT_WEBHOOK_URL", "http://127.0.0.1:3000/api/webhooks/tradingview"))
    args = parser.parse_args()

    assert_execution_off()
    print("E2E_EXECUTION=OFF")

    reader = PlaywrightChartReader()
    chart_obj = reader.connect()
    chart = chart_obj.to_dict()
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
    missing = [tf for tf in REQUIRED_TFS if not mtf.get("frames", {}).get(tf, {}).get("verified")]
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
        analysis, timing, source = load_live_kfoo()
        hns_for_promotion = hns
        print(f"E2E_KFOO=LIVE_SOURCE {source}")

    sig = promote(analysis, timing=timing, verified_hns_mtf=hns_for_promotion)
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
        "kfoo": {"source": "live_upstream" if not args.smoke else "smoke_fixture", "live": not args.smoke},
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
