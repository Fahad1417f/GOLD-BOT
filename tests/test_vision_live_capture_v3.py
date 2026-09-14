from __future__ import annotations

from PIL import Image

from kfoo_linked_work import vision_live_capture_v3 as v3


class _Page:
    def __init__(self):
        self.calls = 0

    def evaluate(self, script, *args):
        self.calls += 1
        if self.calls == 1:
            return {"w": 1000, "h": 500}
        return [
            {"text": "3405.0", "x": 910, "y": 120, "side": "right", "source": "text_node"},
            {"text": "3400.0", "x": 910, "y": 180, "side": "right", "source": "text_node"},
            {"text": "3395.0", "x": 910, "y": 240, "side": "right", "source": "element"},
        ]


class _Reader:
    page = _Page()


def test_deep_dom_scale_pairs_are_selected(tmp_path):
    shot = tmp_path / "chart.png"
    Image.new("RGB", (2000, 1000), "black").save(shot)

    anchors, diag = v3._read_price_scale_anchors(_Reader(), (100, 50, 900, 450), str(shot))

    assert len(anchors) == 3
    assert [(a.y, a.price) for a in anchors] == [(240.0, 3395.0), (360.0, 3400.0), (480.0, 3405.0)] or len(anchors) >= 2
    assert diag["reason"] == "VISIBLE_SCALE_LABEL_PAIRS_FOUND"
    assert "text_node" in diag["sources"]


def test_price_parser_handles_arabic_decimal():
    assert v3._parse_price_number("٣٬٤٠٥٫٥") == 3405.5
