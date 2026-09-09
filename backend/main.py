from __future__ import annotations
import os, secrets, time
from typing import Literal, Any
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app=FastAPI(title="GOLD-BOT Backend",version="2.0")
API_TOKEN=os.getenv("GOLDBOT_BACKEND_TOKEN","").strip()
ALLOWED={"status","health","test","log","stop"}

class AgentState(BaseModel):
    symbol:str|None=None; timeframe:str|None=None; direction:str="neutral"
    confidence:float=0.0; kfoo:str="0/5"; flow:str=""; execution:str="OFF"
    level:str="WAIT"; score:float=0.0; eventType:str="NO_SIGNAL"
    gravity:dict[str,str]={}; leader:dict[str,str]={}; timing:dict[str,str]={}
    kfooDetail:dict[str,Any]={}; reasons:list[str]=[]; updated_at:float=0.0

state=AgentState()
last_event_key=""

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET","POST","OPTIONS"], allow_headers=["*"])

def auth(x_gb_token:str|None):
    if not API_TOKEN or not x_gb_token or not secrets.compare_digest(x_gb_token,API_TOKEN):
        raise HTTPException(401,"unauthorized")

@app.get("/health")
def health():
    return {"ok":True,"execution":"OFF","production_binance":"BLOCKED","webhook":"ready","allowed_commands":sorted(ALLOWED)}

@app.get("/api/public-state")
def public_state():
    return state.model_dump()

@app.get("/state")
def get_state(x_gb_token:str|None=Header(default=None)):
    auth(x_gb_token); return state.model_dump()

class Command(BaseModel):
    command:Literal["status","health","test","log","stop"]

@app.post("/agent/state")
def push_state(payload:AgentState,x_gb_token:str|None=Header(default=None)):
    auth(x_gb_token)
    payload.updated_at=time.time(); state.__dict__.update(payload.model_dump())
    return {"ok":True}

@app.post("/api/webhooks/tradingview")
def tradingview_webhook(payload:dict):
    global last_event_key
    event_key=str(payload.get("eventKey") or payload.get("eventId") or "")
    # Same-machine/local contract; never accepts or executes orders.
    if event_key and event_key==last_event_key:
        return {"ok":True,"duplicate":True,"execution":"OFF"}
    last_event_key=event_key
    state.direction=str(payload.get("direction") or "neutral")
    state.confidence=float(payload.get("confidence") or 0.0)
    state.symbol=payload.get("symbol") or "XAUUSD"
    state.timeframe=payload.get("timeframe") or "15m"
    state.level=str(payload.get("level") or payload.get("eventType") or "WAIT")
    state.score=float(payload.get("score") or 0.0)
    state.eventType=str(payload.get("eventType") or state.level)
    state.gravity=dict(payload.get("gravity") or {})
    state.leader=dict(payload.get("leader") or {})
    state.timing=dict(payload.get("timing") or {})
    state.kfooDetail=dict(payload.get("kfoo") or {})
    state.reasons=list(payload.get("reasons") or [])
    state.execution="OFF"
    state.updated_at=time.time()
    return {"ok":True,"received":True,"level":state.level,"eventType":state.eventType,"execution":"OFF"}

@app.post("/agent/command")
def command(payload:Command,x_gb_token:str|None=Header(default=None)):
    auth(x_gb_token)
    return {"ok":True,"queued":payload.command,"execution":"OFF","production_binance":"BLOCKED"}

@app.get("/security")
def security():
    return {"arbitrary_shell":False,"powershell":False,"navigation":False,"tab_switching":False,"order_clicks":False,"execution_default":"OFF","production_binance":"BLOCKED","commands":sorted(ALLOWED)}
