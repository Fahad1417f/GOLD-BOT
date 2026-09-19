from __future__ import annotations

"""Fail-closed semantic verifier for captured KFOO regions.

This layer deliberately does not perform OCR itself. It accepts OCR/vision
observations from a trusted adapter and normalizes them into the same KFOO
evidence states. An image crop by itself is never treated as proof.
"""

from dataclasses import dataclass
from typing import Mapping

from .kfoo_evidence_adapter_v1 import (
    ABSENT,
    DATA_UNAVAILABLE,
    PRESENT,
    UNREADABLE,
)


@dataclass(frozen=True)
class RegionObservation:
    key: str
    status: str
    matched_text: str | None = None
    confidence: float | None = None
    source: str = "external_vision_adapter"
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "status": self.status,
            "matched_text": self.matched_text,
            "confidence": self.confidence,
            "source": self.source,
            "reason": self.reason,
        }


def verify_region_observations(
    observations: Mapping[str, Mapping[str, object]] | None,
) -> dict:
    """Normalize trusted visual observations without inventing missing evidence."""
    if observations is None:
        return {
            "status": DATA_UNAVAILABLE,
            "source": "external_vision_adapter",
            "evidence": [],
            "reason": "NO_VISUAL_OBSERVATIONS",
        }

    evidence: list[dict] = []
    for key, raw in observations.items():
        if not isinstance(raw, Mapping):
            evidence.append(RegionObservation(
                key=key,
                status=UNREADABLE,
                reason="INVALID_OBSERVATION",
            ).to_dict())
            continue

        status = str(raw.get("status", UNREADABLE)).upper()
        if status not in {PRESENT, ABSENT, UNREADABLE, DATA_UNAVAILABLE}:
            status = UNREADABLE

        confidence = raw.get("confidence")
        if confidence is not None:
            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                confidence = None

        # Confidence is metadata only. It never upgrades UNREADABLE/ABSENT.
        evidence.append(RegionObservation(
            key=key,
            status=status,
            matched_text=str(raw["matched_text"]) if raw.get("matched_text") is not None else None,
            confidence=confidence,
            source=str(raw.get("source", "external_vision_adapter")),
            reason=str(raw.get("reason", "")),
        ).to_dict())

    if not evidence:
        overall = DATA_UNAVAILABLE
    elif any(item["status"] == DATA_UNAVAILABLE for item in evidence):
        overall = DATA_UNAVAILABLE
    elif any(item["status"] == UNREADABLE for item in evidence):
        overall = UNREADABLE
    else:
        overall = "READ"

    return {
        "status": overall,
        "source": "external_vision_adapter",
        "evidence": evidence,
        "rule": "Observed status is authoritative; confidence never converts missing evidence into PRESENT.",
    }
