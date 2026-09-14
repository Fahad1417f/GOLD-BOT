from pathlib import Path
from PIL import Image, ImageDraw

from kfoo_linked_work.vision_candle_detector_v1 import detect_candles


def test_tradingview_like_overlays_do_not_block_candle_detection(tmp_path: Path):
    p = tmp_path / "tv_like.png"
    im = Image.new("RGB", (900, 500), (15, 15, 15))
    d = ImageDraw.Draw(im)

    # Grid/annotation lines resembling the supplied TradingView screenshot.
    for y in (70, 110, 150, 190, 230, 270, 310, 350):
        d.line((20, y, 850, y), fill=(205, 135, 15), width=1)
    d.line((50, 40, 500, 300), fill=(170, 170, 170), width=1)
    d.line((80, 320, 600, 180), fill=(240, 140, 0), width=2)

    # A run of candle bodies/wicks with TradingView-like red/green colors.
    candles = [
        (180, 95, 145, (235, 35, 70)),
        (195, 105, 160, (0, 205, 120)),
        (210, 100, 155, (235, 35, 70)),
        (225, 115, 175, (0, 205, 120)),
        (240, 90, 140, (235, 35, 70)),
    ]
    for x, top, bottom, fill in candles:
        d.rectangle((x - 5, top, x + 5, bottom), fill=fill)
        d.line((x, top - 12, x, top), fill=fill, width=1)
        d.line((x, bottom, x, bottom + 15), fill=fill, width=1)

    im.save(p)
    result = detect_candles(p)
    assert result.verified
    assert result.reason == "PIXEL_CANDLES_DETECTED"
    assert len(result.candles) >= 3
