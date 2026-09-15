from __future__ import annotations
import json, os, time
from pathlib import Path
from verified_chart_controller import VerifiedChartController

DEFAULT_TFS=("4h","1h","15m","5m","3m")

def scan_symbol(symbol, cdp_url=None):
    ctl=VerifiedChartController(cdp_url)
    connected=ctl.connect()
    if not connected.connected:
        return {"status":"BLOCKED","symbol":symbol,"reason":connected.reason}
    try:
        selected=ctl.select_symbol(symbol)
        frames=ctl.scan_timeframes(DEFAULT_TFS)
        return {
            "status":"READY_FOR_KFOO_CAPTURE",
            "symbol":symbol,
            "identity": {"title":selected.title,"url":selected.url,"timeframe":selected.timeframe,"symbol":selected.symbol,"verified":selected.verified},
            "timeframes":frames,
            "execution":"OFF",
            "note":"This stage changes/reads chart UI only. KFOO visual capture and scoring remain fail-closed until verified observations are available."
        }
    except Exception as exc:
        return {"status":"BLOCKED","symbol":symbol,"reason":f"{type(exc).__name__}:{exc}","execution":"OFF"}
    finally:
        ctl.close()

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("symbol")
    p.add_argument("--cdp-url",default=os.getenv("TRADINGVIEW_CDP_URL","http://127.0.0.1:9222"))
    a=p.parse_args()
    print(json.dumps(scan_symbol(a.symbol,a.cdp_url),ensure_ascii=False,indent=2))
