from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from self_healing import diagnose, KNOWN_ANALYSIS_ERROR

def test_known_analysis_error():
    d = diagnose("TypeError: " + KNOWN_ANALYSIS_ERROR)
    assert d["class"] == "CODE_INTEGRATION_ERROR"
    assert d["repair"] == "QUARANTINE_AND_PROPOSE"

def test_runtime_error_is_restartable():
    d = diagnose("Traceback (most recent call last)")
    assert d["class"] == "RUNTIME_ERROR"
    assert d["repair"] == "RESTART_AND_RETEST"

def test_clean_log():
    d = diagnose("CAPTURE_15M=PASS\nKFOO_TABLE_15M=PASS")
    assert d["class"] == "NONE"
