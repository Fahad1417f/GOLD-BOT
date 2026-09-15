from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Optional
import hashlib, json

from market_context_v56 import enrich_market_context


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
    market_context: dict | None=None
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


def _hns_gate(verified_hns_mtf: dict | None, gravity: str | None) -> tuple[bool, list[str]]:
    if not isinstance(verified_hns_mtf, dict):
        return False, []
    reasons: list[str] = []
    verified = bool(verified_hns_mtf.get('verified'))
    aligned = bool(verified_hns_mtf.get('aligned'))
    hdir = _dir(verified_hns_mtf.get('direction'))
    if not verified:
        reasons.append('verified MTF H&S feed incomplete; H&S not used for promotion')
        return False, reasons
    if aligned and hdir in ('long', 'short'):
        if gravity and hdir != gravity:
            return True, [f'verified MTF H&S conflicts with higher-timeframe gravity (H&S={hdir}, gravity={gravity})']
        reasons.append(f'verified MTF H&S confirmed and aligned ({hdir})')
        return False, reasons
    if any(bool((f or {}).get('detected')) for f in (verified_hns_mtf.get('frames') or {}).values()):
        reasons.append('verified MTF H&S detected but clean multi-timeframe confirmation is not complete')
    return False, reasons


def _market_gate(analysis: dict[str,dict], direction: str) -> tuple[bool, bool, list[str], dict]:
    """Return (allow_setup, allow_entry, reasons, context).

    Risk Ratio is a volatility filter, not a direction signal. High volatility
    downgrades entry readiness; extreme volatility blocks promotion. Continuity
    disagreement blocks the direction. Missing enrichment never fabricates data.
    """
    frame = analysis.get('15m') or {}
    ctx = enrich_market_context(frame, expected_side=direction)
    reasons: list[str] = []
    risk = ctx.risk
    if risk.valid:
        reasons.append(f'RiskRatio={risk.status}' + (' rising' if risk.rising else ''))
    if ctx.liquidity.valid:
        if ctx.liquidity.net_ratio_pct is not None:
            reasons.append(f'liquidity_net={ctx.liquidity.net_ratio_pct:.1f}%')
        reasons.append(f'liquidity_strength={ctx.liquidity.strength}')
        if ctx.liquidity.velocity_usd is not None:
            reasons.append(f'liquidity_velocity={ctx.liquidity.velocity_usd:.0f}')
    if ctx.continuity.valid:
        if ctx.continuity.distance_pct is not None:
            reasons.append(f'continuity_distance={ctx.continuity.distance_pct:.3f}%')
        reasons.append(f'continuity={ctx.continuity.status}')
    allow_setup = True
    allow_entry = True
    if risk.valid and risk.status == 'extreme':
        allow_setup = allow_entry = False
        reasons.append('extreme volatility blocks promotion')
    elif risk.valid and risk.status == 'high':
        allow_entry = False
        reasons.append('high volatility: setup allowed, entry held')
    if ctx.continuity.valid and not ctx.continuity.side_ok:
        allow_entry = False
        reasons.append('continuity average conflicts with direction')
    return allow_setup, allow_entry, reasons, ctx.to_dict()


