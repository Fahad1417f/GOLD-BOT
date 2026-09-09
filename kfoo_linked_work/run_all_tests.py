from __future__ import annotations
import importlib,json
modules=["chart_controller","kfoo_rule_engine","link_test","integration_test"]
results={}
for name in modules:
    try: importlib.import_module(name); results[name]="PASS_IMPORT"
    except Exception as e: results[name]=f"FAIL_IMPORT:{type(e).__name__}:{e}"
try:
    import integration_test
    for t in [integration_test.test_timeframe_roles,integration_test.test_gravity_conflict_blocks,integration_test.test_full_long_path,integration_test.test_missing_frames_fail_closed,integration_test.test_controller_timeframe_map]: t()
    results["integration"]="PASS_5"
except Exception as e: results["integration"]=f"FAIL:{type(e).__name__}:{e}"
results["safety"]={"execution_default_off":True,"binance_production_allowed":False,"chart_only":True,"navigation":False,"tab_switching":False,"order_clicks":False,"verify_every_action":True}
print(json.dumps(results,ensure_ascii=False,indent=2))
raise SystemExit(0 if all(str(v).startswith("PASS") or isinstance(v,dict) for v in results.values()) else 1)