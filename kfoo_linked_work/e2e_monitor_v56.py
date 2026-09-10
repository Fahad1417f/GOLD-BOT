from __future__ import annotations

"""V56 end-to-end monitor harness.

Stages:
  TradingView/Playwright identity -> verified MTF OHLC -> verified MTF H&S
  -> live KFOO analysis -> V56 Signal Engine -> local webhook.

The harness is read-only and fail-closed. It never enables or executes trades.
Live KFOO is discovered from the running monitor's local state/output; no
synthetic KFOO is created for a live run. Use --smoke only for a deterministic
contract test.
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


def _valid_kfoo_analysis(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    # Accept either a direct timeframe map or a wrapper containing analysis.
    candidate = value.get("analysis") if isinstance(value.get("analysis"), dict) else value
    if not isinstance(candidate, dict):
        return False
    return all(isinstance(candidate.get(tf), dict) for tf in REQUIRED_TFS)


def _unwrap_kfoo_source(value: dict) -> tuple[dict, dict]:
    if _valid_kfoo_analysis(value):
        candidate = value.get("analysis") if isinstance(value.get("analysis"), dict) else value
        timing = value.get("timing", {}) if isinstance(value.get("timing"), dict) else {}
        return candidate, timing
    for key in ("kfoo_analysis", "kfooAnalysis", "kfoo", "live_kfoo_analysis"):
        candidate = value.get(key)
        if _valid_kfoo_analysis(candidate):
            timing = value.get("timing", {}) if isinstance(value.get("timing"), dict) else {}
            return (candidate.get("analysis") if isinstance(candidate.get("analysis"), dict) else candidate), timing
    raise ValueError("no verified KFOO timeframe analysis in source")


def _candidate_roots() -> list[Path]:
    roots = [ROOT]
    explicit = os.getenv("GOLDBOT_BUILD_PATH", "").strip()
    if explicit:
        roots.append(Path(explicit).expanduser())
    roots.extend(sorted(ROOT.parent.glob("GOLD_BOT_V56*")))
    return list(dict.fromkeys(p.resolve() for p in roots if p.exists()))


def load_live_kfoo() -> tuple[dict, dict, str]:
    # Explicit JSON remains supported for CI/isolated tests, but it is not required.
    raw = os.getenv("GOLDBOT_KFOO_ANALYSIS_JSON", "").strip()
    if raw:
        value = json.loads(raw)
        analysis, timing = _unwrap_kfoo_source(value)
        return analysis, timing, "env:GOLDBOT_KFOO_ANALYSIS_JSON"

    paths: list[Path] = []
    explicit_path = os.getenv("GOLDBOT_KFOO_ANALYSIS_PATH", "").strip()
    if explicit_path:
        paths.append(Path(explicit_path).expanduser())
    names = ("kfoo_live_analysis.json", "kfoo_analysis.json", "live_kfoo_analysis.json", "kfoo_state.json")
    for root in _candidate_roots():
        paths.extend(root / name for name in names)
        paths.extend(root / "v56_build" / name for name in names)

    seen: set[Path] = set()
    errors: list[str] = []
    for path in paths:
        path = path.resolve()
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            analysis, timing = _unwrap_kfoo_source(value)
            return analysis, timing, f"file:{path}"
        except Exception as exc:
            errors.append(f"{path.name}:{type(exc).__name__}")

    # The local website state is a read-only bridge. We only accept it when the
    # full upstream KFOO analysis is actually present; aggregates alone are not
    # promoted into fake samples or directions.
    state_path = ROOT / "website_state.json"
    if state_path.is_file():
        try:
            value = json.loads(state_path.read_text(encoding="utf-8"))
            analysis, timing = _unwrap_kfoo_source(value)
            return analysis, timing, f"file:{state_path}"
        except Exception as exc:
            errors.append(f"website_state.json:{type(exc).__name__}")

    detail = "; ".join(errors[-6:]) if errors else "no candidate KFOO state found"
    raise RuntimeError(
        "LIVE_KFOO_SOURCE_NOT_FOUND: running monitor must publish full verified "
        f"KFOO analysis for {','.join(REQUIRED_TFS)}; {detail}"
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
