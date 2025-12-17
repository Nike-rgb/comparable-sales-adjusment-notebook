import json
import requests
import certifi 
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

HOMESAGE_URL = "https://developers.homesage.ai/api/properties/info/"
HOMESAGE_CONDITION_URL = "https://developers.homesage.ai/api/properties/property-condition/"

def _full_address(p: Dict[str, Any]) -> str:
    """
    Homesage expects a plain full address string, e.g.:
      "9021 Phoenix Ave, Fair Oaks, CA 95628" OR "9021 Phoenix Ave, Fair Oaks"
    Use p['address'] as-is. Only if it's missing, fall back to assembling.
    """
    addr = (p.get("address") or "").strip()
    if addr:
        return addr  # send exactly what user provided
    # fallback assembly if 'address' absent
    city = p.get("city") or ""
    postal = p.get("postal") or ""
    tail = ", ".join([x for x in [city] if x]).strip()
    return ", ".join([x for x in [addr, f"{tail} {postal}".strip()] if x]).strip(", ").strip()

def _fetch_property_condition(address: str, headers: dict) -> dict:
    try:
        resp = requests.get(
            HOMESAGE_CONDITION_URL,
            headers=headers,
            params={"property_address": address},
            timeout=15,
            verify=certifi.where(), 
        )
        try:
            data = resp.json()
        except Exception:
            data = {"status": resp.status_code, "text": resp.text}
        return {"ok": resp.ok, "status": resp.status_code, "data": data}
    except Exception as e:
        return {"ok": False, "status": None, "error": str(e)}

def _fetch_single_property(p: dict, headers: dict) -> tuple:
    """
    Fetch a single property and its condition in parallel.
    Returns: (property_dict, payload_with_condition, property_type)
    """
    address = _full_address(p)
    params = {"property_address": address}
    
    try:
        resp = requests.get(
            HOMESAGE_URL,
            headers=headers,
            params=params,
            timeout=15,
            verify=certifi.where(),
        )
        
        print(f"DEBUG HS: Response for {address} - Status: {resp.status_code}")
        print(f"DEBUG HS: Response body: {resp.text[:500]}")
        
        try:
            payload = resp.json()
        except Exception:
            payload = {"status": resp.status_code, "text": resp.text}
        
        # Fetch condition
        condition = _fetch_property_condition(address, headers)
        if isinstance(payload, dict):
            payload["property_condition"] = condition
        else:
            payload = {"data": payload, "property_condition": condition}
        
        return (p, payload, p.get("type"))
    except Exception as e:
        print(f"ERROR HS: Failed to fetch {address}: {str(e)}")
        return (p, {"error": str(e)}, p.get("type"))

def fetch_homesage_comps(
    props: Dict[str, Any],
    token: str,
) -> Dict[str, Any]:
    """
    Fetches property data from Homesage API in parallel (preserving order).
    Returns: {"subject": <dict>, "comparables": [<dict>, ...]}
    """
    headers = {"Authorization": token}
    subject = None
    comparables = []
    
    properties = props.get("properties", [])
    print(f"DEBUG HS: Fetching {len(properties)} properties in parallel")
    
    # fetch all properties in parallel while preserving order
    with ThreadPoolExecutor(max_workers=min(len(properties), 10)) as executor:
        results = executor.map(
            lambda p: _fetch_single_property(p, headers),
            properties
        )
        
        for p, payload, prop_type in results:
            if prop_type == "subject" and subject is None:
                subject = payload
            else:
                comparables.append(payload)
            
    result = {"subject": subject, "comparables": comparables}
    return result