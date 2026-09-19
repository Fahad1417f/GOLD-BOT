from __future__ import annotations

import json

import pytest

from kfoo_linked_work.kfoo_region_config_v1 import load_regions


def test_empty_config_is_safe(tmp_path):
    path = tmp_path / "regions.json"
    path.write_text(json.dumps({"regions": []}), encoding="utf-8")
    assert load_regions(path) == ()


def test_valid_region_is_loaded(tmp_path):
    path = tmp_path / "regions.json"
    path.write_text(json.dumps({
        "regions": [{
            "key": "whales_buying",
            "left": 0.1,
            "top": 0.2,
            "right": 0.5,
            "bottom": 0.8
        }]
    }), encoding="utf-8")
    regions = load_regions(path)
    assert len(regions) == 1
    assert regions[0].key == "whales_buying"


def test_unknown_key_is_rejected(tmp_path):
    path = tmp_path / "regions.json"
    path.write_text(json.dumps({
        "regions": [{
            "key": "made_up",
            "left": 0.1,
            "top": 0.1,
            "right": 0.2,
            "bottom": 0.2
        }]
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported_region_key"):
        load_regions(path)


def test_invalid_geometry_is_rejected(tmp_path):
    path = tmp_path / "regions.json"
    path.write_text(json.dumps({
        "regions": [{
            "key": "whales_buying",
            "left": 0.5,
            "top": 0.5,
            "right": 0.2,
            "bottom": 0.8
        }]
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid_normalized_region"):
        load_regions(path)
