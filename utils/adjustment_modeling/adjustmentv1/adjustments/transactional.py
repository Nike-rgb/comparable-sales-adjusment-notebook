from __future__ import annotations
from typing import Tuple, Dict
import pandas as pd
from ..policy import CostAssumptions
from ..utils import months_between, num

def sale_date(subject: pd.Series, comp: pd.Series, costs: CostAssumptions, indicated_value: float) -> Tuple[float, Dict]:
    # Adjust comp price for market time difference relative to subject sale date.
    # If subject has no sale date, use comp date only (no change).
    subj_date = subject.get('sale_date')
    comp_date = comp.get('sale_date')
    m = months_between(subj_date, comp_date)
    pct = -m * costs.monthly_market_trend_pct  # older comp -> trend up; newer comp -> trend down
    adj = (comp.get('sale_price') or 0.0) * pct
    return float(adj), {'months_diff': m, 'pct_per_month': costs.monthly_market_trend_pct, 'pct_total': pct}

def hoa_fee(subject: pd.Series, comp: pd.Series, costs: CostAssumptions) -> Tuple[float, Dict]:
    s = num(subject.get('hoa_fee'))
    c = num(comp.get('hoa_fee'))
    
    # If either is NaN (missing data), return 0 - same pattern as bedrooms, stories, etc.
    if s!=s or c!=c:
        return 0.0, {'subject_hoa': None, 'comp_hoa': None, 'months_capitalized': 12.0}
    
    years = costs.hoa_years_capitalized
    months = 12.0 * years
    delta = (s - c) * months
    return float(delta), {'subject_hoa': s, 'comp_hoa': c, 'months_capitalized': months}
