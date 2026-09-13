from pathlib import Path
from PIL import Image, ImageDraw
from kfoo_linked_work.vision_candle_detector_v1 import detect_candles


def _fixture(path: Path):
    im = Image.new("RGB", (500, 300), (20, 20, 20))
    d = ImageDraw.Draw(im)
    for i, x in enumerate([120, 145, 170, 195, 220, 245]):
        top = 100 - (i % 3) * 8
        bottom = 135 + (i % 2) * 7
        d.rectangle((x-5, top, x+5, bottom), fill=(220, 60, 60))
        d.line((x, top-15, x, top), fill=(220, 60, 60), width=1)
        d.line((x, bottom, x, bottom+18), fill=(220, 60, 60), width=1)
    im.save(path)


def test_detects_pixel_candles(tmp_path):
    p = tmp_path / "chart.png"
    _fixture(p)
    r = detect_candles(p)
    assert r.verified
    assert r.reason == "PIXEL_CANDLES_DETECTED"
    assert len(r.candles) >= 3


def test_missing_image_fails_closed(tmp_path):
    r = detect_candles(tmp_path / "missing.png")
    assert not r.verified
    assert r.reason.startswith("IMAGE_READ_FAILED")


def test_horizontal_lines_do_not_weld_the_chart_into_one_candidate(tmp_path):
    p = tmp_path / "chart_with_gridlines.png"
    im = Image.new("RGB", (800, 400), (20, 20, 20))
    d = ImageDraw.Draw(im)

    # Strong horizontal chart/annotation lines across the entire ROI.
    for y in (80, 120, 160, 200, 240, 280, 320):
        d.line((55, y, 745, y), fill=(220, 140, 0), width=1)

    # Three real candle geometries with red bodies and wicks.
    for x, top, bottom in ((150, 110, 165), (190, 125, 178), (230, 95, 150)):
        d.rectangle((x - 5, top, x + 5, bottom), fill=(220, 60, 60))
        d.line((x, top - 12, x, top), fill=(220, 60, 60), width=1)
        d.line((x, bottom, x, bottom + 14), fill=(220, 60, 60), width=1)

    im.save(p)
    r = detect_candles(p)
    assert r.verified
    assert r.reason == "PIXEL_CANDLES_DETECTED"
    assert len(r.candles) >= 3


def test_lower_indicator_and_overlay_box_edges_are_rejected(tmp_path):
    p = tmp_path / "chart_with_indicator_and_labels.png"
    im = Image.new("RGB", (1000, 700), (15, 15, 15))
    d = ImageDraw.Draw(im)

    # Price-pane candles: regular, narrow bodies with a center wick.
    for i, x in enumerate(range(120, 820, 18)):
        body_top = 180 + (i % 7) * 5
        body_bottom = body_top + 18 + (i % 3) * 4
        color = (3, 207, 112) if i % 2 == 0 else (241, 1, 49)
        d.rectangle((x - 4, body_top, x + 4, body_bottom), fill=color)
        d.line((x, body_top - 14, x, body_top), fill=color, width=2)
        d.line((x, body_bottom, x, body_bottom + 12), fill=color, width=2)

    # Lower oscillator pane: deliberately candle-like red/green vertical lines.
    for i, x in enumerate(range(120, 820, 18)):
        y = 560 + (i % 5) * 12
        color = (3, 207, 112) if i % 2 == 0 else (241, 1, 49)
        d.line((x, y, x, y + 24), fill=color, width=3)

    # Annotation boxes: solid colored rectangles should not be mistaken for
    # candles merely because their vertical edges contain long colored runs.
    d.rectangle((280, 90, 370, 125), fill=(255, 0, 85))
    d.rectangle((610, 130, 760, 165), fill=(3, 207, 112))

    im.save(p)
    r = detect_candles(p)
    assert r.verified
    assert len(r.candles) >= 10
    assert all(c.high_y < 500 for c in r.candles)
