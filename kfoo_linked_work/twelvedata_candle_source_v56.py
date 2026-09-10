from __future__ import annotations

import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from verified_candle_source_v56 import CandleFeed


class TwelveDataCandleSourceV56:
    """Read-only XAU/USD OHLC source for V56.

    Uses Twelve Data's documented time-series endpoint. No TradingView
    navigation, clicks, or execution are involved. Without an API key the
    adapter fails closed.
    """

    BASE_URL = "https://api.twelvedata.com/time_series"
    INTERVALS = {
        "1m": "1min",
        "3m": "3min",
        "5m": "5min",
        "15m": "15min",
        "30m": "30min",
        "45m": "45min",
        "1h": "1h",
        "2h": "2h",
        "4h": "4h",
        "6h": "6h",
        "12h": "12h",
        "1d": "1day",
        "1w": "1week",
    }

    def __init__(self, api_key: str | None = None, timeout: float = 10.0):
        self.api_key = api_key or os.getenv("TWELVEDATA_API_KEY", "")
        self.timeout = timeout

    def read(self, timeframe: str, outputsize: int = 100) -> CandleFeed:
        interval = self.INTERVALS.get(timeframe)
        if not self.api_key:
            return CandleFeed(timeframe=timeframe, reason="TWELVEDATA_API_KEY_NOT_SET")
        if not interval:
            return CandleFeed(timeframe=timeframe, reason="UNSUPPORTED_TIMEFRAME")
        if outputsize < 9:
            return CandleFeed(timeframe=timeframe, reason="OUTPUTSIZE_TOO_SMALL")

        params = urlencode({
            "symbol": "XAU/USD",
            "interval": interval,
            "outputsize": min(int(outputsize), 5000),
            "apikey": self.api_key,
        })
        request = Request(
            f"{self.BASE_URL}?{params}",
            headers={"User-Agent": "GOLD-BOT-V56/1.0"},
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            return CandleFeed(timeframe=timeframe, reason=f"TWELVEDATA_REQUEST_FAILED:{type(exc).__name__}:{exc}")

        if payload.get("status") != "ok":
            return CandleFeed(timeframe=timeframe, reason=f"TWELVEDATA_ERROR:{payload.get('message', 'unknown')}")

        values = payload.get("values")
        if not isinstance(values, list) or len(values) < 9:
            return CandleFeed(timeframe=timeframe, reason="TWELVEDATA_INSUFFICIENT_CANDLES")

        candles = []
        try:
            for row in reversed(values):
                item = {k: float(row[k]) for k in ("open", "high", "low", "close")}
                if row.get("datetime"):
                    item["time"] = row["datetime"]
                candles.append(item)
        except (KeyError, TypeError, ValueError):
            return CandleFeed(timeframe=timeframe, reason="TWELVEDATA_INVALID_OHLC")

        return CandleFeed(
            available=True,
            verified=True,
            source="twelvedata_xau_usd",
            timeframe=timeframe,
            candles=candles,
            reason="VERIFIED_EXTERNAL_CANDLES_READ",
        )


if __name__ == "__main__":
    source = TwelveDataCandleSourceV56()
    result = source.read("15m", outputsize=20)
    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
