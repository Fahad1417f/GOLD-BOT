"""Canonical V56 signal engine adapter.

The monitor previously contained a second implementation. This module now
re-exports the authoritative engine so callers cannot silently drift.
"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from kfoo_linked_work.signal_engine_v56 import Signal, finalize, promote
__all__=["Signal","promote","finalize"]
