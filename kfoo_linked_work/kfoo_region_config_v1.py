from __future__ import annotations

"""Load explicitly configured KFOO screenshot regions.

No coordinates are inferred. A region only becomes active when a user/operator
supplies valid normalized coordinates in JSON.
"""

import json
from pathlib import Path

from .kfoo_evidence_regions_v1 import Region


REGION_KEYS = (
    "continuity_average",
    "liquidity_table",
    "liquidity_net_positive",
    "ascending_channel",
    "whales_buying",
    "kfoo_arrow",
    "divergence",
    "whale_wave_sync",
)


def load_regions(path: str | Path | None) -> tuple[Region, ...]:
    if not path:
        return ()

    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(str(source))

    payload = json.loads(source.read_text(encoding="utf-8"))
    raw_regions = payload.get("regions", payload) if isinstance(payload, dict) else payload
    if not isinstance(raw_regions, list):
        raise ValueError("regions_must_be_a_list")

    regions: list[Region] = []
    seen: set[str] = set()
    for raw in raw_regions:
        if not isinstance(raw, dict):
            raise ValueError("region_entry_must_be_object")
        key = str(raw.get("key", "")).strip()
        if key not in REGION_KEYS:
            raise ValueError(f"unsupported_region_key:{key}")
        if key in seen:
            raise ValueError(f"duplicate_region_key:{key}")
        region = Region(
            key=key,
            left=float(raw["left"]),
            top=float(raw["top"]),
            right=float(raw["right"]),
            bottom=float(raw["bottom"]),
        )
        region.validate()
        seen.add(key)
        regions.append(region)

    return tuple(regions)
