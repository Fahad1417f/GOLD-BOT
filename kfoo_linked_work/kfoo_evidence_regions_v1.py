from __future__ import annotations

"""Fail-closed KFOO visual region evidence.

Regions are configuration, not claims about the KFOO layout. Until a region is
explicitly configured and OCR/semantic verification is available, its evidence
remains UNREADABLE.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .kfoo_evidence_adapter_v1 import DATA_UNAVAILABLE, UNREADABLE


@dataclass(frozen=True)
class Region:
    key: str
    left: float
    top: float
    right: float
    bottom: float

    def validate(self) -> None:
        values = (self.left, self.top, self.right, self.bottom)
        if any(v < 0 or v > 1 for v in values) or self.right <= self.left or self.bottom <= self.top:
            raise ValueError(f"invalid_normalized_region:{self.key}")


DEFAULT_REGIONS: tuple[Region, ...] = ()


def capture_regions(
    screenshot_path: str | Path | None,
    *,
    regions: tuple[Region, ...] = DEFAULT_REGIONS,
    output_dir: str | Path | None = None,
) -> dict:
    if not screenshot_path:
        return {"status": DATA_UNAVAILABLE, "reason": "SCREENSHOT_UNAVAILABLE", "regions": []}

    source = Path(screenshot_path)
    if not source.exists():
        return {"status": DATA_UNAVAILABLE, "reason": "SCREENSHOT_NOT_FOUND", "regions": []}

    if not regions:
        return {
            "status": UNREADABLE,
            "reason": "NO_KFOO_REGIONS_CONFIGURED",
            "regions": [],
        }

    for region in regions:
        region.validate()

    try:
        from PIL import Image
    except Exception:
        return {"status": UNREADABLE, "reason": "PIL_NOT_AVAILABLE", "regions": []}

    target_dir = Path(output_dir or source.parent) / "kfoo_regions"
    target_dir.mkdir(parents=True, exist_ok=True)

    with Image.open(source) as image:
        width, height = image.size
        artifacts = []
        for region in regions:
            box = (
                round(region.left * width),
                round(region.top * height),
                round(region.right * width),
                round(region.bottom * height),
            )
            target = target_dir / f"{region.key}.png"
            image.crop(box).save(target)
            artifacts.append({
                "key": region.key,
                "status": UNREADABLE,
                "reason": "REGION_CAPTURED_BUT_NOT_SEMANTICALLY_VERIFIED",
                "path": str(target),
                "box_px": list(box),
            })

    return {
        "status": UNREADABLE,
        "reason": "REGION_ARTIFACTS_READY_FOR_VERIFICATION",
        "regions": artifacts,
    }
