from __future__ import annotations

"""Run Opportunity Scanner V2 and optionally send the selected alert to Telegram."""

import json

from kfoo_linked_work.opportunity_scanner_v2 import scan_environment
from telegram_notifier import notify_opportunity


def main() -> int:
    result = scan_environment()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    if result.status == "SELECTED" and result.selected is not None:
        sent = notify_opportunity(result.selected.to_dict())
        print(json.dumps({"telegram": sent}, ensure_ascii=False, indent=2))
        return 0 if sent.get("ok") else 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())