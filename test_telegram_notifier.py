from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from telegram_notifier import enabled, format_opportunity, notify_opportunity


class TelegramNotifierTests(unittest.TestCase):
    def test_disabled_without_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(enabled())

    def test_format_contains_execution_guard(self):
        text = format_opportunity({
            "symbol": "TESTUSDT",
            "direction": "long",
            "status": "TRADEABLE",
            "score": 88,
            "risk_ratio_pct": 20,
            "reward_risk": 3,
            "reasons": ["aligned"],
            "hard_blocks": [],
        })
        self.assertIn("Execution: OFF", text)
        self.assertIn("TESTUSDT", text)

    def test_non_tradeable_does_not_send(self):
        with patch("telegram_notifier.send_message") as send:
            result = notify_opportunity({
                "symbol": "TESTUSDT",
                "status": "WATCH",
            })
        self.assertFalse(result["sent"])
        send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
