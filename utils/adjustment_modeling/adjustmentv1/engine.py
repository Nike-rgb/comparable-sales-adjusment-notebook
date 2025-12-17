from __future__ import annotations
import numpy as np
import pandas as pd
from .policy import AdjustmentPolicy, CostAssumptions
from .adjustments import transactional, location_edu_waterfront, site, structure, rooms_size, condition_interior, amenities_utilities, external_placeholders

def _cap(x: float, base: float, pct: float) -> float:
    cap = abs(pct) * (base or 0.0)
    return float(max(-cap, min(cap, x)))

def run(subject: pd.Series, comps: pd.DataFrame, policy: AdjustmentPolicy, costs: CostAssumptions):
    # indicated value basis (for % adjustments on building component)
    indicated_value = float(np.nanmedian(comps['sale_price'])) if 'sale_price' in comps.columns else float('nan')

    rows = []
    for _, comp in comps.iterrows():
        base = float(comp.get('sale_price') or 0.0)
        line_base = max(base, 1.0)

        # --- Transactional
        adj_time, d_time = transactional.sale_date(subject, comp, costs, indicated_value)
        adj_hoa, d_hoa = transactional.hoa_fee(subject, comp, costs)

        # --- Location
        adj_loc, d_loc = location_edu_waterfront.location_school_water(subject, comp, costs, indicated_value)

        # --- Site
        adj_lot, d_lot = site.lot_size(subject, comp, costs)
        adj_fence, d_fence = site.lot_features_fencing(subject, comp, costs)

        # --- Structure / Design / Quality
        adj_age, d_age = structure.age_year_built(subject, comp, costs)
        adj_style, d_style = structure.style(subject, comp, costs)
        adj_constr, d_constr = structure.construction(subject, comp, costs)
        adj_found, d_found = structure.foundation(subject, comp, costs)
        adj_roof, d_roof = structure.roof(subject, comp, costs)

        # --- Size & Rooms
        adj_gla, d_gla = rooms_size.gla(subject, comp, comps, costs)
        adj_abv, d_abv = rooms_size.above_grade(subject, comp, costs)
        adj_blw, d_blw = rooms_size.below_grade(subject, comp, costs)
        adj_bed, d_bed = rooms_size.bedrooms(subject, comp, costs)
        adj_bath, d_bath = rooms_size.bathrooms(subject, comp, costs)
        adj_story, d_story = rooms_size.stories(subject, comp, costs)

        # --- Condition & Interior
        adj_qual, d_qual = condition_interior.quality(subject, comp, costs, indicated_value)
        adj_cond, d_cond = condition_interior.condition(subject, comp, costs, indicated_value)
        adj_floor, d_floor = condition_interior.flooring(subject, comp, costs)
        adj_int, d_int = condition_interior.interior_features(subject, comp, costs)
        adj_fp, d_fp = condition_interior.fireplace(subject, comp, costs)

        # --- Amenities & Utilities
        adj_cool, d_cool = amenities_utilities.cooling(subject, comp, costs)
        adj_heat, d_heat = amenities_utilities.heating(subject, comp, costs)
        adj_gar, d_gar = amenities_utilities.garage_parking(subject, comp, costs)
        adj_out, d_out = amenities_utilities.porch_deck_patio(subject, comp, costs)
        adj_energy, d_energy = amenities_utilities.energy_utilities(subject, comp, costs)

        # --- External & Exemptions (placeholders unless provided elsewhere)
        adj_ext, d_ext = external_placeholders.external_market(subject, comp)
        adj_exm, d_exm = external_placeholders.exemptions(subject, comp)

        # cap line items
        line_items = {
            'Time (Sale Date)': _cap(adj_time, line_base, policy.line_cap_pct),
            'HOA Fees': _cap(adj_hoa, line_base, policy.line_cap_pct),

            'Neighborhood/Subdivision/Schools/Waterfront': _cap(adj_loc, line_base, policy.line_cap_pct),

            'Lot Size': _cap(adj_lot, line_base, policy.line_cap_pct),
            'Lot Features / Fencing': _cap(adj_fence, line_base, policy.line_cap_pct),

            'Age / Year Built': _cap(adj_age, line_base, policy.line_cap_pct),
            'Style': _cap(adj_style, line_base, policy.line_cap_pct),
            'Construction Materials': _cap(adj_constr, line_base, policy.line_cap_pct),
            'Foundation': _cap(adj_found, line_base, policy.line_cap_pct),
            'Roof': _cap(adj_roof, line_base, policy.line_cap_pct),

            'GLA': _cap(adj_gla, line_base, policy.line_cap_pct),
            'Above Grade Size': _cap(adj_abv, line_base, policy.line_cap_pct),
            'Below Grade Size / Basement': _cap(adj_blw, line_base, policy.line_cap_pct),
            'Bedrooms': _cap(adj_bed, line_base, policy.line_cap_pct),
            'Bathrooms': _cap(adj_bath, line_base, policy.line_cap_pct),
            'Stories': _cap(adj_story, line_base, policy.line_cap_pct),

            'Quality (Q)': _cap(adj_qual, line_base, policy.line_cap_pct),
            'Condition (C)': _cap(adj_cond, line_base, policy.line_cap_pct),
            'Flooring': _cap(adj_floor, line_base, policy.line_cap_pct),
            'Interior Features': _cap(adj_int, line_base, policy.line_cap_pct),
            'Fireplace': _cap(adj_fp, line_base, policy.line_cap_pct),

            'Cooling': _cap(adj_cool, line_base, policy.line_cap_pct),
            'Heating': _cap(adj_heat, line_base, policy.line_cap_pct),
            'Garage / Parking': _cap(adj_gar, line_base, policy.line_cap_pct),
            'Porch / Deck / Patio': _cap(adj_out, line_base, policy.line_cap_pct),
            'Energy / Utilities': _cap(adj_energy, line_base, policy.line_cap_pct),

            'External Market (placeholders)': _cap(adj_ext, line_base, policy.line_cap_pct),
            'Exemptions (placeholders)': _cap(adj_exm, line_base, policy.line_cap_pct),
        }

        net_phys = float(sum(line_items.values()))
        net_phys = float(max(-policy.total_cap_pct*line_base, min(policy.total_cap_pct*line_base, net_phys)))
        price_phys = base + net_phys

        row = {
            'Comparable': comp.get('address'),
            'Base Sale Price': base,
            **line_items,
            'Net Adjustment (Property)': net_phys,
            'Adjusted Price (Property)': price_phys,
            'META:Time': d_time, 'META:HOA': d_hoa,
            'META:Loc': d_loc, 'META:Lot': d_lot, 'META:Fencing': d_fence,
            'META:Age': d_age, 'META:Style': d_style, 'META:Constr': d_constr, 'META:Found': d_found, 'META:Roof': d_roof,
            'META:GLA': d_gla, 'META:Above': d_abv, 'META:Below': d_blw, 'META:Bed': d_bed, 'META:Bath': d_bath, 'META:Stories': d_story,
            'META:Q': d_qual, 'META:C': d_cond, 'META:Floor': d_floor, 'META:Int': d_int, 'META:FP': d_fp,
            'META:Cool': d_cool, 'META:Heat': d_heat, 'META:Garage': d_gar, 'META:Outdoor': d_out, 'META:Energy': d_energy,
            'META:External': d_ext, 'META:Exemptions': d_exm
        }
        rows.append(row)

    grid = pd.DataFrame(rows)
    # Simple indicated value = median of adjusted comp prices
    summary = pd.DataFrame([{
        'Indicated Value (median of Adjusted Price)': float(grid['Adjusted Price (Property)'].median())
    }])
    return grid, summary
