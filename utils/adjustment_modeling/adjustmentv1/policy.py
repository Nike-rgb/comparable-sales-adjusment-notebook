from __future__ import annotations
from dataclasses import dataclass

@dataclass
class CostAssumptions:
    # Lot & site
    lot_psf: float = 3.0
    fence_token: float = 1500.0
    site_pos_pct: float = 0.01
    site_neg_pct: float = -0.02

    # Structure/design
    age_per_year: float = 600.0
    style_token: float = 1500.0
    construction_token: float = 1200.0
    foundation_token: float = 1000.0
    roof_token: float = 1000.0

    # Size & rooms
    gla_factor_psf: float = 0.35          # multiplier applied to market psf
    above_grade_psf: float = 40.0
    below_grade_finished_psf: float = 50.0
    below_grade_unfinished_psf: float = 15.0
    v_bed: float = 9000.0
    v_bath_full: float = 12000.0
    v_bath_half: float = 6000.0
    v_story: float = 3000.0

    # Condition & interior
    quality_pct_per_step: float = 0.04    # Q1-6 step on building value
    condition_pct_per_step: float = 0.025 # C1-6 step on building value
    interior_token: float = 1000.0
    fireplace_each: float = 6000.0

    # Amenities & utilities
    hvac_central_bonus: float = 2000.0
    whole_house_fan_bonus: float = 800.0
    multi_unit_cooling_bonus: float = 1200.0
    solar_contrib: float = 10000.0
    natural_gas_bonus: float = 1500.0
    pv_on_grid_bonus: float = 2000.0
    garage_space_value: float = 25000.0  # per space proxy (space x sqft x $/sf simplified)
    patio_pkg: float = 4000.0
    deck_pkg: float = 5000.0
    porch_pkg: float = 3000.0

    # Transactional
    monthly_market_trend_pct: float = 0.0025 # 0.25% / month
    hoa_years_capitalized: float = 1.0       # months of HOA to capitalize (1 year)

    # Location & schools
    different_neighborhood_pct: float = -0.01
    different_subdivision_pct: float = -0.005
    different_school_district_pct: float = -0.005
    school_rating_pct_per_point: float = 0.002 # 0.2% per rating point
    waterfront_pct: float = 0.03

    # Building share basis for % steps
    building_share: float = 0.60

@dataclass
class AdjustmentPolicy:
    line_cap_pct: float = 0.09
    total_cap_pct: float = 0.27
    market_each_cap: float = 0.03
    market_total_cap: float = 0.05
