"""Capture adapter contract. Intentionally broker/platform agnostic."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Any

@dataclass(frozen=True)
class Frame:
    image:Any
    timestamp:float
    source:str="screen"

class CaptureAdapter(Protocol):
    def capture(self) -> Frame: ...
