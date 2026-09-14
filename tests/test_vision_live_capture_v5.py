from __future__ import annotations

from PIL import Image

from kfoo_linked_work import vision_live_capture_v5 as v5


class _Page:
    def evaluate(self, script, *args):
        return {"w": 1000, "h": 500}


class _Reader:
    page = _Page()


def test_ocr_scale_uses_screenshot_pixel_coordinates(monkeypatch, tmp_path):
    shot = tmp_path / "chart.png"
    Image.new("RGB", (2000, 1000), "black").save(shot)

    monkeypatch.setattr(v5.shutil, "which", lambda name: "tesseract")

    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t1\t1\t1\t1\t10\t100\t80\t20\t95\t4305.0\n"
        "5\t1\t1\t1\t2\t1\t10\t300\t80\t20\t95\t4300.0\n"
    )

    class _Proc:
        stdout = tsv

    monkeypatch.setattr(v5.subprocess, "run", lambda *args, **kwargs: _Proc())

    anchors, diag = v5._ocr_scale_anchors(_Reader(), str(shot), (100, 50, 900, 450))

    assert len(anchors) == 2
    # Viewport is 1000x500 while screenshot is 2000x1000, so OCR y is
    # mapped from the 2x enlarged crop back into screenshot coordinates.
    assert round(anchors[0].y, 2) == 160.0
    assert round(anchors[1].y, 2) == 260.0
    assert anchors[0].price == 4305.0
    assert anchors[1].price == 4300.0
    assert diag["reason"] == "OCR_SCALE_ANCHORS_FOUND"
