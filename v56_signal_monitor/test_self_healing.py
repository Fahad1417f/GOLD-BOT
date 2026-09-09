import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from self_healing import diagnose, KNOWN_ANALYSIS_ERROR

class SelfHealingTests(unittest.TestCase):
    def test_known_analysis_error(self):
        d=diagnose("TypeError: "+KNOWN_ANALYSIS_ERROR)
        self.assertEqual(d["class"],"CODE_INTEGRATION_ERROR")
        self.assertEqual(d["repair"],"QUARANTINE_AND_PROPOSE")

    def test_runtime_error_is_restartable(self):
        d=diagnose("Traceback (most recent call last)")
        self.assertEqual(d["class"],"RUNTIME_ERROR")
        self.assertEqual(d["repair"],"RESTART_AND_RETEST")

    def test_clean_log(self):
        d=diagnose("CAPTURE_15M=PASS\nKFOO_TABLE_15M=PASS")
        self.assertEqual(d["class"],"NONE")

if __name__=="__main__":
    unittest.main()
