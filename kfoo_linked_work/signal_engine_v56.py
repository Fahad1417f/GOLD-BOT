from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Optional
import hashlib, json


def _dir(v: Any) -> Optional[str]:
    if v in ('bullish','long'): return 'long'
    if v in ('bearish','short'): return 'short'
    return None

def _pct(agg: dict, key: str) -> float:
    try: return float(agg.get(key) or 0.0)
    except Exception: return 0.0

@dataclass
class Signal:
    level: str='WAIT'; direction: str='neutral'; score: float=0.0
    reasons: list[str] | None=None; event_key: str=''
    setup_ready: bool=False; entry_ready: bool=False; timestamp_utc: str=''
    def to_dict(self):
        d=asdict(self); d['reasons']=list(self.reasons or []); return d

def _stable_gravity(items: dict[str,dict], tf: str):
    x=items.get(tf) or {}; samples=x.get('samples') or x.get('gravity_samples_data') or []
    dirs=[_dir(s.get('active_kfoo')) or _dir(s.get('direction')) for s in samples]
    dirs=[d for d in dirs if d]
    if not dirs: return None,False,'no_stable_samples'
    last=dirs[-1]; latest3=dirs[-3:]
    majority=sum(1 for d in dirs if d==last)/len(dirs)
    stable=len(latest3)==3 and all(d==last for d in latest3) and majority>=0.70
    return last,stable,f'{sum(1 for d in dirs if d==last)}/{len(dirs)}'

def promote(analysis: dict[str,dict], timing: dict[str,Any]|None=None)->Signal:
    timing=timing or {}; reasons=[]
    g4,s4,r4=_stable_gravity(analysis,'4h'); g1,s1,r1=_stable_gravity(analysis,'1h')
    leader=analysis.get('15m') or {}; linfo=leader.get('analysis') or {}
    ldir=_dir(leader.get('active_kfoo')) or _dir((linfo.get('kfoo_table_direction') or {}).get('bias')) or _dir(linfo.get('direction'))
    table=linfo.get('kfoo_table') or {}; aggs=table.get('aggregates') or {}
    tfagg=aggs.get('timeframes') or {}; indagg=aggs.get('indicators') or {}
    table_ok=bool(linfo.get('kfoo_table_detected')); active15=_dir((table.get('timeframes') or {}).get('15m',{}).get('signal'))
    tf_pct=max(_pct(tfagg,'bullish_pct'),_pct(tfagg,'bearish_pct')); ind_pct=max(_pct(indagg,'bullish_pct'),_pct(indagg,'bearish_pct'))
    gravity=bool(g4 and g1 and g4==g1 and s4 and s1); leader_ok=bool(gravity and ldir==g4)
    kfoo_ok=table_ok and tf_pct>=62.5 and ind_pct>=75.0 and active15==ldir
    hns=linfo.get('head_shoulders') if isinstance(linfo,dict) else None
    hns=hns or {}; hns_confirmed=bool(hns.get('confirmed')); hns_dir=_dir(hns.get('direction'))
    if gravity: reasons.append('4H+1H gravity aligned and stable')
    else: reasons.append(f'gravity not aligned/stable (4H={g4}/{r4}, 1H={g1}/{r1})')
    if leader_ok: reasons.append('15M leader agrees with gravity')
    else: reasons.append(f'15M leader not confirmed (leader={ldir}, activeKFOO={active15})')
    if kfoo_ok: reasons.append(f'KFOO confirmed TF={tf_pct:.1f}% IND={ind_pct:.1f}%')
    else: reasons.append(f'KFOO incomplete/weak TF={tf_pct:.1f}% IND={ind_pct:.1f}%')
    if hns_confirmed and hns_dir==g4: reasons.append('H&S confirmed and aligned with gravity')
    elif hns.get('detected'): reasons.append('H&S detected but clean neckline confirmation is not complete')
    if hns_confirmed and hns_dir not in (g4,None):
        return Signal('WAIT',g4 or 'neutral',0.20,reasons+['H&S direction conflicts with higher-timeframe gravity'],False,False,datetime.now(timezone.utc).isoformat())
    if not gravity or not leader_ok or not kfoo_ok:
        return Signal('WAIT',g4 or ldir or 'neutral',0.40 if gravity else 0.20,reasons,False,False,datetime.now(timezone.utc).isoformat())
    if not bool(timing.get('leader_closed')):
        return Signal('STRONG_SETUP',g4,0.85,reasons+['waiting for 15M candle close'],'',True,False,datetime.now(timezone.utc).isoformat())
    a5=analysis.get('5m') or {}; a3=analysis.get('3m') or {}
    d5=_dir(((a5.get('analysis') or {}).get('kfoo_table_direction') or {}).get('bias')) or _dir((a5.get('analysis') or {}).get('direction'))
    d3=_dir(((a3.get('analysis') or {}).get('kfoo_table_direction') or {}).get('bias')) or _dir((a3.get('analysis') or {}).get('direction'))
    entry=d5==g4 and d3==g4 and bool((a5.get('analysis') or {}).get('kfoo_table_detected')) and bool((a3.get('analysis') or {}).get('kfoo_table_detected'))
    if entry: return Signal('STRONG_ENTRY',g4,0.95,reasons+['5M and 3M timing aligned'],'',True,True,datetime.now(timezone.utc).isoformat())
    return Signal('STRONG_SETUP',g4,0.90,reasons+[f'timing not aligned (5M={d5}, 3M={d3})'],'',True,False,datetime.now(timezone.utc).isoformat())

def finalize(sig: Signal, payload_core: dict)->Signal:
    raw=json.dumps({'level':sig.level,'direction':sig.direction,'core':payload_core},sort_keys=True,ensure_ascii=False)
    sig.event_key=hashlib.sha256(raw.encode()).hexdigest()[:24]
    return sig
