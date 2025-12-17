from __future__ import annotations
from typing import Tuple, Dict
from ..utils import num, site_token_score
from ..policy import CostAssumptions

def lot_size(subject, comp, costs: CostAssumptions):
    s = num(subject.get('lot_sqft'))
    c = num(comp.get('lot_sqft'))
    d = (0.0 if (s!=s or c!=c) else s - c)
    adj = d * costs.lot_psf
    return float(adj), {'delta_sqft': d, 'lot_psf': costs.lot_psf}

def lot_features_fencing(subject, comp, costs: CostAssumptions):
    # Basic tokenization
    desc_s = f"{subject.get('fencing') or ''} | {subject.get('lot_features_text') or ''}"
    desc_c = f"{comp.get('fencing') or ''} | {comp.get('lot_features_text') or ''}"
    sc_s = site_token_score(desc_s)
    sc_c = site_token_score(desc_c)
    d = sc_s - sc_c
    # positive token ~ +1% * indicated price; negative token ~ -2% (captured via score sign)
    # here we convert score differences into a flat $ using fence_token anchor
    adj = d * costs.fence_token
    return float(adj), {'subject_score': sc_s, 'comp_score': sc_c, 'delta_score': d, 'token_value': costs.fence_token}
