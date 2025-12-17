import json
import os
import time
import requests
from typing import Dict, Any

# API Configuration
API_URL = "https://api.datafiniti.co/v4/properties/search"
TOKEN = os.environ.get("DATAFINITI_TOKEN")

if not TOKEN:
    raise ValueError("DATAFINITI_TOKEN environment variable is required")

HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}

SLEEP_BETWEEN = 1  # gentle rate limit

def _query_string(p: Dict[str, Any]) -> str:
    """
    Datafiniti expects: country:US AND address:"..." AND city:... AND province:...
    """
    return f'country:US AND address:"{p["address"]}" AND city:{p["city"]} AND province:{p["province"]}'

def _fetch_first_record(prop: dict) -> dict:
    """
    Fetch the first matching record for a given property.
    Returns empty dict if no record found or error occurs.
    """
    payload = {"query": _query_string(prop), "num_records": 1}
    
    try:
        resp = requests.post(API_URL, headers=HEADERS, json=payload, timeout=30)
        data = resp.json()
        
        # Check for records in either 'records' or 'data' field
        if isinstance(data, dict) and isinstance(data.get("records"), list) and data["records"]:
            return data["records"][0]
        if isinstance(data, dict) and isinstance(data.get("data"), list) and data["data"]:
            return data["data"][0]
    except Exception:
        pass
    
    return {}

def fetch_datafiniti_comps(props: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetches property data from Datafiniti API.
    
    Args:
        props: {"properties": [{"type": "subject", "address": "...", "city": "...", "province": "..."}, ...]}
    
    Returns:
        {"subject": <dict>, "comparables": [<dict>, ...]}
    """
    items = props.get("properties", [])
    if not items:
        raise ValueError("Input must contain a non-empty 'properties' list.")

    # Identify subject (first with type=subject) and comparables
    subject_prop = None
    comp_props = []
    
    for p in items:
        t = str(p.get("type", "")).strip().lower()
        if t == "subject" and subject_prop is None:
            subject_prop = p
        elif t == "comparable":
            comp_props.append(p)

    # Fallback: first item as subject, rest as comps if types aren't provided
    if subject_prop is None:
        subject_prop = items[0]
        if not comp_props:
            comp_props = items[1:]
    
    comp_props = comp_props[:3]  # only the next 3

    # Fetch raw records
    subject_record = _fetch_first_record(subject_prop)
    time.sleep(SLEEP_BETWEEN)

    comp_records = []
    for cp in comp_props:
        comp_records.append(_fetch_first_record(cp))
        time.sleep(SLEEP_BETWEEN)

    result = {"subject": subject_record, "comparables": comp_records}
    return result