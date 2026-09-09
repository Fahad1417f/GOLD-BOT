from __future__ import annotations
import json, time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT=Path(__file__).resolve().parent
STATE=ROOT/'website_state.json'
DEFAULT={"eventType":"NO_SIGNAL","level":"WAIT","direction":"neutral","confidence":0.0,"score":0.0,"symbol":"XAUUSD","timeframe":"15m","gravity":{"4h":"unknown","1h":"unknown"},"leader":{"15m":"unknown"},"timing":{"5m":"unknown","3m":"unknown"},"kfoo":{"tf_pct":None,"ind_pct":None,"active15":"unknown"},"reasons":[],"updated_at":0.0,"execution":"OFF"}

def load_state():
    try:return json.loads(STATE.read_text(encoding='utf-8'))
    except Exception:return DEFAULT.copy()

def save_state(data):
    tmp=STATE.with_suffix('.tmp'); tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8'); tmp.replace(STATE)

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT/'website'),**kw)
    def end_headers(self):self.send_header('Cache-Control','no-store');super().end_headers()
    def do_GET(self):
        if self.path in ('/api/health','/health'):
            b=json.dumps({'ok':True,'execution':'OFF','webhook':'ready'},ensure_ascii=False).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
        if self.path=='/api/public-state':
            b=json.dumps(load_state(),ensure_ascii=False).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
        return super().do_GET()
    def do_POST(self):
        if self.path!='/api/webhooks/tradingview':self.send_response(404);self.end_headers();return
        try:
            n=int(self.headers.get('Content-Length','0'));data=json.loads(self.rfile.read(n).decode('utf-8'))
            state=load_state(); state.update({
                'eventType':data.get('eventType') or data.get('level') or 'WAIT',
                'level':data.get('level') or data.get('eventType') or 'WAIT',
                'direction':data.get('direction') or 'neutral',
                'confidence':float(data.get('confidence') or data.get('signalScore') or 0.0),
                'score':float(data.get('score') or data.get('signalScore') or 0.0),
                'symbol':data.get('symbol') or 'XAUUSD','timeframe':data.get('timeframe') or '15m',
                'gravity':data.get('gravity') or {},'leader':data.get('leader') or {},'timing':data.get('timing') or {},
                'kfoo':data.get('kfoo') or {},'reasons':data.get('reasons') or data.get('signalReasons') or [],
                'updated_at':time.time(),'execution':'OFF'
            }); save_state(state)
            b=json.dumps({'ok':True,'received':True,'execution':'OFF'},ensure_ascii=False).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
            print(f"WEBHOOK_RECEIVED level={state['level']} direction={state['direction']} score={state['score']}",flush=True)
        except Exception as e:
            b=json.dumps({'ok':False,'error':str(e)}).encode();self.send_response(400);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)

if __name__=='__main__':
    if not STATE.exists():save_state(DEFAULT)
    httpd=ThreadingHTTPServer(('127.0.0.1',3000),Handler)
    print('GOLD_BOT_SITE_SERVER=READY',flush=True);print('SITE_URL=http://127.0.0.1:3000',flush=True);print('WEBHOOK=http://127.0.0.1:3000/api/webhooks/tradingview',flush=True);print('EXECUTION=OFF',flush=True)
    httpd.serve_forever()
