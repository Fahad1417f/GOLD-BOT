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


def _read_dom_bridge(page) -> Any:
    """Read an explicitly published KFOO bridge from the live TradingView DOM.

    The bridge is deliberately narrow: it only accepts JSON published by the
    chart page itself under a data attribute or a script tag. It does not OCR,
    infer direction from pixels/colors, or manufacture missing values.
    """
    return page.evaluate(
        r"""() => {
          const nodes = [
            ...document.querySelectorAll('[data-goldbot-kfoo]'),
            ...document.querySelectorAll('script[type="application/json"][data-goldbot-kfoo]')
          ];
          for (const n of nodes) {
            const raw = n.getAttribute('data-goldbot-kfoo') || n.textContent || '';
            if (!raw.trim()) continue;
            try { return JSON.parse(raw); } catch (_) {}
          }
          return null;
        }"""
    )


def read_from_page(page) -> tuple[dict[str, dict], dict[str, Any]]:
    try:
        payload = page.evaluate(f"() => window.{PROVIDER} || null")
    except Exception as exc:
        raise RuntimeError(f"LIVE_KFOO_PROVIDER_READ_FAILED:{type(exc).__name__}:{exc}") from exc

    if payload is not None:
        return validate(payload)

    try:
        payload = _read_dom_bridge(page)
    except Exception as exc:
        raise RuntimeError(f"LIVE_KFOO_DOM_BRIDGE_READ_FAILED:{type(exc).__name__}:{exc}") from exc

    if payload is None:
        raise RuntimeError(
            "LIVE_KFOO_INPUT_NOT_CONFIGURED:"
            "TradingView page exposes neither window.__GOLDBOT_KFOO__ "
            "nor a data-goldbot-kfoo JSON bridge"
        )
    return validate(payload)
