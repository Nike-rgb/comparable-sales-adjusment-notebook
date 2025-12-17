from __future__ import annotations
import numpy as np
import pandas as pd

def similarity_weight(subj: pd.Series, comp: pd.Series, policy) -> float:
    dist = np.nan
    if pd.notna(subj.get('latitude')) and pd.notna(subj.get('longitude')) and pd.notna(comp.get('latitude')) and pd.notna(comp.get('longitude')):
        dy = (subj['latitude'] - comp['latitude']) * 69.0
        dx = (subj['longitude'] - comp['longitude']) * 54.6
        dist = np.sqrt(dx*dx + dy*dy)
    dist_pen = (1.0 / (1.0 + policy.distance_decay * (dist if dist==dist else 0.0)))

    size_pen = 1.0 / (1.0 + 0.001 * abs((subj.get('gross_living_area') or 0) - (comp.get('gross_living_area') or 0)))
    age_pen  = 1.0 / (1.0 + 0.02  * abs((subj.get('year_built') or 0) - (comp.get('year_built') or 0)))

    raw = dist_pen * size_pen * age_pen
    return float(max(0.2, min(1.0, raw)) * 100.0)
