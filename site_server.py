from __future__ import annotations
import json, time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT=Path(__file__).resolve().parent
STATE=ROOT/'website_state.json'
ALERTED_KEYS:set[str]=set()

try:
    from kfoo_linked_work.opportunity_scanner_v1 import OpportunityScanner
    from telegram_notifier import notify_opportunity
    SCANNER=OpportunityScanner()
except Exception:
    SCANNER=None
    notify_opportunity=None

DEFAULT={
    "eventType":"NO_SIGNAL","level":"WAIT","direction":"neutral","confidence":0.0,"score":0.0,
    "symbol":"XAUUSD","timeframe":"15m","gravity":{"4h":"unknown","1h":"unknown"},
    "leader":{"15m":"unknown"},"timing":{"5m":"unknown","3m":"unknown"},
    "kfoo":{"tf_pct":None,"ind_pct":None,"active15":"unknown"},
    "head_shoulders":{"available":False,"detected":False,"confirmed":False,"direction":"neutral","pattern":"none","reason":"verified_candle_feed_not_available"},
    "market_context":{
        "available":False,
        "risk":{"value_pct":None,"status":"unknown","rising":False},
        "liquidity":{"incoming_usd":None,"outgoing_usd":None,"net_usd":None,"net_ratio_pct":None,"strength":"unknown"},
        "continuity":{"price":None,"average":None,"slope":None,"distance_pct":None,"side_ok":False,"status":"unknown"}
    },
    "opportunity":{"status":"WAIT","score":0.0,"risk_ratio_pct":None,"reward_risk":None,"reasons":[],"hard_blocks":[]},
    "chart_reader":{"backend":"playwright_cdp","connected":False,"verified":False,"source":"none","candles_available":False,"reason":"not_started"},
    "reasons":[],"updated_at":0.0,"execution":"OFF"
}

def load_state():
    try:return json.loads(STATE.read_text(encoding='utf-8'))
    except Exception:return DEFAULT.copy()

def save_state(data):
    tmp=STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    tmp.replace(STATE)

def build_opportunity(data:dict, state:dict) -> dict:
    raw=data.get("opportunity")
    if isinstance(raw,dict):
        candidate=dict(raw)
    else:
        mc=data.get("market_context") or state.get("market_context") or {}
        risk=mc.get("risk") or {}
        liq=mc.get("liquidity") or {}
        cont=mc.get("continuity") or {}
        k=data.get("kfoo") or {}
        gravity=data.get("gravity") or {}
        leader=data.get("leader") or {}
        timing=data.get("timing") or {}
        candidate={
            "symbol":data.get("symbol") or "XAUUSD",
            "direction":data.get("direction") or "neutral",
            "risk_ratio_pct":risk.get("value_pct"),
            "reward_risk":data.get("reward_risk",data.get("rr")),
            "entry":data.get("entry"),
            "stop":data.get("stop") or data.get("stop_loss"),
            "target":data.get("target") or data.get("take_profit"),
            "gravity_4h":gravity.get("4h"),
            "gravity_1h":gravity.get("1h"),
            "leader_15m":leader.get("15m") or data.get("direction"),
            "timing_5m":timing.get("5m"),
            "timing_3m":timing.get("3m"),
            "kfoo_tf_pct":k.get("tf_pct",k.get("tf_agg")),
            "kfoo_ind_pct":k.get("ind_pct",k.get("ind_agg")),
            "liquidity":liq,
            "continuity":cont,
            "event_key":data.get("eventKey") or data.get("event_key")
        }
    return SCANNER.scan(candidate).to_dict() if SCANNER else {
        "status":"WAIT","score":0.0,"hard_blocks":["Opportunity Scanner unavailable"]
    }

def maybe_alert(opportunity:dict):
    if not notify_opportunity or opportunity.get("status")!="TRADEABLE":
        return {"sent":False,"reason":"NOT_TRADEABLE_OR_NOT_CONFIGURED"}
    key=str(opportunity.get("event_key") or opportunity.get("eventKey") or "")
    if key and key in ALERTED_KEYS:
        return {"sent":False,"reason":"DUPLICATE_EVENT"}
    result=notify_opportunity(opportunity)
    if result.get("sent") and key:
        ALERTED_KEYS.add(key)
    return result

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT/'website'),**kw)
    def end_headers(self):
        self.send_header('Cache-Control','no-store')
        super().end_headers()
    def do_GET(self):
        if self.path in ('/api/health','/health'):
            s=load_state()
            b=json.dumps({
                'ok':True,'execution':'OFF','webhook':'ready',
                'opportunity':s.get('opportunity',{}),
                'telegram_alerts':bool(notify_opportunity),
                'chart_reader':s.get('chart_reader',{}),
                'head_shoulders':s.get('head_shoulders',{}),
                'market_context':s.get('market_context',{})
            },ensure_ascii=False).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
        if self.path=='/api/public-state':
            b=json.dumps(load_state(),ensure_ascii=False).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
        return super().do_GET()
    def do_POST(self):
        if self.path!='/api/webhooks/tradingview':
            self.send_response(404);self.end_headers();return
        try:
            n=int(self.headers.get('Content-Length','0'))
            data=json.loads(self.rfile.read(n).decode('utf-8'))
            state=load_state()
            state.update({
                'eventType':data.get('eventType') or data.get('level') or 'WAIT',
                'level':data.get('level') or data.get('eventType') or 'WAIT',
                'direction':data.get('direction') or 'neutral',
                'confidence':float(data.get('confidence') or data.get('signalScore') or 0.0),
                'score':float(data.get('score') or data.get('signalScore') or 0.0),
                'symbol':data.get('symbol') or 'XAUUSD',
                'timeframe':data.get('timeframe') or '15m',
                'gravity':data.get('gravity') or {},
                'leader':data.get('leader') or {},
                'timing':data.get('timing') or {},
                'kfoo':data.get('kfoo') or {},
                'head_shoulders':data.get('head_shoulders') or data.get('hns') or state.get('head_shoulders',{}),
                'market_context':data.get('market_context') or state.get('market_context',{}),
                'chart_reader':data.get('chart_reader') or state.get('chart_reader',{}),
                'reasons':data.get('reasons') or data.get('signalReasons') or [],
                'updated_at':time.time(),'execution':'OFF'
            })
            opportunity=build_opportunity(data,state)
            state['opportunity']=opportunity
            save_state(state)
            alert=maybe_alert(opportunity)
            b=json.dumps({'ok':True,'received':True,'execution':'OFF','opportunity':opportunity,'telegram':alert},ensure_ascii=False).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
            print(f"WEBHOOK_RECEIVED level={state['level']} direction={state['direction']} score={state['score']} opportunity={opportunity.get('status')} opp_score={opportunity.get('score')}",flush=True)
        except Exception as e:
            b=json.dumps({'ok':False,'error':str(e),'execution':'OFF'}).encode()
            self.send_response(400);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)

if __name__=='__main__':
    if not STATE.exists():save_state(DEFAULT)
    httpd=ThreadingHTTPServer(('127.0.0.1',3000),Handler)
    print('GOLD_BOT_SITE_SERVER=READY',flush=True)
    print('SITE_URL=http://127.0.0.1:3000',flush=True)
    print('WEBHOOK=http://127.0.0.1:3000/api/webhooks/tradingview',flush=True)
    print('TELEGRAM_OPPORTUNITY_ALERTS=CONFIGURED_VIA_ENV',flush=True)
    print('EXECUTION=OFF',flush=True)
    httpd.serve_forever()
