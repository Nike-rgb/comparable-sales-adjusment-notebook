from __future__ import annotations
import json, math
from pathlib import Path
from typing import Tuple, Any, Dict, List
import pandas as pd
import numpy as np

def _num(x):
    try:
        if x is None: return np.nan
        if isinstance(x, (int,float)): return float(x)
        s = str(x).replace(',', '').strip()
        return float(s)
    except Exception:
        return np.nan

def _na_to_none(x):
    return None if (x is None or (isinstance(x,float) and math.isnan(x))) else x

def _to_row(d: Dict[str, Any], role: str) -> Dict[str, Any]:
    """
    Shared transformation logic for converting a property dict to a normalized row.
    Extracted from load_homesage to be reused by load_homesage_from_dict.
    """
    # core numerics
    sale_price = _num(d.get('sold_1_price'))
    sale_date = d.get('sold_1_date')
    gla = _num(d.get('sf') or d.get('above_grade_size') or d.get('total_size'))
    above = _num(d.get('above_grade_size'))
    below = _num(d.get('below_grade_size'))
    lot_sqft = _num(d.get('lot_sqft') or (d.get('lot_acres') and float(d['lot_acres'])*43560))
    beds = _num(d.get('beds'))
    baths = _num(d.get('baths'))  # Combined baths field
    baths_full = _num(d.get('baths_full'))
    baths_half = _num(d.get('baths_half'))
    stories = _num(d.get('stories'))
    year_built = _num(d.get('year_built'))

    # parking/garage (prefer explicit spaces, then fallback total spaces)
    garage_spaces = _num(d.get('garage_spaces_from_features'))
    if math.isnan(garage_spaces):
        garage_spaces = _num(d.get('parking_total_spaces'))

    # location & schools
    school_ratings = d.get('school_ratings') or []
    avg_school_rating = np.nan
    if isinstance(school_ratings, list) and school_ratings:
        vals = [ _num(x.get('rating')) for x in school_ratings if x and x.get('rating') is not None ]
        vals = [v for v in vals if not (isinstance(v,float) and math.isnan(v))]
        if len(vals):
            avg_school_rating = float(np.mean(vals))

    row = {
        'role': role,
        'address': d.get('address'),
        'sale_price': sale_price,
        'sale_date': sale_date,
        'gla': gla,
        'above_grade_size': above,
        'below_grade_size': below,
        'lot_sqft': lot_sqft,
        'beds': beds,
        'baths': baths,  # Add combined baths field
        'baths_full': baths_full,
        'baths_half': baths_half,
        'stories': stories,
        'year_built': year_built,
        'style': d.get('style') or '',
        'construction_materials': d.get('construction_materials') or '',
        'foundation_details': d.get('foundation_details') or '',
        'roof': d.get('roof') or '',
        'basement': bool(d.get('basement')) if d.get('basement') is not None else False,
        'cooling': d.get('cooling') or '',
        'heating': d.get('heating') or '',
        'garage_spaces': garage_spaces,
        'parking_desc': d.get('parking_desc_from_building_info') or '',
        'fencing': d.get('fencing') or '',
        'lot_features_text': d.get('lot_features_text') or '',
        'interior_features': d.get('interior_features') or [],
        'flooring': d.get('flooring') or '',
        'property_condition_label': d.get('property_condition_label') or '',
        'hoa': bool(d.get('hoa')) if d.get('hoa') is not None else False,
        'hoa_fee': _num(d.get('hoa_fee')),
        'neighborhood': d.get('neighborhood') or '',
        'subdivision': d.get('subdivision') or '',
        'school_district': d.get('school_district') or '',
        'waterfront': (d.get('waterfront') or '').strip(),
        # utilities/energy
        'electric': bool(d.get('electric')) if d.get('electric') is not None else False,
        'electric_220_volts': bool(d.get('electric_220_volts')) if d.get('electric_220_volts') is not None else False,
        'electric_pv_on_grid': bool(d.get('electric_pv_on_grid')) if d.get('electric_pv_on_grid') is not None else False,
        'natural_gas_connected': bool(d.get('natural_gas_connected')) if d.get('natural_gas_connected') is not None else False,
        'solar': bool(d.get('solar')) if d.get('solar') is not None else False,
        'utilities_raw': d.get('utilities_raw') or [],
        # school rating aggregate
        'avg_school_rating': avg_school_rating
    }
    return row

def load_homesage(path: str | Path) -> Tuple[pd.Series, pd.DataFrame]:
    """Load a *Homesage-normalized* JSON that already contains:
       { 'subject': {...}, 'comparables': [ {...}, ... ] }

       We pull robustly with natural-language tolerant keys and store
       everything in a consistent schema expected by the engine.
    """
    data = json.loads(Path(path).read_text(encoding='utf-8'))

    subj = _to_row(data['subject'], 'subject')
    comps = [_to_row(x, 'comp') for x in data.get('comparables', [])]

    subject = pd.Series(subj)
    comps_df = pd.DataFrame(comps)
    return subject, comps_df

def load_homesage_from_dict(data: Dict[str, Any]) -> Tuple[pd.Series, pd.DataFrame]:
    """Load from an already-parsed dict (e.g., from POST request body).
       Expects same structure as load_homesage:
       { 'subject': {...}, 'comparables': [ {...}, ... ] }
       
       Returns the same (pd.Series, pd.DataFrame) tuple as load_homesage.
    """
    subj = _to_row(data['subject'], 'subject')
    comps = [_to_row(x, 'comp') for x in data.get('comparables', [])]

    subject = pd.Series(subj)
    comps_df = pd.DataFrame(comps)
    return subject, comps_df