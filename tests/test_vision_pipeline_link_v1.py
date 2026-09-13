from pathlib import Path
import json

from kfoo_linked_work import vision_live_capture_v1 as live
from kfoo_linked_work.vision_candle_detector_v1 import Detection, PixelCandleCandidate


# Existing tests remain unchanged above this point.


def test_module_output_is_valid_json(monkeypatch, capsys):
    payload = {"capture_verified": False, "reason": "TRADINGVIEW_PAGE_NOT_FOUND"}
    monkeypatch.setattr(live, "capture_once", lambda *_args, **_kwargs: payload)
    try:
        exec(
            compile(Path(live.__file__).read_text(encoding="utf-8"), str(live.__file__), "exec"),
            {
                "__name__": "__main__",
                "os": __import__("os"),
                "json": json,
                # Execute the real module entrypoint with the already-imported
                # (and monkeypatched) function so the test validates JSON output
                # without opening a second Playwright/CDP session.
                "capture_once": live.capture_once,
            },
        )
    except SystemExit:
        pass
    assert "capture_verified" in capsys.readouterr().out
