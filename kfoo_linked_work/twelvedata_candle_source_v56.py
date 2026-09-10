from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from verified_candle_source_v56 import CandleFeed


class TwelveDataCandleSourceV56:
    """Read-only XAU/USD OHLC source for V56.

    Twelve Data documents 1min/5min/15min/etc. intervals but not 3min.
    Therefore V56 obtains verified 1-minute XAU/USD candles and deterministically
    aggregates contiguous 3-minute buckets locally. No screenshot-derived or
    guessed candles are accepted.
    """

    BASE_URL = "https://api.twelvedata.com/time_series"
    INTERVALS = {
        "1m": "1min",
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

    def _request(self, interval: str, outputsize: int) -> tuple[dict | None, str | None]:
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
            return None, f"TWELVEDATA_REQUEST_FAILED:{type(exc).__name__}:{exc}"
        if payload.get("status") != "ok":
            return None, f"TWELVEDATA_ERROR:{payload.get('message', 'unknown')}"
        return payload, None

    @staticmethod
    def _rows_to_candles(values: list[dict]) -> list[dict] | None:
        candles = []
        try:
            for row in reversed(values):
                item = {k: float(row[k]) for k in ("open", "high", "low", "close")}
                if row.get("datetime"):
                    item["time"] = row["datetime"]
                candles.append(item)
        except (KeyError, TypeError, ValueError):
            return None
        return candles

    @staticmethod
    def _aggregate_3m(candles_1m: list[dict], outputsize: int) -> list[dict] | None:
        """Aggregate only complete, contiguous 1-minute buckets into 3m OHLC."""
        parsed = []
        try:
            for c in candles_1m:
                if not c.get("time"):
                    return None
                dt = datetime.fromisoformat(c["time"].replace("Z", "+00:00"))
                parsed.append((dt, c))
        except (TypeError, ValueError):
            return None

        parsed.sort(key=lambda x: x[0])
        buckets: dict[datetime, list[tuple[datetime, dict]]] = {}
        for dt, candle in parsed:
            bucket = dt.replace(minute=(dt.minute // 3) * 3, second=0, microsecond=0)
            buckets.setdefault(bucket, []).append((dt, candle))

        result = []
        for bucket in sorted(buckets):
            rows = buckets[bucket]
            if len(rows) != 3:
                continue
            times = [dt for dt, _ in rows]
            if any(times[i + 1] - times[i] != timedelta(minutes=1) for i in range(2)):
                continue
            vals = [c for _, c in rows]
            result.append({
                "open": vals[0]["open"],
                "high": max(c["high"] for c in vals),
                "low": min(c["low"] for c in vals),
                "close": vals[-1]["close"],
                "time": bucket.isoformat(),
            })
        return result[-max(9, int(outputsize)):]

    def read(self, timeframe: str, outputsize: int = 100) -> CandleFeed:
        if not self.api_key:
            return CandleFeed(timeframe=timeframe, reason="TWELVEDATA_API_KEY_NOT_SET")
        if outputsize < 9:
            return CandleFeed(timeframe=timeframe, reason="OUTPUTSIZE_TOO_SMALL")

        if timeframe == "3m":
            payload, error = self._request("1min", min(5000, max(27, int(outputsize) * 4)))
            if error:
                return CandleFeed(timeframe=timeframe, reason=error)
            values = payload.get("values") if payload else None
            if not isinstance(values, list) or len(values) < 9:
                return CandleFeed(timeframe=timeframe, reason="TWELVEDATA_INSUFFICIENT_CANDLES")
            candles_1m = self._rows_to_candles(values)
            if candles_1m is None:
                return CandleFeed(timeframe=timeframe, reason="TWELVEDATA_INVALID_OHLC")
            candles = self._aggregate_3m(candles_1m, outputsize)
            if candles is None or len(candles) < 9:
                return CandleFeed(timeframe=timeframe, reason="TWELVEDATA_3M_AGGREGATION_INSUFFICIENT_COMPLETE_BUCKETS")
            return CandleFeed(
                available=True,
                verified=True,
                source="twelvedata_xau_usd_1m_aggregated_3m",
                timeframe=timeframe,
                candles=candles,
                reason="VERIFIED_EXTERNAL_1M_AGGREGATED_3M",
            )

        interval = self.INTERVALS.get(timeframe)
        if not interval:
            return CandleFeed(timeframe=timeframe, reason="UNSUPPORTED_TIMEFRAME")
        payload, error = self._request(interval, outputsize)
        if error:
            return CandleFeed(timeframe=timeframe, reason=error)
        values = payload.get("values") if payload else None
        if not isinstance(values, list) or len(values) < 9:
            return CandleFeed(timeframe=timeframe, reason="TWELVEDATA_INSUFFICIENT_CANDLES")
        candles = self._rows_to_candles(values)
        if candles is None:
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
