# src/adjustment_modeling/core/fetch_data.py
import json
from pathlib import Path
from typing import Dict, Any, Tuple
import requests

HOMESAGE_URL = "https://developers.homesage.ai/api/properties/info/"
HOMESAGE_CONDITION_URL = "https://developers.homesage.ai/api/properties/property-condition/"


# Save path (matches your layout)
BASE_DIR = Path(r"C:\Users\Dewank Mahajan\Desktop\DKM Business\LowPropTax\DEV\DataSystemDesign\AdjustmentModellingByD-HS") ## CHANGE ACCORDINGLY
DATA_DIR = BASE_DIR / "Data"
OUTPUT_PATH = DATA_DIR / "data_sub_comps_homesage.json" ## Rename it as _subject_prop_address_file(Something)
DATA_DIR.mkdir(parents=True, exist_ok=True)


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
    tail = ", ".join([x for x in [city, prov] if x]).strip()
    return ", ".join([x for x in [addr, f"{tail} {postal}".strip()] if x]).strip(", ").strip()

def _fetch_property_condition(address: str, headers: dict) -> dict:
    try:
        resp = requests.get(
            HOMESAGE_CONDITION_URL,
            headers=headers,
            params={"property_address": address},
            timeout=30,
        )
        try:
            data = resp.json()
        except Exception:
            data = {"status": resp.status_code, "text": resp.text}
        return {"ok": resp.ok, "status": resp.status_code, "data": data}
    except Exception as e:
        return {"ok": False, "status": None, "error": str(e)}


def fetch_homesage_comps(
    props: Dict[str, Any],
    token: str,
    out_path: str | Path = OUTPUT_PATH,
) -> Tuple[Dict[str, Any], str]:
    """
    Same shape as fetch_datafiniti_comps:
      returns (result_dict, save_path)
      result_dict = {"subject": <dict>, "comparables": [<dict>, ...]}
    """
    headers = {"Authorization": token}
    subject = None
    comparables = []

    for p in props.get("properties", []):
        params = {"property_address": _full_address(p)}
        resp = requests.get(HOMESAGE_URL, headers=headers, params=params)
        try:
            payload = resp.json()
        except Exception:
            payload = {"status": resp.status_code, "text": resp.text}

        # Add condition for subject and all comps
        condition = _fetch_property_condition(_full_address(p), headers)
        if isinstance(payload, dict):
            payload["property_condition"] = condition
        else:
            payload = {"data": payload, "property_condition": condition}

        # existing assignment logic stays the same
        if p.get("type") == "subject" and subject is None:
            subject = payload
        else:
            comparables.append(payload)





    

    result = {"subject": subject, "comparables": comparables}

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result, str(out_path)
