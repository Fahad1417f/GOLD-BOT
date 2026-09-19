from __future__ import annotations

from PIL import Image

from kfoo_linked_work.kfoo_evidence_regions_v1 import Region, capture_regions
from kfoo_linked_work.kfoo_evidence_adapter_v1 import DATA_UNAVAILABLE, UNREADABLE


def test_no_regions_fail_closed(tmp_path):
    image = tmp_path / "frame.png"
    Image.new("RGB", (100, 100)).save(image)
    result = capture_regions(image)
    assert result["status"] == UNREADABLE
    assert result["reason"] == "NO_KFOO_REGIONS_CONFIGURED"


def test_configured_region_creates_artifact_but_stays_unreadable(tmp_path):
    image = tmp_path / "frame.png"
    Image.new("RGB", (200, 100)).save(image)
    result = capture_regions(
        image,
        regions=(Region("whales_buying", 0.1, 0.2, 0.5, 0.8),),
        output_dir=tmp_path,
    )
    assert result["status"] == UNREADABLE
    item = result["regions"][0]
    assert item["status"] == UNREADABLE
    assert (tmp_path / "kfoo_regions" / "whales_buying.png").exists()


def test_missing_screenshot_is_data_unavailable(tmp_path):
    result = capture_regions(tmp_path / "missing.png")
    assert result["status"] == DATA_UNAVAILABLE
