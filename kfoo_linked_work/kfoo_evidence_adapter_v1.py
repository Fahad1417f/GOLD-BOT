from __future__ import annotations

"""Fail-closed KFOO visual evidence normalization.

This module never derives KFOO values from generic market indicators. It only
reports evidence that is explicitly visible in supplied TradingView text.
"""

from dataclasses import dataclass
import re
from typing import Mapping

PRESENT = "PRESENT"
ABSENT = "ABSENT"
UNREADABLE = "UNREADABLE"
DATA_UNAVAILABLE = "DATA_UNAVAILABLE"

DEFAULT_ALIASES: dict[str, tuple[str, ...]] = {
    "continuity_average": ("continuity average", "continuity avg", "متوسط الاستمرارية"),
    "liquidity_table": ("liquidity", "liquidity table", "السيولة", "جدول السيولة"),
    "liquidity_net_positive": ("net liquidity positive", "inflow > outflow", "صافي السيولة موجب"),
    "ascending_channel": ("ascending channel", "rising channel", "القناة صاعدة", "قناة صاعدة"),
    "whales_buying": ("whales buying", "whale buying", "الحيتان شراء"),
    "kfoo_arrow": ("kfoo arrow", "kfoo signal arrow", "سهم كفو"),
    "divergence": ("kfoo divergence", "divergence", "دايفر"),
    "whale_wave_sync": ("whale wave sync", "whale wave", "مزامنة موجة الحيتان"),
}

@dataclass(frozen=True)
class EvidenceItem:
    key: str
    status: str
    matched_text: str | None = None
    source: str = "tradingview_visible_text"
    reason: str = ""

    def to_dict(self) -> dict:
        return {"key": self.key, "status": self.status, "matched_text": self.matched_text,
                "source": self.source, "reason": self.reason}

def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().casefold()

def _find(text: str, aliases: tuple[str, ...]) -> str | None:
    normalized = _normalize(text)
    for alias in aliases:
        needle = _normalize(alias)
        if needle and needle in normalized:
            return alias
    return None

def extract_kfoo_evidence(
    visible_text: str | None,
    *,
    aliases: Mapping[str, tuple[str, ...]] | None = None,
) -> dict:
    if visible_text is None:
        return {"status": DATA_UNAVAILABLE, "source": "tradingview_visible_text",
                "evidence": [], "reason": "VISIBLE_TEXT_UNAVAILABLE"}
    text = visible_text.strip()
    if not text:
        return {"status": DATA_UNAVAILABLE, "source": "tradingview_visible_text",
                "evidence": [], "reason": "VISIBLE_TEXT_EMPTY"}

    configured = dict(DEFAULT_ALIASES)
    if aliases:
        configured.update(aliases)

    items: list[EvidenceItem] = []
    for key, key_aliases in configured.items():
        match = _find(text, key_aliases)
        if match:
            items.append(EvidenceItem(key, PRESENT, match))
        else:
            items.append(EvidenceItem(
                key, UNREADABLE, None,
                reason="NO_VERIFIABLE_KFOO_LABEL_IN_VISIBLE_TEXT",
            ))

    return {
        "status": "READ",
        "source": "tradingview_visible_text",
        "evidence": [item.to_dict() for item in items],
        "rule": "Only explicit visible KFOO evidence is PRESENT; missing evidence is UNREADABLE.",
    }
