from __future__ import annotations

"""Bridge for an external OCR/vision provider.

The bridge intentionally accepts observations rather than interpreting pixels.
A provider must explicitly return a supported status for each KFOO feature.
Missing provider output remains UNREADABLE/DATA_UNAVAILABLE.
"""

from typing import Mapping

from .kfoo_visual_verifier_v1 import verify_region_observations
from .kfoo_evidence_adapter_v1 import DATA_UNAVAILABLE, UNREADABLE

KFOO_KEYS = (
    "continuity_average",
    "liquidity_table",
    "liquidity_net_positive",
    "ascending_channel",
    "whales_buying",
    "kfoo_arrow",
    "divergence",
    "whale_wave_sync",
)


def normalize_provider_output(provider_output: Mapping[str, Mapping[str, object]] | None) -> dict:
    if provider_output is None:
        return {
            "status": DATA_UNAVAILABLE,
            "source": "external_vision_provider",
            "evidence": [],
            "reason": "VISION_PROVIDER_OUTPUT_UNAVAILABLE",
        }

    observations = {}
    for key in KFOO_KEYS:
        raw = provider_output.get(key)
        if isinstance(raw, Mapping):
            observations[key] = raw
        else:
            observations[key] = {
                "status": UNREADABLE,
                "source": "external_vision_provider",
                "reason": "FEATURE_NOT_RETURNED_BY_PROVIDER",
            }

    return verify_region_observations(observations)
