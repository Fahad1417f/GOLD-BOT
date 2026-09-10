from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Optional
import hashlib, json

def _dir_from_bias(v: Any) -> Optional[str]:
    if v in ('bullish','long'): return 'long'
    if v in ('bearish','short'): return 'short'
    return None

def _pct(agg: dict, key: str) -> float:
    try: return float(agg.get(key) or 0.0)
    except Exception: return 0.0
@dataclass
class Signal:
    level: str='WAIT'; direction: str='neutral'; score: float=0.0
    reasons: list[str]|None=None; event_key: str=''; setup_ready: bool=False; entry_ready: bool=False; timestamp_utc: str=''
    def to_dict(self):
        d=asdict(self); d['reasons']=list(self.reasons or []); return d

def _stable_gravity(items:dict[str,dict], tf:str)->tuple[Optional[str],bool,str]:
    x=items.get(tf) or {}; samples=x.get('samples') or x.get('gravity_samples_data') or []
    dirs=[_dir_from_bias(s.get('active_kfoo')) or _dir_from_bias(s.get('direction')) for s in samples]; dirs=[d for d in dirs if d]
    if not dirs:return None,False,'no_stable_samples'
    last=dirs[-1]; latest3=dirs[-3:]; majority=sum(1 for d in dirs if d==last)/len(dirs)
    stable=len(latest3)==3 and all(d==last for d in latest3) and majority>=0.70
    return last,stable,f'{sum(1 for d in dirs if d==last)}/{len(dirs)}'

def _hns_gate(verified_hns_mtf: dict|None, gravity: str|None)->tuple[bool,list[str]]:
    if not isinstance(verified_hns_mtf,dict): return False,[]
    if not verified_hns_mtf.get('verified'):
        return False,['verified MTF H&S feed incomplete; H&S not used for promotion']
    aligned=bool(verified_hns_mtf.get('aligned')); hdir=_dir_from_bias(verified_hns_mtf.get('direction'))
    if aligned and hdir in ('long','short'):
        if gravity and hdir!=gravity:
            return True,[f'verified MTF H&S conflicts with higher-timeframe gravity (H&S={hdir}, gravity={gravity})']
        return False,[f'verified MTF H&S confirmed and aligned ({hdir})']
    if any(bool((f or {}).get('detected')) for f in (verified_hns_mtf.get('frames') or {}).values()):
        return False,['verified MTF H&S detected but clean multi-timeframe confirmation is not complete']
    return False,[]

def promote(analysis:dict[str,dict],timing:dict[str,Any]|None=None,verified_hns_mtf:dict|None=None)->Signal:
    timing=timing or {}; reasons=[]
    g4,s4,r4=_stable_gravity(analysis,'4h'); g1,s1,r1=_stable_gravity(analysis,'1h')
    gravity_aligned=bool(g4 and g1 and g4==g1 and s4 and s1)
    hns_blocked,hns_reasons=_hns_gate(verified_hns_mtf,g4 if gravity_aligned else None); reasons.extend(hns_reasons)
    if hns_blocked:return Signal(level='WAIT',direction=g4 or 'neutral',score=0.20,reasons=reasons,setup_ready=False,entry_ready=False,timestamp_utc=datetime.now(timezone.utc).isoformat())
    leader=analysis.get('15m') or {}; linfo=leader.get('analysis') or {}
    ldir=_dir_from_bias(leader.get('active_kfoo')) or _dir_from_bias((linfo.get('kfoo_table_direction') or {}).get('bias')) or _dir_from_bias(linfo.get('direction'))
    table=linfo.get('kfoo_table') or {}; aggs=table.get('aggregates') or {}; tfagg=aggs.get('timeframes') or {}; indagg=aggs.get('indicators') or {}
    leader_table_ok=bool(linfo.get('kfoo_table_detected')); active15=_dir_from_bias((table.get('timeframes') or {}).get('15m',{}).get('signal'))
    tf_pct=max(_pct(tfagg,'bullish_pct'),_pct(tfagg,'bearish_pct')); ind_pct=max(_pct(indagg,'bullish_pct'),_pct(indagg,'bearish_pct'))
    leader_aligned=bool(gravity_aligned and ldir==g4); kfoo_quality=leader_table_ok and tf_pct>=62.5 and ind_pct>=75.0 and active15==ldir
    reasons.append('4H+1H gravity aligned and stable' if gravity_aligned else f'gravity not aligned/stable (4H={g4}/{r4}, 1H={g1}/{r1})')
    reasons.append('15M leader agrees with gravity' if leader_aligned else f'15M leader not confirmed (leader={ldir}, activeKFOO={active15})')
    reasons.append(f'KFOO confirmed TF={tf_pct:.1f}% IND={ind_pct:.1f}%' if kfoo_quality else f'KFOO incomplete/weak TF={tf_pct:.1f}% IND={ind_pct:.1f}%')
    if not gravity_aligned or not leader_aligned or not kfoo_quality:return Signal(level='WAIT',direction=g4 or ldir or 'neutral',score=0.40 if gravity_aligned else 0.20,reasons=reasons,setup_ready=False,entry_ready=False,timestamp_utc=datetime.now(timezone.utc).isoformat())
    if not bool(timing.get('leader_closed')):return Signal(level='STRONG_SETUP',direction=g4,score=0.85,reasons=reasons+['waiting for 15M candle close'],setup_ready=True,entry_ready=False,timestamp_utc=datetime.now(timezone.utc).isoformat())
    a5=analysis.get('5m') or {}; a3=analysis.get('3m') or {}
    d5=_dir_from_bias((a5.get('analysis') or {}).get('kfoo_table_direction',{}).get('bias')) or _dir_from_bias((a5.get('analysis') or {}).get('direction'))
    d3=_dir_from_bias((a3.get('analysis') or {}).get('kfoo_table_direction',{}).get('bias')) or _dir_from_bias((a3.get('analysis') or {}).get('direction'))
    entry=d5==g4 and d3==g4 and bool((a5.get('analysis') or {}).get('kfoo_table_detected')) and bool((a3.get('analysis') or {}).get('kfoo_table_detected'))
    if entry:return Signal(level='STRONG_ENTRY',direction=g4,score=0.95,reasons=reasons+['5M and 3M timing aligned'],setup_ready=True,entry_ready=True,timestamp_utc=datetime.now(timezone.utc).isoformat())
    return Signal(level='STRONG_SETUP',direction=g4,score=0.90,reasons=reasons+[f'timing not aligned (5M={d5}, 3M={d3})'],setup_ready=True,entry_ready=False,timestamp_utc=datetime.now(timezone.utc).isoformat())

def finalize(sig:Signal,payload_core:dict)->Signal:
    raw=json.dumps({'level':sig.level,'direction':sig.direction,'core':payload_core},sort_keys=True,ensure_ascii=False); sig.event_key=hashlib.sha256(raw.encode()).hexdigest()[:24]; return sig
