"""
Mapper to convert normalized property data to strict 44-field format
"""

def _compute_baths(baths_full, baths_half):
    """
    Combine full and half baths into a single number.
    Logic:
      - each full bath = 1
      - each half bath = 0.5
    """
    if baths_full is None and baths_half is None:
        return None
    return (baths_full or 0) + 0.5 * (baths_half or 0)



def _compute_sewer(sewer_public, sewer_in_connected, sewer_in_street):
    """
    Convert sewer booleans to descriptive string
    Priority: Public Sewer > Connected > In Street
    """
    if sewer_public:
        return "Public Sewer"
    elif sewer_in_connected:
        return "Connected"
    elif sewer_in_street:
        return "In Street"
    else:
        return None


def _compute_parking(garage_spaces, parking_desc):
    """
    Use garage_spaces if available, otherwise fall back to parking_desc
    """
    if garage_spaces is not None:
        return garage_spaces
    return parking_desc


def _map_property_to_44_fields(prop):
    """
    Map a single property object to the 44-field structure
    
    Args:
        prop: Normalized property dict
        
    Returns:
        Dict with exactly 44 fields in order
    """
    return {

        "address": prop.get("address", ""),
        "list_date": prop.get("list_date"),
        "status": prop.get("status"),
        "listing_price": prop.get("listing_price"),
        "sf": prop.get("sf"),
        "psf": prop.get("psf"),
        "dom": prop.get("dom"),
        "beds": prop.get("beds"),

        "baths": _compute_baths(
            prop.get("baths_full"),
            prop.get("baths_half")
        ),
        
        "stories": prop.get("stories"),
        "basement": prop.get("basement"),
        "style": prop.get("style", ""),
        "new_construction": prop.get("new_construction"),
        "year_built": prop.get("year_built"),
        "cooling": prop.get("cooling", ""),
        
        "parking": _compute_parking(
            prop.get("garage_spaces_from_features"),
            prop.get("parking_desc_from_building_info")
        ),
        
        "property_type": prop.get("property_type", ""),
        "structure": prop.get("structure", ""),
        "above_grade_size": prop.get("above_grade_size"),
        "below_grade_size": prop.get("below_grade_size"),
        "total_sqft": prop.get("total_size"),  
        "foundation_details": prop.get("foundation_details", ""),
        "construction_materials": prop.get("construction_materials", ""),
        "building_exterior_type": prop.get("building_exterior_type", ""),
        "roof": prop.get("roof", ""),
        "flooring": prop.get("flooring", ""),
        
        "lot_acres": prop.get("lot_acres"),
        "lot_sqft": prop.get("lot_sqft"),
        "fencing": prop.get("fencing", ""),
        "lot_features_text": prop.get("lot_features_text", ""),
        "parking_total_spaces": prop.get("parking_total_spaces"),
        "parking_features": prop.get("parking_features"),
        "interior_features": prop.get("interior_features", []),  # array
        
        "electric": prop.get("electric"),
        "solar": prop.get("solar"),
        "water_public": prop.get("water_public"),
        
        "sewer": _compute_sewer(
            prop.get("sewer_public"),
            prop.get("sewer_in_connected"),
            prop.get("sewer_in_street")
        ),
        
        "utilities_raw": prop.get("utilities_raw", []),  
        
        "sold_1_date": prop.get("sold_1_date"),
        "sold_1_price": prop.get("sold_1_price"),
        "sold_1_source_name": prop.get("sold_1_source_name"),
        "property_condition_label": prop.get("property_condition_label", ""),
    }


def map_to_44_fields(normalized_data):
    """
    Convert full normalized data structure to 44-field format
    
    Args:
        normalized_data: Dict with 'subject' and 'comparables' keys
        
    Returns:
        Dict with same structure but only 44 fields per property
    """
    result = {}
    
    if "subject" in normalized_data:
        result["subject"] = _map_property_to_44_fields(normalized_data["subject"])
    
    if "comparables" in normalized_data:
        result["comparables"] = [
            _map_property_to_44_fields(comp)
            for comp in normalized_data["comparables"]
        ]
    
    return result