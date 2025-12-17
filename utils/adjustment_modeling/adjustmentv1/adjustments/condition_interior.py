from __future__ import annotations
from typing import Tuple, Dict
import re
from ..policy import CostAssumptions
from ..utils import txt

Q_MAP = {'luxury':2,'custom':3,'excellent':2,'above average':3,'average':4,'economy':5,'basic':6}
C_MAP = {'new':2,'excellent':2,'renovated':3,'updated':3,'good':3,'average':4,'typical':4,'outdated':5,'fair':5,'poor':6}

def _q_from_text(style_text: str) -> int|None:
    s = txt(style_text).lower()
    for k,v in Q_MAP.items():
        if k in s: return v
    return None

def _c_from_text(cond_text: str) -> int|None:
    s = txt(cond_text).lower()
    for k,v in C_MAP.items():
        if k in s: return v
    return None

def quality(subject, comp, costs: CostAssumptions, indicated_value: float):
    # Use style text as a weak proxy for Q if not provided explicitly
    qs = _q_from_text(subject.get('style')) or 4
    qc = _q_from_text(comp.get('style')) or 4
    steps = qs - qc
    bldg_val = indicated_value * 0.60
    adj = -steps * costs.quality_pct_per_step * bldg_val
    return float(adj), {'Q_subject': qs, 'Q_comp': qc, 'steps': steps, 'pct_per_step': costs.quality_pct_per_step, 'building_basis': bldg_val}

def condition(subject, comp, costs: CostAssumptions, indicated_value: float):
    cs = _c_from_text(subject.get('property_condition_label')) or 4
    cc = _c_from_text(comp.get('property_condition_label')) or 4
    steps = cs - cc
    bldg_val = indicated_value * 0.60
    adj = -steps * costs.condition_pct_per_step * bldg_val
    return float(adj), {'C_subject': cs, 'C_comp': cc, 'steps': steps, 'pct_per_step': costs.condition_pct_per_step, 'building_basis': bldg_val}

def flooring(subject, comp, costs: CostAssumptions):
    # Simple token scoring: wood/tile superior to vinyl/carpet
    def score(s: str):
        s = txt(s).lower()
        sc = 0
        if 'hardwood' in s or 'wood' in s: sc += 2
        if 'tile' in s: sc += 1
        if 'vinyl' in s: sc -= 1
        if 'carpet' in s: sc -= 1
        return sc
    ss = score(subject.get('flooring'))
    cs = score(comp.get('flooring'))
    d = ss - cs
    return float(d*costs.interior_token), {'subject_score': ss, 'comp_score': cs, 'delta': d, 'token': costs.interior_token}

def interior_features(subject, comp, costs: CostAssumptions):
    # Look for premium interior tokens
    PREMIUM = ['cathedral', 'vaulted', 'open beam', 'skylight', 'skylight tube']
    s_list = subject.get('interior_features') or []
    c_list = comp.get('interior_features') or []
    s_txt = ' | '.join([txt(x).lower() for x in s_list])
    c_txt = ' | '.join([txt(x).lower() for x in c_list])
    def sc(t): return sum(1 for k in PREMIUM if k in t)
    ss, cs = sc(s_txt), sc(c_txt)
    d = ss - cs
    return float(d*costs.interior_token), {'subject_score': ss, 'comp_score': cs, 'delta': d, 'token': costs.interior_token}

def fireplace(subject, comp, costs: CostAssumptions):
    # Try to infer from interior features or parking_desc text (rare)
    def has_fireplace(items, extra_text):
        s = ' | '.join([txt(x).lower() for x in (items or [])]) + ' | ' + txt(extra_text).lower()
        return ('fireplace' in s) or ('fire place' in s) or ('woodburn' in s)
    s_fp = 1 if has_fireplace(subject.get('interior_features'), subject.get('parking_desc')) else 0
    c_fp = 1 if has_fireplace(comp.get('interior_features'), comp.get('parking_desc')) else 0
    d = s_fp - c_fp
    return float(d*costs.fireplace_each), {'subject_fireplace': bool(s_fp), 'comp_fireplace': bool(c_fp), 'delta': d, 'each': costs.fireplace_each}
