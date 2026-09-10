from __future__ import annotations

from typing import Any

PROVIDER = "__GOLDBOT_KFOO__"
REQUIRED_TFS = ("4h", "1h", "15m", "5m", "3m")


def normalize_direction(value: Any) -> str | None:
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"long", "bullish", "buy"}:
            return "long"
        if v in {"short", "bearish", "sell"}:
            return "short"
    return None


def validate(payload: Any) -> tuple[dict[str, dict], dict[str, Any]]:
    if not isinstance(payload, dict):
        raise RuntimeError("LIVE_KFOO_PROVIDER_INVALID:not_object")

    analysis = payload.get("analysis")
    timing = payload.get("timing") or {}
    if not isinstance(analysis, dict):
        raise RuntimeError("LIVE_KFOO_PROVIDER_INVALID:analysis_missing")
    if not isinstance(timing, dict):
        raise RuntimeError("LIVE_KFOO_PROVIDER_INVALID:timing_not_object")

    missing = [tf for tf in REQUIRED_TFS if not isinstance(analysis.get(tf), dict)]
    if missing:
        raise RuntimeError("LIVE_KFOO_PROVIDER_INCOMPLETE:" + ",".join(missing))

    for tf in REQUIRED_TFS:
        frame = analysis[tf]
        info = frame.get("analysis")
        if not isinstance(info, dict):
            raise RuntimeError(f"LIVE_KFOO_PROVIDER_INVALID:{tf}:analysis_missing")
        if not bool(info.get("kfoo_table_detected")):
            raise RuntimeError(f"LIVE_KFOO_PROVIDER_INVALID:{tf}:table_not_verified")
        direction = (
            normalize_direction(frame.get("active_kfoo"))
            or normalize_direction(info.get("direction"))
            or normalize_direction((info.get("kfoo_table_direction") or {}).get("bias"))
        )
        if direction is None:
            raise RuntimeError(f"LIVE_KFOO_PROVIDER_INVALID:{tf}:direction_missing")

        table = info.get("kfoo_table") or {}
        aggs = table.get("aggregates") or {}
        tfagg = aggs.get("timeframes") or {}
        indagg = aggs.get("indicators") or {}
        for name, agg in (("timeframes", tfagg), ("indicators", indagg)):
            if not isinstance(agg, dict):
                raise RuntimeError(f"LIVE_KFOO_PROVIDER_INVALID:{tf}:{name}_aggregate_missing")
            for key in ("bullish_pct", "bearish_pct"):
                try:
                    value = float(agg[key])
                except Exception as exc:
                    raise RuntimeError(f"LIVE_KFOO_PROVIDER_INVALID:{tf}:{name}:{key}") from exc
                if not 0.0 <= value <= 100.0:
                    raise RuntimeError(f"LIVE_KFOO_PROVIDER_INVALID:{tf}:{name}:{key}_range")

    return analysis, timing


def read_from_page(page) -> tuple[dict[str, dict], dict[str, Any]]:
    try:
        payload = page.evaluate(f"() => window.{PROVIDER} || null")
    except Exception as exc:
        raise RuntimeError(f"LIVE_KFOO_PROVIDER_READ_FAILED:{type(exc).__name__}:{exc}") from exc
    return validate(payload)