def promote(analysis: dict[str,dict], timing: dict[str,Any]|None=None,
            verified_hns_mtf: dict | None=None, previous_analysis: dict[str,dict] | None=None)->Signal:
    timing=timing or {}; reasons=[]
    g4,s4,r4=_stable_gravity(analysis,'4h'); g1,s1,r1=_stable_gravity(analysis,'1h')
    gravity=bool(g4 and g1 and g4==g1 and s4 and s1)
    hns_blocked,hns_reasons=_hns_gate(verified_hns_mtf, g4 if gravity else None)
    reasons.extend(hns_reasons)
    if hns_blocked:
        return Signal(level='WAIT',direction=g4 or 'neutral',score=0.20,reasons=reasons,setup_ready=False,entry_ready=False,timestamp_utc=datetime.now(timezone.utc).isoformat())

    leader=analysis.get('15m') or {}; linfo=leader.get('analysis') or {}
    ldir=_dir(leader.get('active_kfoo')) or _dir((linfo.get('kfoo_table_direction') or {}).get('bias')) or _dir(linfo.get('direction'))
    table=linfo.get('kfoo_table') or {}; aggs=table.get('aggregates') or {}
    tfagg=aggs.get('timeframes') or {}; indagg=aggs.get('indicators') or {}
    table_ok=bool(linfo.get('kfoo_table_detected')); active15=_dir((table.get('timeframes') or {}).get('15m',{}).get('signal'))
    tf_pct=max(_pct(tfagg,'bullish_pct'),_pct(tfagg,'bearish_pct')); ind_pct=max(_pct(indagg,'bullish_pct'),_pct(indagg,'bearish_pct'))
    leader_ok=bool(gravity and ldir==g4)
    kfoo_ok=table_ok and tf_pct>=62.5 and ind_pct>=75.0 and active15==ldir

    if gravity: reasons.append('4H+1H gravity aligned and stable')
    else: reasons.append(f'gravity not aligned/stable (4H={g4}/{r4}, 1H={g1}/{r1})')
    if leader_ok: reasons.append('15M leader agrees with gravity')
    else: reasons.append(f'15M leader not confirmed (leader={ldir}, activeKFOO={active15})')
    if kfoo_ok: reasons.append(f'KFOO confirmed TF={tf_pct:.1f}% IND={ind_pct:.1f}%')
    else: reasons.append(f'KFOO incomplete/weak TF={tf_pct:.1f}% IND={ind_pct:.1f}%')

    if not gravity or not leader_ok or not kfoo_ok:
        return Signal(level='WAIT',direction=g4 or ldir or 'neutral',score=0.40 if gravity else 0.20,reasons=reasons,setup_ready=False,entry_ready=False,timestamp_utc=datetime.now(timezone.utc).isoformat())

    allow_setup, allow_entry, context_reasons, context = _market_gate(analysis, g4)
    reasons.extend(context_reasons)
    if not allow_setup:
        return Signal(level='WAIT',direction=g4,score=0.30,reasons=reasons,setup_ready=False,entry_ready=False,market_context=context,timestamp_utc=datetime.now(timezone.utc).isoformat())

    if not bool(timing.get('leader_closed')):
        return Signal(level='STRONG_SETUP',direction=g4,score=0.85,reasons=reasons+['waiting for 15M candle close'],setup_ready=True,entry_ready=False,market_context=context,timestamp_utc=datetime.now(timezone.utc).isoformat())

    a5=analysis.get('5m') or {}; a3=analysis.get('3m') or {}
    d5=_dir(((a5.get('analysis') or {}).get('kfoo_table_direction') or {}).get('bias')) or _dir((a5.get('analysis') or {}).get('direction'))
    d3=_dir(((a3.get('analysis') or {}).get('kfoo_table_direction') or {}).get('bias')) or _dir((a3.get('analysis') or {}).get('direction'))
    entry=d5==g4 and d3==g4 and bool((a5.get('analysis') or {}).get('kfoo_table_detected')) and bool((a3.get('analysis') or {}).get('kfoo_table_detected')) and allow_entry
    if entry:
        return Signal(level='STRONG_ENTRY',direction=g4,score=0.95,reasons=reasons+['5M and 3M timing aligned'],setup_ready=True,entry_ready=True,market_context=context,timestamp_utc=datetime.now(timezone.utc).isoformat())
    hold_reason='high-risk entry hold' if not allow_entry else f'timing not aligned (5M={d5}, 3M={d3})'
    return Signal(level='STRONG_SETUP',direction=g4,score=0.90,reasons=reasons+[hold_reason],setup_ready=True,entry_ready=False,market_context=context,timestamp_utc=datetime.now(timezone.utc).isoformat())


def finalize(sig: Signal, payload_core: dict)->Signal:
    raw=json.dumps({'level':sig.level,'direction':sig.direction,'core':payload_core},sort_keys=True,ensure_ascii=False)
    sig.event_key=hashlib.sha256(raw.encode()).hexdigest()[:24]
    return sig
