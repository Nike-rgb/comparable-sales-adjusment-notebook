from __future__ import annotations
from typing import Tuple, Dict
import numpy as np
import pandas as pd
from ..utils import num
from ..policy import CostAssumptions

def _market_psf(comps: pd.DataFrame):
    v = comps[['sale_price','gla']].dropna()
    if v.empty: return 0.0
    psf = (v['sale_price'] / v['gla']).median()
    return float(psf)

def gla(subject, comp, comps_df, costs: CostAssumptions):
    base_psf = _market_psf(comps_df)
    rate = base_psf * costs.gla_factor_psf
    s = num(subject.get('gla')); c = num(comp.get('gla'))
    d = (0.0 if (s!=s or c!=c) else s - c)
    return float(d*rate), {'delta_sqft': d, 'rate_psf': rate, 'market_psf': base_psf}

def above_grade(subject, comp, costs: CostAssumptions):
    s = num(subject.get('above_grade_size')); c = num(comp.get('above_grade_size'))
    if s!=s or c!=c: return 0.0, {'note':'missing above_grade_size'}
    d = s - c
    return float(d*costs.above_grade_psf), {'delta_sqft': d, 'rate_psf': costs.above_grade_psf}

def below_grade(subject, comp, costs: CostAssumptions):
    s = num(subject.get('below_grade_size')); c = num(comp.get('below_grade_size'))
    if s!=s or c!=c: return 0.0, {'note':'missing below_grade_size'}
    d = s - c
    # No finish split in normalized → use blended
    blended = 0.5*costs.below_grade_finished_psf + 0.5*costs.below_grade_unfinished_psf
    return float(d*blended), {'delta_sqft': d, 'rate_psf': blended}

def bedrooms(subject, comp, costs: CostAssumptions):
    s = num(subject.get('beds')); c = num(comp.get('beds'))
    if s!=s or c!=c: return 0.0, {'note':'missing beds'}
    d = s - c
    return float(d*costs.v_bed), {'delta_beds': d, 'per_bed': costs.v_bed}

def bathrooms(subject, comp, costs: CostAssumptions):
    # Use combined 'baths' field instead of separate full/half
    s_baths = num(subject.get('baths'))
    c_baths = num(comp.get('baths'))
    
    # Default to 0 if NaN
    s_baths = 0.0 if s_baths!=s_baths else s_baths
    c_baths = 0.0 if c_baths!=c_baths else c_baths
    
    # Calculate adjustment using flat rate per bathroom
    delta = s_baths - c_baths
    adj = delta * costs.v_bath_full  # Using v_bath_full as the rate (12000)
    
    return float(adj), {
        'delta_baths': delta,
        'per_bath': costs.v_bath_full
    }


def stories(subject, comp, costs: CostAssumptions):
    s = num(subject.get('stories')); c = num(comp.get('stories'))
    if s!=s or c!=c: return 0.0, {'note':'missing stories'}
    d = s - c
    return float(d*costs.v_story), {'delta_stories': d, 'per_story': costs.v_story}
