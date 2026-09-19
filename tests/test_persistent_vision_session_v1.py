from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import kfoo_linked_work.vision_live_capture_v1 as live


class _FakeReader:
    def __init__(self, *args, **kwargs):
        self.page = object()
        self.closed = False

    def connect(self):
        return SimpleNamespace(
            connected=True,
            symbol="BTCUSDT.P",
            timeframe="3m",
            reason="IDENTITY_VERIFIED",
            to_dict=lambda: {
                "connected": True,
                "symbol": "BTCUSDT.P",
                "timeframe": "3m",
                "reason": "IDENTITY_VERIFIED",
            },
        )

    def read(self):
        return SimpleNamespace(
            connected=True,
            symbol="BTCUSDT.P",
            timeframe="3m",
            reason="IDENTITY_VERIFIED",
            screenshot_path=None,
            plot_rect=None,
            to_dict=lambda: {
                "connected": True,
                "symbol": "BTCUSDT.P",
                "timeframe": "3m",
                "reason": "IDENTITY_VERIFIED",
            },
        )

    def close(self):
        self.closed = True
        self.page = None


def test_persistent_session_keeps_reader_until_close(tmp_path, monkeypatch):
    reader = _FakeReader()
    monkeypatch.setattr(live, "PlaywrightChartReader", lambda *a, **k: reader)

    def fake_capture(_reader, _output_dir, sequence):
        return {
            "connected": True,
            "capture_verified": True,
            "symbol": "BTCUSDT.P",
            "timeframe": "3m",
            "reason": "IDENTITY_VERIFIED",
            "screenshot_path": str(tmp_path / f"{sequence}.png"),
            "captured_at": f"2026-09-19T17:00:0{sequence}Z",
            "frame_sha256": f"hash-{sequence}",
        }

    monkeypatch.setattr(live, "_capture_with_reader", fake_capture)

    session = live.PersistentVisionSession(output_dir=str(tmp_path))
    first = session.connect()
    assert first["connected"] is True
    assert session.reader is reader

    second = session.capture()
    third = session.capture()

    assert second["capture_sequence"] == 1
    assert third["capture_sequence"] == 2
    assert second["frame_changed"] is True
    assert third["frame_changed"] is True
    assert session.reader is reader

    heartbeat = json.loads((tmp_path / "vision_heartbeat.json").read_text(encoding="utf-8"))
    assert heartbeat["status"] == "RUNNING"
    assert heartbeat["connected"] is True
    assert heartbeat["capture_sequence"] == 2
    assert heartbeat["execution"] == "OFF"

    session.close()
    assert reader.closed is True


def test_persistent_session_fails_closed_on_capture_error(tmp_path, monkeypatch):
    reader = _FakeReader()
    monkeypatch.setattr(live, "PlaywrightChartReader", lambda *a, **k: reader)
    monkeypatch.setattr(
        live,
        "_capture_with_reader",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    session = live.PersistentVisionSession(output_dir=str(tmp_path))
    assert session.connect()["connected"] is True

    data = session.capture()

    assert data["status"] == "DATA_UNAVAILABLE"
    assert data["capture_verified"] is False
    assert data["connected"] is False
    assert "CAPTURE_FAILED:RuntimeError:boom" in data["reason"]

    heartbeat = json.loads((tmp_path / "vision_heartbeat.json").read_text(encoding="utf-8"))
    assert heartbeat["status"] == "DATA_UNAVAILABLE"
    assert heartbeat["connected"] is False
    assert heartbeat["consecutive_failures"] == 1


def test_loop_cli_is_available(monkeypatch, tmp_path):
    seen = {}

    class Session:
        def __init__(self, **kwargs):
            seen.update(kwargs)

        def run(self, interval):
            seen["interval"] = interval
            return 0

    monkeypatch.setattr(live, "PersistentVisionSession", Session)

    rc = live.main([
        "--loop",
        "--interval", "15",
        "--output-dir", str(tmp_path),
        "--heartbeat", str(tmp_path / "heartbeat.json"),
    ])

    assert rc == 0
    assert seen["interval"] == 15.0
    assert seen["output_dir"] == str(tmp_path)
    assert seen["heartbeat_path"] == str(tmp_path / "heartbeat.json")
