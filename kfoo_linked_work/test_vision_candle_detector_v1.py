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
