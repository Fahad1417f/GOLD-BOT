from __future__ import annotations

from pathlib import Path

from PIL import Image

import kfoo_linked_work.vision_live_capture_v2 as v2


class FakePage:
    def evaluate(self, script, arg=None):
        if arg is None:
            return {"w": 1000, "h": 500}
        return [
            {"text": "2,660.0", "x": 1010, "y": 100, "w": 70, "h": 18, "side": "right"},
            {"text": "2,650.0", "x": 1010, "y": 300, "w": 70, "h": 18, "side": "right"},
            {"text": "KFOO", "x": 100, "y": 200, "w": 60, "h": 18, "side": "left"},
        ]


class FakeReader:
    def __init__(self):
        self.page = FakePage()


def test_v2_finds_two_distinct_scale_anchors(tmp_path: Path):
    screenshot = tmp_path / "chart.png"
    Image.new("RGB", (2000, 1000), "black").save(screenshot)

    anchors, diag = v2._read_price_scale_anchors(
        FakeReader(), (100, 50, 900, 450), str(screenshot)
    )

    assert len(anchors) == 2
    assert anchors[0].price == 2660.0
    assert anchors[1].price == 2650.0
    assert anchors[0].y < anchors[1].y
    assert diag["reason"] == "VISIBLE_SCALE_LABEL_PAIRS_FOUND"
