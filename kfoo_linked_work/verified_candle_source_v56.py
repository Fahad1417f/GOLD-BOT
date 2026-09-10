from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

try:
    from playwright.sync_api import Page
except Exception:  # pragma: no cover
    Page = Any


@dataclass
class CandleFeed:
    available: bool = False
    verified: bool = False
    source: str = "none"
    timeframe: str | None = None
    candles: list[dict[str, float]] | None = None
    reason: str = ""


class VerifiedCandleSourceV56:
    """Strict read-only candle adapter.

    Accepts OHLC only from an explicitly exposed GoldBot provider. It never
    derives candles from screenshots, visible text, chart pixels, or guessed
    TradingView internals.
    """

    PROVIDER = "__GOLDBOT_CANDLES__"

    def __init__(self, page: Page):
        self.page = page

    def read(self, timeframe: str | None = None) -> CandleFeed:
        try:
            raw = self.page.evaluate(
                """(name) => {
                    const value = window[name];
                    return value || null;
                }""",
                self.PROVIDER,
            )
        except Exception as exc:
            return CandleFeed(reason=f"PROVIDER_READ_FAILED:{type(exc).__name__}:{exc}")

        if not isinstance(raw, list) or len(raw) < 9:
            return CandleFeed(reason="VERIFIED_PROVIDER_UNAVAILABLE")

        out: list[dict[str, float]] = []
        try:
            for row in raw:
                if not isinstance(row, dict):
                    return CandleFeed(reason="INVALID_PROVIDER_ROW")
                item = {k: float(row[k]) for k in ("open", "high", "low", "close")}
                if "time" in row:
                    item["time"] = float(row["time"])
                out.append(item)
        except (KeyError, TypeError, ValueError):
            return CandleFeed(reason="INVALID_PROVIDER_OHLC")

        return CandleFeed(
            available=True,
            verified=True,
            source="goldbot_verified_provider",
            timeframe=timeframe,
            candles=out,
            reason="VERIFIED_CANDLES_READ",
        )


def provider_contract() -> dict[str, object]:
    return {
        "provider": VerifiedCandleSourceV56.PROVIDER,
        "minimum_candles": 9,
        "required_fields": ["open", "high", "low", "close"],
        "optional_fields": ["time"],
        "screenshot_inference": False,
        "chart_dom_inference": False,
        "execution": False,
    }


if __name__ == "__main__":
    print(json.dumps(provider_contract(), ensure_ascii=False, indent=2))
