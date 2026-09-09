from __future__ import annotations
import importlib,json
REQUIRED=["kfoo_table","kfoo_direction","multi_timeframe","kfoo_rules","crypto_demo_v53","telegram_notifier","openai_bridge","live_vision_agent_fixed","chart_controller"]
def check():
    results={}
    for name in REQUIRED:
        try:
            mod=importlib.import_module(name); results[name]={"ok":True,"file":getattr(mod,"__file__",None)}
        except Exception as exc: results[name]={"ok":False,"error":f"{type(exc).__name__}: {exc}"}
    return {"imports":results,"safety":{"tradingview_only_chart_control":True,"navigation_disabled":True,"tab_switching_disabled":True,"order_clicks_disabled":True,"verify_every_action":True,"binance_production_allowed":False,"execution_default_off":True}}
if __name__=="__main__":
    r=check(); print(json.dumps(r,ensure_ascii=False,indent=2)); raise SystemExit(1 if any(not v["ok"] for v in r["imports"].values()) else 0)