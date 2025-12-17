"""
Merger utility to combine HomeSage and DataFiniti data with redundancy
Priority: HomeSage first, DataFiniti fills null values
"""

import re
import datetime
from datetime import datetime

def _extract_foundation(construction_details):
    """Extract foundation info from construction details string"""
    if not construction_details:
        return None
    match = re.search(r'Foundation[:\s]+([^,]+)', construction_details, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _extract_fencing(lot_features):
    """Extract fencing info from lot features"""
    if not lot_features:
        return None
    if "fenc" in lot_features.lower():
        match = re.search(r'Fencing[:\s]+([^,]+)', lot_features, re.IGNORECASE)
        return match.group(1).strip() if match else "Fenced"
    return None


def _build_utilities_raw(df_prop):
    """Build utilities_raw array from DataFiniti fields"""
    utilities = []
    
    if df_prop.get("heating_types"):
        utilities.append(f"Heating: {df_prop['heating_types']}")
    if df_prop.get("cooling_types"):
        utilities.append(f"Cooling: {df_prop['cooling_types']}")
    if df_prop.get("water_source"):
        utilities.append(f"Water: {df_prop['water_source']}")
    if df_prop.get("sewer_type"):
        utilities.append(f"Sewer: {df_prop['sewer_type']}")
    
    return utilities if utilities else []

# Field mapping: HomeSage 44 fields -> DataFiniti equivalents
FIELD_MAPPING = {
    "address": lambda df: f"{df.get('address', '')}, {df.get('city', '')}, {df.get('state', '')}, {df.get('zip_code', '')}".strip(", "),
    "list_date": "list_date",
    "status": "status",
    "listing_price": "list_price",
    "sf": "living_sqft",
    "psf": "price_per_sqft",
    "dom": lambda df: (
    (datetime.fromisoformat(df["sale_date"].strip()) - datetime.fromisoformat(df["list_date"].strip())).days
    if df.get("sale_date") and df.get("list_date") else None
    ),
    "heating": lambda df: df.get("heating_types"),
    "beds": "beds",
    "baths": lambda df: df.get("baths_total"),
    "stories": "stories",
    "basement": lambda df: df.get("basement_type") is not None and df.get("basement_type") != "None",
    "style": lambda df: df.get("architectural_style") or df.get("design_style"),
    "new_construction": lambda df: (
        df.get("year_built") is not None and df.get("list_date") is not None and
        (datetime.fromisoformat(df["list_date"]).year - df["year_built"] <= 2)
    ),
    "year_built": "year_built",
    "cooling": lambda df: df.get("cooling_types", "").split(",")[0].strip() if df.get("cooling_types") else None,
    "parking": "garage_spaces",
    "property_type": "property_type",
    "structure": lambda df: (
    "Attached" if any(pt in (df.get("property_type") or "").lower() for pt in ["townhouse", "row house", "duplex", "apartment unit"]) 
    else "Detached" if any(pt in (df.get("property_type") or "").lower() for pt in ["single family dwelling", "single family residence", "house"]) 
    else None 
),
    "above_grade_size": "floor1_sqft",
    "below_grade_size": "basement_area_sqft",
    "total_sqft": "living_sqft",
    "foundation_details": lambda df: _extract_foundation(df.get("construction_details", "")),
    "construction_materials": "construction_materials",
    "building_exterior_type": None,  
    "roof": "roof_type",
    "flooring": "flooring_types",
    "lot_acres": "lot_acres",
    "lot_sqft": "lot_sqft",
    "fencing": lambda df: df.get("fence") or _extract_fencing(df.get("lot_features", "")),
    "lot_features_text": lambda df: df.get("lot_features") or df.get("lot_description"),
    "parking_total_spaces": "garage_spaces",
    "parking_features": "parking_details",
    "interior_features": lambda df: [df.get("interior_features")] if df.get("interior_features") else [],
    "electric": lambda df: "electric" in df.get("heating_types", "").lower() or "electric" in df.get("appliances", "").lower(),
    "solar": lambda df: "solar" in df.get("energy_efficient_items", "").lower() if df.get("energy_efficient_items") else False,
    "water_public": lambda df: df.get("water_source", "").lower() == "public" if df.get("water_source") else None,
    "sewer": "sewer_type",
    "utilities_raw": lambda df: _build_utilities_raw(df),
    "sold_1_date": "sale_date",
    "sold_1_price": "sale_price",
    "sold_1_source_name": lambda df: df.get("listing_company") or "DataFiniti",
    "property_condition_label": "condition",
}


def parse_address_for_datafiniti(hs_address):
    """Parse HomeSage address - handles both comma and space before zip"""
    if not hs_address:
        return {"address": "", "city": "", "province": "", "postal": ""}
    
    pattern1 = r'^(.+?),\s*(.+?),\s*([A-Z]{2}),?\s*(\d{5})$'
    match = re.match(pattern1, hs_address)
    
    if match:
        return {
            "address": match.group(1).strip(),
            "city": match.group(2).strip(),
            "province": match.group(3).strip(),
            "postal": match.group(4).strip()
        }
    
    print(f"Warning: Could not parse address: {hs_address}")
    return {
        "address": hs_address,
        "city": "",
        "province": "",
        "postal": ""
    }

def convert_hs_props_to_df_format(hs_props):
    """
    Convert HomeSage props format to DataFiniti format
    
    Args:
        hs_props: Dict with properties array in HomeSage format
        
    Returns:
        Dict with properties array in DataFiniti format
    """
    df_props = {"properties": []}
    
    for prop in hs_props.get("properties", []):
        parsed = parse_address_for_datafiniti(prop.get("address", ""))
        df_prop = {
            "type": prop.get("type"),
            **parsed
        }
        df_props["properties"].append(df_prop)
    
    return df_props


def get_df_value(df_prop, field_name):
    """
    Get value from DataFiniti property based on field mapping
    
    Args:
        df_prop: DataFiniti normalized property dict
        field_name: HomeSage field name
        
    Returns:
        Value from DataFiniti or None
    """
    if field_name not in FIELD_MAPPING:
        return None
    
    mapping = FIELD_MAPPING[field_name]

    if mapping is None:
        return None
    
    if callable(mapping):
        try:
            return mapping(df_prop)
        except Exception as e:
            print(f"ERROR mapping field '{field_name}': {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    return df_prop.get(mapping)


def merge_single_property(hs_44_fields, df_normalized):
    """
    Merge a single property: fill null HomeSage values with DataFiniti
    
    Args:
        hs_44_fields: Dict with 44 HomeSage fields (some may be null)
        df_normalized: Dict with full DataFiniti normalized data
        
    Returns:
        Dict with merged 44 fields + all extra DataFiniti fields
    """
    merged = {}

    for field_name, hs_value in hs_44_fields.items():
        if hs_value is not None and hs_value != "" and hs_value != []:
            merged[field_name] = hs_value
        else:
            df_value = get_df_value(df_normalized, field_name)
            merged[field_name] = df_value if df_value is not None else hs_value
    
    for df_field, df_value in df_normalized.items():
        if df_field not in merged:
            merged[df_field] = df_value
    
    return merged


def merge_properties_by_index(hs_props, df_props):
    """
    Merge properties by index (they're already aligned)
    
    Args:
        hs_props: List of HomeSage 44-field properties
        df_props: List of DataFiniti normalized properties
        
    Returns:
        List of merged properties
    """
    merged_props = []
    
    for i, hs_prop in enumerate(hs_props):
        if i < len(df_props):
            merged_props.append(merge_single_property(hs_prop, df_props[i]))
        else:
            merged_props.append(hs_prop)
    
    return merged_props

def merge_datasets(hs_44_data, df_normalized_data):
    """
    Merge complete datasets (subject + comparables)
    """
    result = {}
    
    if "subject" in hs_44_data and "subject" in df_normalized_data:
        result["subject"] = merge_single_property(
            hs_44_data["subject"],
            df_normalized_data["subject"]
        )
    elif "subject" in hs_44_data:
        result["subject"] = hs_44_data["subject"]
    
    if "comparables" in hs_44_data and "comparables" in df_normalized_data:
        result["comparables"] = merge_properties_by_index(  
            hs_44_data["comparables"],
            df_normalized_data["comparables"]
        )
    elif "comparables" in hs_44_data:
        result["comparables"] = hs_44_data["comparables"]
    
    return result