from __future__ import annotations
from typing import Tuple, Dict
from ..utils import num
from ..policy import CostAssumptions

def age_year_built(subject, comp, costs: CostAssumptions):
    s = num(subject.get('year_built')); c = num(comp.get('year_built'))
    if s!=s or c!=c: return 0.0, {'note':'missing year_built'}
    # older comp (lower year) inferior → upward adj to comp
    d_years = (s - c)
    adj = d_years * costs.age_per_year
    return float(adj), {'delta_years': d_years, 'per_year': costs.age_per_year}

def style(subject, comp, costs: CostAssumptions):
    s = (subject.get('style') or '').lower()
    c = (comp.get('style') or '').lower()
    if s == c or not s or not c: return 0.0, {'note':'same or missing style'}
    return costs.style_token, {'subject': s, 'comp': c, 'token': costs.style_token}

def construction(subject, comp, costs: CostAssumptions):
    s = (subject.get('construction_materials') or '').lower()
    c = (comp.get('construction_materials') or '').lower()
    if s == c or not s or not c: return 0.0, {'note':'same or missing'}
    return costs.construction_token, {'subject': s, 'comp': c, 'token': costs.construction_token}

def foundation(subject, comp, costs: CostAssumptions):
    s = (subject.get('foundation_details') or '').lower()
    c = (comp.get('foundation_details') or '').lower()
    if s == c or not s or not c: return 0.0, {'note':'same or missing'}
    return costs.foundation_token, {'subject': s, 'comp': c, 'token': costs.foundation_token}

def roof(subject, comp, costs: CostAssumptions):
    s = (subject.get('roof') or '').lower()
    c = (comp.get('roof') or '').lower()
    if s == c or not s or not c: return 0.0, {'note':'same or missing'}
    return costs.roof_token, {'subject': s, 'comp': c, 'token': costs.roof_token}
