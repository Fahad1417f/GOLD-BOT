from __future__ import annotations

import json
from typing import Any

from signal_engine_v56 import Signal, promote
from verified_hns_mtf_v56 import VerifiedHNSMTFV56
from verified_mtf_candle_pipeline_v56 import VerifiedMTFCandlePipelineV56


class VerifiedSignalIntegrationV56:
    """Read-only integration between verified OHLC/MTF H&S and V56 promotion.

    KFOO/TradingView analysis remains an upstream input. This class deliberately
    does not invent KFOO values or candles; it only wires verified market data
    into the signal engine and preserves fail-closed behavior.
    """

    def __init__(self, api_key: str | None = None, timeout: float = 10.0):
        self.mtf = VerifiedMTFCandlePipelineV56(api_key=api_key, timeout=timeout)
        self.hns = VerifiedHNSMTFV56(api_key=api_key, timeout=timeout)

    def read_verified_inputs(self, outputsize: int = 100) -> dict[str, Any]:
        # One Twelve Data MTF fetch per monitor cycle. H&S consumes the exact
        # verified candles already read instead of issuing a duplicate batch.
        mtf = self.mtf.read(outputsize=outputsize)
        hns = self.hns.read(outputsize=outputsize, mtf=mtf)
        return {"mtf": mtf.to_dict(), "hns": hns.to_dict()}

    def promote(self, analysis: dict[str, dict], timing: dict[str, Any] | None = None,
                outputsize: int = 100) -> tuple[Signal, dict[str, Any]]:
        inputs = self.read_verified_inputs(outputsize=outputsize)
        sig = promote(analysis, timing=timing, verified_hns_mtf=inputs["hns"])
        return sig, inputs


def main() -> None:
    result = VerifiedSignalIntegrationV56().read_verified_inputs(outputsize=100)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
