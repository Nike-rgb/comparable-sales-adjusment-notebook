from __future__ import annotations
from typing import Tuple, Dict
from ..utils import txt, num, contains_any
from ..policy import CostAssumptions

def cooling(subject, comp, costs: CostAssumptions):
    s = txt(subject.get('cooling')).lower()
    c = txt(comp.get('cooling')).lower()
    def sc(v: str):
        score = 0.0
        if 'central' in v: score += costs.hvac_central_bonus
        if 'whole house fan' in v: score += costs.whole_house_fan_bonus
        if 'multi' in v or 'multiunits' in v: score += costs.multi_unit_cooling_bonus
        if 'wall unit' in v or 'window unit' in v: score -= 500.0
        return score
    adj = sc(s) - sc(c)
    return float(adj), {'subject': s, 'comp': c}

def heating(subject, comp, costs: CostAssumptions):
    # Homesage normalized may not include explicit heating; infer via natural gas
    s_ng = bool(subject.get('natural_gas_connected'))
    c_ng = bool(comp.get('natural_gas_connected'))
    d = (1 if s_ng else 0) - (1 if c_ng else 0)
    return float(d*costs.natural_gas_bonus), {'subject_gas': s_ng, 'comp_gas': c_ng, 'bonus_each': costs.natural_gas_bonus}

def garage_parking(subject, comp, costs: CostAssumptions):
    s = num(subject.get('garage_spaces')); c = num(comp.get('garage_spaces'))
    s = 0.0 if s!=s else s; c = 0.0 if c!=c else c
    d = s - c
    return float(d*costs.garage_space_value), {'delta_spaces': d, 'per_space': costs.garage_space_value}

def porch_deck_patio(subject, comp, costs: CostAssumptions):
    s = f"{txt(subject.get('lot_features_text'))}"
    c = f"{txt(comp.get('lot_features_text'))}"
    def flag(v: str, token: str): return (token in v.lower())
    adj = 0.0
    meta = {}
    for token, pkg, name in [('porch', costs.porch_pkg, 'porch'),
                             ('patio', costs.patio_pkg, 'patio'),
                             ('deck', costs.deck_pkg, 'deck')]:
        sv = flag(s, token); cv = flag(c, token)
        d = (1 if sv else 0) - (1 if cv else 0)
        adj += d * pkg
        meta[name] = {'subject': sv, 'comp': cv, 'delta': d, 'pkg': pkg}
    return float(adj), meta

def energy_utilities(subject, comp, costs: CostAssumptions):
    s_solar = bool(subject.get('solar'))
    c_solar = bool(comp.get('solar'))
    s_pv = bool(subject.get('electric_pv_on_grid'))
    c_pv = bool(comp.get('electric_pv_on_grid'))
    d = (1 if s_solar else 0) - (1 if c_solar else 0)
    d += (1 if s_pv else 0) - (1 if c_pv else 0)
    adj = d * (0.5*costs.solar_contrib + 0.5*costs.pv_on_grid_bonus)
    return float(adj), {'subject_solar': s_solar, 'comp_solar': c_solar, 'subject_pv': s_pv, 'comp_pv': c_pv}
