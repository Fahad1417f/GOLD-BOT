from __future__ import annotations

"""Compatibility bridge from legacy V56 analysis into the unified fail-closed gate.

The existing promote() path is intentionally untouched. Callers that have
explicit KFOO evidence and real entry/stop/target data can opt into this bridge.
"""

from typing import Any, Mapping

from .kfoo_signal_gate_v1 import evaluate_signal


def build_mtf(analysis: Mapping[str, Mapping[str, Any]]) -> dict:
    """Normalize only the documented direction fields; never infer missing data."""
    result: dict[str, dict[str, Any]] = {}
    for tf in ("4h", "1h", "15m", "3m"):
        frame = analysis.get(tf)
        if not isinstance(frame, Mapping):
            continue
        nested = frame.get("analysis")
        if not isinstance(nested, Mapping):
            nested = {}
        direction = (
            frame.get("direction")
            or frame.get("active_kfoo")
            or (nested.get("kfoo_table_direction") or {}).get("bias")
            or nested.get("direction")
        )
        result[tf] = {"direction": direction}
    return result


def evaluate_unified_signal(
    analysis: Mapping[str, Mapping[str, Any]],
    *,
    evidence: Mapping[str, str] | None,
    direction: str,
    entry: object,
    stop: object,
    target: object,
) -> dict:
    """Evaluate the final fail-closed signal without enabling execution."""
    return evaluate_signal(
        evidence,
        build_mtf(analysis),
        direction=direction,
        entry=entry,
        stop=stop,
        target=target,
    )
