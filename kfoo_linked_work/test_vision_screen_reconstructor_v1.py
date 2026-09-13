from kfoo_linked_work.vision_screen_reconstructor_v1 import PixelCandle, ScaleAnchor, VisionScreenReconstructorV1

def candle(i=0):
    return PixelCandle(i,50,20,10,15,15,20,"bullish",0.98)

def test_requires_two_scale_anchors():
    r=VisionScreenReconstructorV1().map_ohlc([candle()], [ScaleAnchor(10,2000)])
    assert not r.verified
    assert r.reason=="TWO_DISTINCT_SCALE_ANCHORS_REQUIRED"

def test_maps_pixel_y_to_price():
    r=VisionScreenReconstructorV1().map_ohlc(
        [candle()], [ScaleAnchor(10,2000),ScaleAnchor(110,1900)]
    )
    assert r.verified
    assert r.reason=="VERIFIED_PIXEL_TO_OHLC"
    assert r.ohlc[0]["high"]==2000.0
    assert r.ohlc[0]["low"]==1900.0

def test_rejects_bad_geometry():
    bad=PixelCandle(0,50,20,10,25,25,20,"bullish",0.98)
    r=VisionScreenReconstructorV1().map_ohlc(
        [bad],[ScaleAnchor(10,2000),ScaleAnchor(110,1900)]
    )
    assert not r.verified
    assert r.reason=="INVALID_CANDLE_GEOMETRY"
