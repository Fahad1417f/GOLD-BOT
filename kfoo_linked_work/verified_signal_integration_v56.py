from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from signal_engine_v56 import Signal, promote
from verified_hns_mtf_v56 import VerifiedHNSMTFV56
from verified_mtf_candle_pipeline_v56 import VerifiedMTFCandlePipelineV56


class VerifiedSignalIntegrationV56:
    """Read-only bridge from verified market inputs to the V56 signal engine."""

    def __init__(self, api_key: str | None = None, timeout: float = 10.0) -> None:
        self.mtf = VerifiedMTFCandlePipelineV56(api_key=api_key, timeout=timeout)
        self.hns = VerifiedHNSMTFV56(api_key=api_key, timeout=timeout)

    def read_verified_inputs(self, outputsize: int = 100) -> dict[str, Any]:
        mtf = self.mtf.read(outputsize=outputsize)
        hns = self.hns.read(outputsize=outputsize)
        return {"mtf": mtf.to_dict(), "hns": hns.to_dict()}

    def promote(
        self,
        analysis: dict[str, dict],
        timing: dict[str, Any] | None = None,
        outputsize: int = 100,
    ) -> tuple[Signal, dict[str, Any]]:
        inputs = self.read_verified_inputs(outputsize=outputsize)
        signal = promote(
            analysis,
            timing=timing,
            verified_hns_mtf=inputs["hns"],
        )
        return signal, inputs


def main() -> None:
    result = VerifiedSignalIntegrationV56().read_verified_inputs(outputsize=100)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
