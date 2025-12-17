from __future__ import annotations
import re, math
import numpy as np
import pandas as pd

POS_SITE_TOKENS = ['cul-de-sac', 'park', 'view', 'greenbelt', 'waterfront', 'backs to open']
NEG_SITE_TOKENS = ['busy road', 'highway', 'arterial', 'rail', 'industrial', 'power line', 'slope', 'steep']

def txt(x): 
    return (str(x) if x is not None else '').strip()

def num(x):
    try:
        if x is None: return np.nan
        if isinstance(x, (int,float)): return float(x)
        s = str(x).replace(',', '').strip()
        return float(s)
    except Exception:
        return np.nan

def months_between(d1: str|None, d2: str|None) -> float:
    if not d1 or not d2: return 0.0
    try:
        a = pd.to_datetime(d1); b = pd.to_datetime(d2)
        return max(-120.0, min(120.0, (a.year - b.year)*12 + (a.month - b.month)))
    except Exception:
        return 0.0

def site_token_score(s: str) -> float:
    s = txt(s).lower()
    score = 0.0
    for t in POS_SITE_TOKENS:
        if t in s: score += 1.0
    for t in NEG_SITE_TOKENS:
        if t in s: score -= 1.0
    return score

def has_token(s: str, tokens: list[str]) -> bool:
    s = txt(s).lower()
    return any(t in s for t in tokens)

def contains_any(items, tokens: list[str]) -> bool:
    if not isinstance(items, list): return False
    s = " | ".join([txt(x) for x in items]).lower()
    return any(t in s for t in tokens)

def safe_delta(a, b):
    if a is None or (isinstance(a,float) and math.isnan(a)): a = 0.0
    if b is None or (isinstance(b,float) and math.isnan(b)): b = 0.0
    return float(a - b)
