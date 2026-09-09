from __future__ import annotations
import os, secrets, time
from typing import Literal
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app=FastAPI(title="GOLD-BOT Backend",version="1.0")
API_TOKEN=os.getenv("GOLDBOT_BACKEND_TOKEN","").strip()
ALLOWED={"status","health","test","log","stop"}

class AgentState(BaseModel):
    symbol:str|None=None; timeframe:str|None=None; direction:str="neutral"
    confidence:float=0.0; kfoo:str="0/5"; flow:str=""; execution:str="OFF"
    updated_at:float=0.0

state=AgentState()

def auth(x_gb_token:str|None):
    if not API_TOKEN or not x_gb_token or not secrets.compare_digest(x_gb_token,API_TOKEN):
        raise HTTPException(401,"unauthorized")

@app.get("/health")
def health(): return {"ok":True,"execution":"OFF","production_binance":"BLOCKED","allowed_commands":sorted(ALLOWED)}

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

@app.post("/agent/command")
def command(payload:Command,x_gb_token:str|None=Header(default=None)):
    auth(x_gb_token)
    # Backend only validates/queues allowlisted commands; it never executes OS shell.
    return {"ok":True,"queued":payload.command,"execution":"OFF","production_binance":"BLOCKED"}

@app.get("/security")
def security():
    return {"arbitrary_shell":False,"powershell":False,"navigation":False,"tab_switching":False,"order_clicks":False,"execution_default":"OFF","production_binance":"BLOCKED","commands":sorted(ALLOWED)}
