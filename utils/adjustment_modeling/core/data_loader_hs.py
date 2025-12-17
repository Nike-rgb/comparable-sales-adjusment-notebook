from pathlib import Path
from datetime import datetime
import json, re

def _to_int(x):
    try:
        if x is None: return None
        if isinstance(x, (int, float)): return int(x)
        return int(float(str(x).replace(",", "").strip()))
    except Exception:
        return None

def _to_float(x):
    try:
        if x is None: return None
        if isinstance(x, (int, float)): return float(x)
        s = str(x).replace(",", "").strip()
        m = re.search(r"[-+]?\d*\.?\d+", s)
        return float(m.group(0)) if m else None
    except Exception:
        return None

def _to_date(x):
    if not x: return None
    try:
        return datetime.fromisoformat(str(x).replace("Z", "+00:00")).date().isoformat()
    except Exception:
        return str(x)[:10]

def _parse_utilities(values):
    """Crafted boolean flags from a list of free-form utility strings."""
    vals = [str(v) for v in (values or [])]
    joined = " | ".join(vals).lower()
    has = lambda s: s.lower() in joined

    flags = {
        # Electric
        "electric": has("electric"),
        "electric_220_volts": has("220 volts"),
        "electric_220_kitchen": has("220 volts in kitchen"),
        "electric_220_laundry": has("220 volts in laundry"),
        "electric_pv_on_grid": has("pv-on grid"),
        # Gas
        "natural_gas_connected": has("natural gas connected"),
        "natural_gas_available": has("natural gas available"),
        # Solar
        "solar": has("solar") or has("photovoltaics"),
        "photovoltaics_third_party_owned": has("photovoltaics third-party owned") or has("photovoltaics third party owned"),
        # Internet
        "internet_available": has("internet available"),
        # Water
        "water_public": has("water source: public") or (" water source:" in joined and "public" in joined),
        "water_meter_on_site": has("meter on site"),
        "water_district": has("water district"),
        # Sewer
        "sewer_public": has("public sewer"),
        "sewer_in_connected": has("in & connected"),
        "sewer_in_street": has("sewer in street"),
        # Ambiguous standalone "Public"
        "public_utility_unspecified": any(s.strip().lower() == "public" for s in vals),
    }
    return flags, values or []

def _top_two_sold_labeled(history):
    """
    Return flat labeled keys for the top 2 Sold events:
      sold_1_date, sold_1_price, sold_1_price_per_sqft, sold_1_source_listing_id, sold_1_source_name
      sold_2_date, sold_2_price, sold_2_price_per_sqft, sold_2_source_listing_id, sold_2_source_name
    Uses your existing _to_date/_to_float helpers.
    """
    def _as_sold(e):
        return {
            "date": _to_date(e.get("date")),
            "price": _to_float(e.get("price")),
            "price_per_sqft": _to_float(e.get("price_per_sqft")),
            "source_listing_id": e.get("source_listing_id"),
            "source_name": e.get("source_name"),
        }

    # 1) keep only Sold (case-insensitive, whitespace-safe)
    sold = []
    for e in (history or []):
        name = str(e.get("event_name") or "").strip().lower()
        if name == "sold":
            sold.append(_as_sold(e))

    # 2) sort newest → oldest; missing dates go last
    sold.sort(key=lambda x: (x.get("date") is None, x.get("date") or ""), reverse=False)
    sold = list(reversed(sold))  # now newest first

    # 3) flatten to labeled keys (fill None when missing)
    out = {}
    for i in (1, 2):
        ev = sold[i-1] if len(sold) >= i else None
        out[f"sold_{i}_date"] = ev["date"] if ev else None
        out[f"sold_{i}_price"] = ev["price"] if ev else None
        out[f"sold_{i}_price_per_sqft"] = ev["price_per_sqft"] if ev else None
        out[f"sold_{i}_source_listing_id"] = ev["source_listing_id"] if ev else None
        out[f"sold_{i}_source_name"] = ev["source_name"] if ev else None
    return out

def _extract_condition_label_strict(p: dict) -> str | None:
    # Exactly this path, no fallbacks:
    # p["property_condition"]["data"]["Property Condition"]  -> "Good"
    try:
        return p["property_condition"]["data"]["Property Condition"]
    except Exception:
        return None


