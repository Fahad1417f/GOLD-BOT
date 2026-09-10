from __future__ import annotations

# Executed as a script from kfoo_linked_work: explicitly add repository root
# so both signal-engine implementations are importable on Windows/Python.
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from signal_engine_v56 import promote as linked_promote
from v56_signal_monitor.signal_engine_v56 import promote as monitor_promote


def _analysis(direction: str = "long") -> dict:
    def frame(samples=None, detected=True, bias=direction):
        return {
            "samples": samples or [{"active_kfoo": bias}] * 3,
            "active_kfoo": bias,
            "analysis": {
                "direction": bias,
                "kfoo_table_detected": detected,
                "kfoo_table_direction": {"bias": bias},
                "kfoo_table": {
                    "aggregates": {
                        "timeframes": {"bullish_pct": 75.0, "bearish_pct": 25.0},
                        "indicators": {"bullish_pct": 80.0, "bearish_pct": 20.0},
                    },
                    "timeframes": {"15m": {"signal": bias}},
                },
            },
        }
    return {"4h": frame(), "1h": frame(), "15m": frame(), "5m": frame(), "3m": frame()}


def _hns(direction: str, *, aligned: bool = True, verified: bool = True) -> dict:
    return {
        "verified": verified,
        "aligned": aligned,
        "direction": direction,
        "frames": {
            "4h": {"verified": verified, "detected": True, "confirmed": aligned},
            "1h": {"verified": verified, "detected": True, "confirmed": aligned},
            "15m": {"verified": verified, "detected": True, "confirmed": aligned},
        },
    }


def _assert_blocked(fn):
    sig = fn(_analysis("long"), {"leader_closed": True}, _hns("short"))
    assert sig.level == "WAIT"
    assert sig.entry_ready is False
    assert any("conflicts" in r for r in (sig.reasons or []))


def _assert_aligned(fn):
    sig = fn(_analysis("long"), {"leader_closed": True}, _hns("long"))
    assert sig.level == "STRONG_ENTRY"
    assert sig.direction == "long"
    assert sig.entry_ready is True
    assert any("H&S confirmed and aligned" in r for r in (sig.reasons or []))


def main() -> None:
    _assert_blocked(linked_promote)
    _assert_aligned(linked_promote)
    _assert_blocked(monitor_promote)
    _assert_aligned(monitor_promote)
    print("VERIFIED_SIGNAL_INTEGRATION_TEST=PASS")


if __name__ == "__main__":
    main()
