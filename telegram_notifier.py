from __future__ import annotations

"""Small, fail-closed Telegram notifier for GOLD-BOT alerts.

Credentials are read only from environment variables:
GOLDBOT_TELEGRAM_BOT_TOKEN
GOLDBOT_TELEGRAM_CHAT_ID
GOLDBOT_TELEGRAM_ALERTS=1

No token, chat id, or .env file belongs in Git.
"""

import os
from typing import Any, Mapping
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json


TOKEN_ENV = "GOLDBOT_TELEGRAM_BOT_TOKEN"
CHAT_ENV = "GOLDBOT_TELEGRAM_CHAT_ID"
ALERTS_ENV = "GOLDBOT_TELEGRAM_ALERTS"


def enabled() -> bool:
    return os.getenv(ALERTS_ENV, "").strip().lower() in {"1", "true", "yes", "on"} and bool(
        os.getenv(TOKEN_ENV, "").strip()
    ) and bool(os.getenv(CHAT_ENV, "").strip())


def send_message(text: str, timeout: float = 10.0) -> dict[str, Any]:
    token = os.getenv(TOKEN_ENV, "").strip()
    chat_id = os.getenv(CHAT_ENV, "").strip()
    if not token or not chat_id:
        return {"ok": False, "sent": False, "reason": "TELEGRAM_CREDENTIALS_MISSING"}
    if not enabled():
        return {"ok": False, "sent": False, "reason": "TELEGRAM_ALERTS_DISABLED"}

    body = urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return {"ok": bool(payload.get("ok")), "sent": bool(payload.get("ok")), "response": payload}
    except Exception as exc:
        return {"ok": False, "sent": False, "reason": f"{type(exc).__name__}:{exc}"}


def _display_symbol(value: Any) -> str:
    """Render perpetual crypto symbols in TradingView-style XXXUSDT.P form."""
    symbol = str(value or "UNKNOWN").strip().upper()
    if symbol.endswith(".P"):
        return symbol
    if symbol.endswith("USDT"):
        return f"{symbol}.P"
    return symbol


def format_opportunity(op: Mapping[str, Any]) -> str:
    status = str(op.get("status") or "WATCH")
    direction = str(op.get("direction") or "neutral").upper()
    arrow = "🟢 BUY" if direction == "LONG" else "🔴 SELL" if direction == "SHORT" else "⚪ WAIT"
    rr = op.get("reward_risk")
    risk = op.get("risk_ratio_pct")
    lines = [
        "GOLD-BOT • Opportunity Scanner",
        f"{arrow} {_display_symbol(op.get('symbol', 'UNKNOWN'))}",
        f"Status: {status} | Score: {op.get('score', '—')}/100",
        f"Risk Ratio: {risk:.1f}%" if isinstance(risk, (int, float)) else "Risk Ratio: —",
        f"Reward/Risk: {rr:.2f}R" if isinstance(rr, (int, float)) else "Reward/Risk: —",
    ]
    blocks = list(op.get("hard_blocks") or [])
    reasons = list(op.get("reasons") or [])
    if blocks:
        lines.append("BLOCK: " + " | ".join(blocks[:3]))
    if reasons:
        lines.append("WHY: " + " | ".join(reasons[:4]))
    lines.append("Execution: OFF")
    return "\n".join(lines)


def notify_opportunity(op: Mapping[str, Any]) -> dict[str, Any]:
    if str(op.get("status")) != "TRADEABLE":
        return {"ok": True, "sent": False, "reason": "NOT_TRADEABLE"}
    return send_message(format_opportunity(op))


if __name__ == "__main__":
    sample = {
        "symbol": "TESTUSDT",
        "direction": "long",
        "status": "TRADEABLE",
        "score": 85,
        "risk_ratio_pct": 20,
        "reward_risk": 3,
        "reasons": ["4H + 1H gravity aligned"],
        "hard_blocks": [],
    }
    print(json.dumps(notify_opportunity(sample), ensure_ascii=False, indent=2))