def _flatten_property(p: dict) -> dict:
    # base
    out = {
        "address": p.get("address"),
        "list_date": _to_date(p.get("list_date")),
        "status": p.get("status"),
        "listing_price": _to_float(p.get("listing_price")),
        "estimated_value": _to_float(p.get("estimated_value")),
        "sf": _to_int(p.get("sf")),
        "psf": _to_float(p.get("psf")),
        "dom": _to_int(p.get("dom")),
    }
    # property_features
    pf = p.get("property_features") or {}
    out.update({
        "beds": _to_int(pf.get("beds")),
        "baths_full": _to_int(pf.get("full_baths")),
        "baths_half": _to_int(pf.get("half_baths")),
        "stories": _to_int(pf.get("stories")),
        "basement": bool(pf.get("basement")) if pf.get("basement") is not None else None,
        "style": pf.get("style"),
        "new_construction": bool(pf.get("new_construction")) if pf.get("new_construction") is not None else None,
        "year_built": _to_int(pf.get("year_built")),
        "cooling": pf.get("cooling"),
        "garage_spaces_from_features": _to_int(pf.get("garage")),
    })
    # location_community
    lc = p.get("location_community") or {}
    out.update({
        "property_type": lc.get("property_type"),
        "ownership": lc.get("ownership"),
        "hoa": bool(lc.get("hoa")) if lc.get("hoa") is not None else None,
        "hoa_fee": _to_float(lc.get("hoa_fee")),
        "county": lc.get("county"),
        "neighborhood": lc.get("neighborhood"),
        "subdivision": lc.get("subdivision"),
        "school_district": lc.get("school_district"),
        "structure": lc.get("structure"),
        "waterfront": lc.get("waterfront"),
    })
    # building_info
    bi = p.get("building_info") or {}
    out.update({
        "above_grade_size": _to_int(bi.get("above_grade_size")),
        "below_grade_size": _to_int(bi.get("below_grade_size")),
        "total_size": _to_int(bi.get("total_size")),
        "elevator": bi.get("elevator"),
        "foundation_details": bi.get("foundation_details"),
        "construction_materials": bi.get("construction_materials"),
        "building_exterior_type": bi.get("building_exterior_type"),
        "roof": bi.get("roof"),
        "flooring": bi.get("flooring"),
        "parking_desc_from_building_info": bi.get("parking"),
    })
    # lot
    lot = p.get("lot") or {}
    out.update({
        "lot_acres": _to_float(lot.get("lot_acres")),
        "lot_sqft": _to_float(lot.get("lot_sqft")),
        "fencing": lot.get("fencing"),
        "lot_features_text": lot.get("lot_features"),
    })
    # parking
    pk = p.get("parking") or {}
    out.update({
        "parking_total_spaces": _to_int(pk.get("total_parking_spaces")),
        "parking_features": pk.get("features"),
    })
    # interiors
    out["interior_features"] = p.get("interior_features") or []
    # utilities
    util_flags, util_raw = _parse_utilities(p.get("utilities"))
    out.update(util_flags)
    out["utilities_raw"] = util_raw
    # history
#    out["sold_events"] = _top_two_sold(p.get("property_history"))
    out.update(_top_two_sold_labeled(p.get("property_history")))

    # Property condition (strict path, no fallbacks)
    out["property_condition_label"] = _extract_condition_label_strict(p)

    # School ratings & photos unchanged
    out["school_ratings"] = p.get("school_ratings") or []
    out["photos"] = p.get("photos") or []


    # schools/photos unchanged
    out["school_ratings"] = p.get("school_ratings") or []
    out["photos"] = p.get("photos") or []
    return out

def normalize_homesage(data: dict) -> dict:
    return {
        "subject": _flatten_property(data.get("subject")) if data.get("subject") else None,
        "comparables": [_flatten_property(c) for c in (data.get("comparables") or [])]
        # 'listing_office', 'listing_details', 'home_value' intentionally not carried over
    }

# Example for file IO:
# raw = json.loads(Path("data_sub_comps_homesage.json").read_text())
# normalized = normalize_homesage(raw)
# Path("homesage_normalized.json").write_text(json.dumps(normalized, indent=2), encoding="utf-8")
