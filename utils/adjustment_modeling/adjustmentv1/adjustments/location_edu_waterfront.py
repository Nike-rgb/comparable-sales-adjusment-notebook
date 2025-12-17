from __future__ import annotations
from typing import Tuple, Dict
import pandas as pd
from ..policy import CostAssumptions

def location_school_water(subject: pd.Series, comp: pd.Series, costs: CostAssumptions, indicated_value: float) -> Tuple[float, Dict]:
    pct = 0.0
    det = {}

    # Neighborhood
    if (subject.get('neighborhood') or '') != (comp.get('neighborhood') or ''):
        pct += costs.different_neighborhood_pct
        det['neighborhood_delta'] = costs.different_neighborhood_pct

    # Subdivision
    if (subject.get('subdivision') or '') != (comp.get('subdivision') or ''):
        pct += costs.different_subdivision_pct
        det['subdivision_delta'] = costs.different_subdivision_pct

    # School district
    if (subject.get('school_district') or '') != (comp.get('school_district') or ''):
        pct += costs.different_school_district_pct
        det['school_district_delta'] = costs.different_school_district_pct

    # School ratings (average)
    s_avg = subject.get('avg_school_rating')
    c_avg = comp.get('avg_school_rating')
    try:
        if pd.notna(s_avg) and pd.notna(c_avg):
            det['school_rating_diff'] = float(s_avg - c_avg)
            pct += (float(s_avg) - float(c_avg)) * costs.school_rating_pct_per_point
    except Exception:
        pass

    # Waterfront toggle
    s_w = str(subject.get('waterfront') or '').strip().lower()
    c_w = str(comp.get('waterfront') or '').strip().lower()
    if bool(s_w) != bool(c_w):
        pct += (costs.waterfront_pct if bool(s_w) else -costs.waterfront_pct)
        det['waterfront'] = (bool(s_w), bool(c_w))

    adj = (comp.get('sale_price') or 0.0) * pct
    det['pct_total'] = pct
    return float(adj), det
