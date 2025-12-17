# -*- coding: utf-8 -*-

import json
import math
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

ACRES_TO_SQFT = 43560.0

# ----------------------------- Regex toolbelt -----------------------------
MONEY_PAT = re.compile(r'\$\s*([\d,]+(?:\.\d{1,2})?)')
NUM_PAT = re.compile(r'([-\d.,]+)')
AREA_SQFT_PAT = re.compile(r'(\d{2,6}(?:,\d{3})?(?:\.\d+)?)\s*(?:sq\.?\s*ft|square\s*feet|sf)\b', re.I)
PCT_PAT = re.compile(r'(\d{1,2}(?:\.\d+)?)\s*%')

# Narrative mining
CRIME_PAT = re.compile(r'\b(crime rate|crime risk|criminal|safety)\b', re.I)
CLIMATE_PAT = re.compile(r'\b(natural disaster|earthquake|tornado|flood|wildfire|hurricane|climate risk)\b', re.I)
SCHOOLS_PAT = re.compile(r'\b(schools?|school ratings?)\b', re.I)
JOB_PAT = re.compile(r'\b(job market|employment|unemployment rate)\b', re.I)
INCOME_PAT = re.compile(r'\b(cost of living|median household income|family income)\b', re.I)
WEATHER_PAT = re.compile(r'\b(weather|temperature|rainfall|snowfall|year[-\s]?round)\b', re.I)
SURROUNDING_PAT = re.compile(r'^\s*for the surrounding community', re.I)
UNEMPLOYMENT_NUMBER_PAT = re.compile(r'unemployment(?:\s*rate)?[^0-9%]*?(\d{1,2}(?:\.\d+)?)\s*%', re.I)

# Appliances (efficient tokenization)
APPLIANCE_TERMS = [
    "dishwasher", "disposal", "microwave", "refrigerator", "fridge", "freezer",
    "oven", "gas oven", "electric oven", "range", "gas range", "electric range",
    "cooktop", "range hood", "hood", "washer", "dryer", "stacked washer/dryer",
    "wine fridge", "compactor", "ice maker"
]
APPLIANCE_PAT = re.compile(r'\b(' + r'|'.join([re.escape(t) for t in sorted(APPLIANCE_TERMS, key=len, reverse=True)]) + r')s?\b', re.I)

# Transport score lines
TRANSPORT_SCORE_PAT = re.compile(
    r'\b(?:(Walking|Biking|Bike|Transit)\s*Score)\s*:\s*(\d{1,3})/100(?:\s*-\s*([^-]+))?',
    re.I
)

# Feature key fuzzy match helpers
def _norm(s: Any) -> str:
    return str(s or '').strip()

def _to_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = _norm(val)
    if not s:
        return None
    s = s.replace(',', '')
    # Strip currency and percent symbols
    s = re.sub(r'[$%]', '', s)
    try:
        return float(s)
    except Exception:
        m = NUM_PAT.search(s)
        if m:
            try:
                return float(m.group(1).replace(',', ''))
            except Exception:
                return None
    return None

def _to_int(val: Any) -> Optional[int]:
    f = _to_float(val)
    return int(round(f)) if f is not None else None

def _to_bool(val: Any) -> Optional[bool]:
    if isinstance(val, bool):
        return val
    s = _norm(val).lower()
    if not s:
        return None
    if s in {"true", "yes", "y", "1"}:
        return True
    if s in {"false", "no", "n", "0", "none"}:
        return False
    return None

def _date_any(val: Any) -> Optional[str]:
    if not val:
        return None
    try:
        # Simple ISO date parsing without pandas
        if isinstance(val, str):
            # Try to parse ISO format
            val = val.replace('Z', '+00:00')
            dt = datetime.fromisoformat(val)
            return dt.date().isoformat()
    except Exception:
        return None
    return None

def _point_wkt_to_latlon(point: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse 'POINT (lon lat)' -> (lat, lon)
    """
    if not point:
        return None, None
    m = re.search(r'POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)', point)
    if not m:
        return None, None
    lon, lat = m.group(1), m.group(2)
    try:
        return float(lat), float(lon)
    except Exception:
        return None, None

def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> Optional[float]:
    try:
        r = 3958.7613
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dl = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return r * c
    except Exception:
        return None

def _join(values: Iterable[Any], sep=", ") -> Optional[str]:
    vals = []
    for v in values or []:
        s = _norm(v)
        if s:
            vals.append(s)
    return sep.join(vals) if vals else None

# ----------------------------- Feature index -----------------------------
def features_index(features: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    Build a case-insensitive index: 'key_lower' -> list of string values.
    """
    idx: Dict[str, List[str]] = {}
    for f in features or []:
        k = _norm(f.get('key')).lower()
        if not k:
            continue
        vals = f.get('value', [])
        if isinstance(vals, list):
            sv = [v for v in map(_norm, vals) if v]
        else:
            sv = [_norm(vals)] if _norm(vals) else []
        idx.setdefault(k, []).extend(sv)
    return idx

def find_feat(idx: Dict[str, List[str]], *keys_contains: str) -> List[str]:
    pats = [kc.lower() for kc in keys_contains if kc]
    outs: List[str] = []
    for k, vs in idx.items():
        if any(p in k for p in pats):
            outs.extend(vs)
    return outs

def first_number_from_texts(texts: List[str]) -> Optional[float]:
    for t in texts or []:
        # Accept "Field: 1173", "1,173 Sq Ft", etc.
        # Strip prefix before colon if present.
        tt = t.split(':', 1)[-1].strip() if ':' in t else t
        n = _to_float(tt)
        if n is not None:
            return n
        m = NUM_PAT.search(tt)
        if m:
            try:
                return float(m.group(1).replace(',', ''))
            except Exception:
                continue
    return None

# ----------------------------- Transport parsing -----------------------------
def parse_transport(texts: List[str]) -> Dict[str, Any]:
    out = {
        "walk_score": None, "walk_score_desc": None,
        "bike_score": None, "bike_score_desc": None,
        "transit_score": None, "transit_score_desc": None
    }
    for t in texts or []:
        for m in TRANSPORT_SCORE_PAT.finditer(t):
            kind = m.group(1).lower()
            score = _to_int(m.group(2))
            desc = _norm(m.group(3)) or None
            if 'walk' in kind:
                out["walk_score"], out["walk_score_desc"] = score, desc
            elif 'bike' in kind or 'biking' in kind:
                out["bike_score"], out["bike_score_desc"] = score, desc
            elif 'transit' in kind:
                out["transit_score"], out["transit_score_desc"] = score, desc
    return out

# ----------------------------- Narrative mining -----------------------------
def mine_descriptions(desc_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Pull full text blocks for crime, climate risk, schools, job market/unemployment,
    cost of living/income, weather, and 'surrounding community' paragraphs.
    Also extract a numeric unemployment rate when explicit.
    """
    out = {
        "crime_text": None, "climate_risk_text": None, "schools_text": None,
        "job_market_text": None, "income_text": None, "weather_text": None,
        "surrounding_community_text": None, "unemployment_rate": None
    }
    for d in desc_list or []:
        v = _norm(d.get('value'))
        if not v:
            continue
        l = v.lower()
        if CRIME_PAT.search(l) and not out["crime_text"]:
            out["crime_text"] = v
        if CLIMATE_PAT.search(l) and not out["climate_risk_text"]:
            out["climate_risk_text"] = v
        if SCHOOLS_PAT.search(l) and not out["schools_text"]:
            out["schools_text"] = v
        if JOB_PAT.search(l) and not out["job_market_text"]:
            out["job_market_text"] = v
            um = UNEMPLOYMENT_NUMBER_PAT.search(l)
            if um and out["unemployment_rate"] is None:
                out["unemployment_rate"] = _to_float(um.group(1))
        if INCOME_PAT.search(l) and not out["income_text"]:
            out["income_text"] = v
        if WEATHER_PAT.search(l) and not out["weather_text"]:
            out["weather_text"] = v
        if SURROUNDING_PAT.search(l) and not out["surrounding_community_text"]:
            out["surrounding_community_text"] = v
    return out

# ----------------------------- Appliances mining -----------------------------
def extract_appliances(text_blobs: List[str], explicit_list: List[str]) -> Tuple[Optional[str], Dict[str, Optional[bool]]]:
    """
    Build a deduped comma-separated appliances list from explicit array + any text blobs.
    Return (appliances_csv, flags).
    """
    tokens = set()
    for a in explicit_list or []:
        m = APPLIANCE_PAT.findall(a)
        if m:
            tokens.update([t.lower() for t in m])
        else:
            # If it's an exact item (e.g., "Gas Oven"), keep it verbatim
            s = _norm(a)
            if s:
                tokens.add(s.lower())
    for text in text_blobs or []:
        for m in APPLIANCE_PAT.finditer(text):
            tokens.add(m.group(1).lower())
    # Normalize some synonyms
    canon = set()
    for t in tokens:
        if t == 'fridge':
            canon.add('refrigerator')
        elif t == 'hood':
            canon.add('range hood')
        else:
            canon.add(t)
    # Flags
    flags = {
        "has_dishwasher": 'dishwasher' in canon,
        "has_disposal": 'disposal' in canon or 'compactor' in canon,
        "has_microwave": 'microwave' in canon,
        "has_refrigerator": 'refrigerator' in canon,
        "has_washer_dryer": ('washer' in canon and 'dryer' in canon) or 'stacked washer/dryer' in canon
    }
    appliances_csv = ", ".join(sorted(canon)) if canon else None
    return appliances_csv, flags

# ----------------------------- Core normalizer -----------------------------
class DatafinitiNormalizer:
    def __init__(self, data: Any):
        if isinstance(data, str):
            with open(data, "r", encoding="utf-8") as f:
                self.raw = json.load(f)
        else:
            self.raw = data
        self.subject = self.raw.get("subject") or {}
        self.comparables = self.raw.get("comparables") or []

    # ---------- Schema-first identity ----------
    def id_block(self, p: Dict[str, Any]) -> Dict[str, Any]:
        lat = _to_float(p.get("latitude"))
        lon = _to_float(p.get("longitude"))
        if lat is None or lon is None:
            plat, plon = _point_wkt_to_latlon(_norm(p.get("geoLocation")))
            lat = lat if lat is not None else plat
            lon = lon if lon is not None else plon
        parcel = None
        if p.get("parcelNumbers"):
            try:
                parcel = p["parcelNumbers"][0].get("number")
            except Exception:
                pass
        return {
            "address": _norm(p.get("address")),
            "city": _norm(p.get("city")),
            "state": _norm(p.get("province")),
            "zip_code": _norm(p.get("postalCode")),
            "county": _norm(p.get("county")),
            "latitude": lat,
            "longitude": lon,
            "parcel_number": parcel or _norm(p.get("taxID")),
            "legal_description": _norm(p.get("legalDescription")),
            "subdivision": _norm(p.get("subdivision")),
            "neighborhoods": _join(p.get("neighborhoods")),
            "mls_number": _norm(p.get("mlsNumber")),
            "property_type": _norm(p.get("propertyType")),
            "categories": _join(p.get("categories")),
            "year_built": _to_int(p.get("yearBuilt")),
            "year_renovated": _to_int(p.get("yearRenovated")),
        }

    # ---------- Size & areas ----------
    def size_block(self, p: Dict[str, Any], idx: Dict[str, List[str]]) -> Dict[str, Any]:
        # living areas
        living_sqft = _to_float(p.get("floorSizeValue"))
        gross_area = first_number_from_texts(find_feat(idx, "areagross", "building area total", "living area srch", "gross"))
        # floors breakdown
        floor1 = first_number_from_texts(find_feat(idx, "floor1sizevalue", "floor 1"))
        floor2 = first_number_from_texts(find_feat(idx, "floor2sizevalue", "floor 2"))
        # lot area
        lot_unit = _norm(p.get("lotSizeUnit")).lower()
        lot_sqft = _to_float(p.get("lotSizeValue")) if lot_unit in {"sq ft", "sqft", "square foot"} else None
        lot_ac = _to_float(p.get("lotSizeValue")) if lot_unit in {"ac", "acs", "acre", "acres"} else None
        # Falls back to features
        if lot_sqft is None:
            lot_sqft = first_number_from_texts(find_feat(idx, "lot size square feet", "lot sq ft", "lot sqft", "lot sq ft apx"))
        if lot_ac is None:
            lot_ac = first_number_from_texts(find_feat(idx, "lot size acres", "acres", "lotsizevalueacres", "lot size area"))
        # Derive missing side
        if not lot_sqft and lot_ac:
            lot_sqft = lot_ac * ACRES_TO_SQFT
        if not lot_ac and lot_sqft:
            lot_ac = lot_sqft / ACRES_TO_SQFT
        # garage
        garage_sqft = first_number_from_texts(find_feat(idx, "parkinggaragearea", "garage area"))

        # basement (type + area)
        basement_texts = find_feat(idx, "basement information", "basement")
        basement_text = _join(basement_texts)
        basement_area = None
        for t in basement_texts:
            m = AREA_SQFT_PAT.search(t)
            if m:
                basement_area = _to_float(m.group(1))
                break

        # lot dimensions + description/features/structures
        lot_dimensions = _join(find_feat(idx, "lot size dimensions", "lot dimensions"))
        lot_description = _join(find_feat(idx, "lot description"))
        lot_features = _join(find_feat(idx, "lot features", "topography", "land info"))
        lot_information_raw = _join(find_feat(idx, "lot information"))
        other_structures = None
        for s in find_feat(idx, "property information"):
            # e.g., "Other Structures: Shed(s)"
            if "other structures" in s.lower():
                other_structures = s.split(":", 1)[-1].strip()

        return {
            "living_sqft": _to_float(living_sqft),
            "gross_living_area": _to_float(gross_area),
            "floor1_sqft": _to_float(floor1),
            "floor2_sqft": _to_float(floor2),
            "lot_sqft": _to_float(lot_sqft),
            "lot_acres": _to_float(lot_ac),
            "garage_sqft": _to_float(garage_sqft),
            "basement_type": basement_text,
            "basement_area_sqft": _to_float(basement_area),
            "lot_dimensions": lot_dimensions,
            "lot_description": lot_description,
            "lot_features": lot_features,
            "lot_information_raw": lot_information_raw,
            "other_structures_on_lot": other_structures,
        }

    # ---------- Beds, baths, rooms ----------
    def beds_baths_block(self, p: Dict[str, Any], idx: Dict[str, List[str]]) -> Dict[str, Any]:
        beds = _to_int(p.get("numBedroom")) or _to_int(first_number_from_texts(find_feat(idx, "bedrooms total", "bedrooms", "main and upper beds")))
        baths_total = p.get("numBathroom")
        if baths_total is None:
            baths_total = first_number_from_texts(find_feat(idx, "bathrooms total", "bathrooms total count", "bathrooms"))
        baths_full = first_number_from_texts(find_feat(idx, "bathrooms full", "main full bathrooms"))
        baths_half = first_number_from_texts(find_feat(idx, "bathrooms half", "half bath"))
        if baths_total is None and (baths_full is not None or baths_half is not None):
            baths_total = (baths_full or 0) + 0.5 * (baths_half or 0)
        stories = _to_int(p.get("numFloor"))
        rooms_total = _to_int(p.get("numRoom")) or _to_int(first_number_from_texts(find_feat(idx, "rooms total", "total rooms", "# of rooms", "room count")))
        return {
            "beds": beds,
            "baths_total": _to_float(baths_total),
            "baths_full": _to_int(baths_full),
            "baths_half": _to_int(baths_half),
            "stories": stories,
            "rooms_total": rooms_total
        }

    # ---------- Materials / style / roof / quality / condition ----------
    def build_block(self, p: Dict[str, Any], idx: Dict[str, List[str]]) -> Dict[str, Any]:
        style_top = _join(p.get("architecturalStyles"))
        style_feat = _join(find_feat(idx, "architectural style", "style description", "style"))
        construction = _join(p.get("exteriorConstruction")) or _join(find_feat(idx, "construction materials", "construction"))
        roof = _join(p.get("roofing")) or _join(find_feat(idx, "roof"))
        build_info = _join(find_feat(idx, "building information"))
        prop_info = _join(find_feat(idx, "property information"))
        condition = _join(find_feat(idx, "property condition", "condition"))
        quality = _join(find_feat(idx, "quality", "construction quality", "grade", "property condition"))
        design_style = _join(find_feat(idx, "style", "style description"))

        return {
            "architectural_style": style_top or style_feat,
            "construction_materials": construction,
            "roof_type": roof,
            "construction_details": build_info,
            "property_details_raw": prop_info,
            "condition": condition,
            "quality_of_construction": quality,
            "design_style": design_style
        }

    # ---------- HVAC / utilities / energy ----------
    def hvac_block(self, p: Dict[str, Any], idx: Dict[str, List[str]]) -> Dict[str, Any]:
        hvac_types = _join(p.get("hvacTypes")) or _join(find_feat(idx, "heating & cooling", "hvac"))
        # Heating/cooling types & fuels — DO NOT collapse to one; keep all
        heating_values = find_feat(idx, "heating", "hvacheatingdetail", "heat source")
        cooling_values = find_feat(idx, "cooling", "hvaccoolingdetail")
        heating_type = _join([v.split(":", 1)[-1].strip() if ":" in v else v for v in heating_values])
        cooling_type = _join([v.split(":", 1)[-1].strip() if ":" in v else v for v in cooling_values])
        heating_fuel = _join(find_feat(idx, "heat source", "heating fuel", "hvacheatingfuel"))
        has_heating = None
        has_cooling = None
        for t in heating_values:
            b = _to_bool(t)
            if b is True:
                has_heating = True
        for t in cooling_values:
            b = _to_bool(t)
            if b is True:
                has_cooling = True
        # Water & Sewer
        water_source = _join(p.get("waterSource")) or _join(find_feat(idx, "water source", "water"))
        sewer_type = _join(p.get("sewerType")) or _join(find_feat(idx, "sewer"))
        # Energy / windows
        energy = _join(find_feat(idx, "solar", "energy", "dual pane", "double pane", "energy efficient", "efficiency"))
        window_features = _join(find_feat(idx, "window features", "window"))
        water_heater = _join(find_feat(idx, "water heat", "water heater"))

        return {
            "hvac_summary": hvac_types,
            "has_heating": has_heating,
            "heating_types": heating_type,
            "heating_fuels": heating_fuel,
            "has_cooling": has_cooling,
            "cooling_types": cooling_type,
            "water_source": water_source,
            "sewer_type": sewer_type,
            "water_heater": water_heater,
            "energy_efficient_items": energy or window_features
        }

    # ---------- Interior / exterior / yard / fireplace / parking ----------
    def inout_block(self, p: Dict[str, Any], idx: Dict[str, List[str]]) -> Dict[str, Any]:
        # Appliances
        appliances_explicit = p.get("appliances") or []
        appliance_texts = find_feat(idx, "appliances", "kitchen", "interior features")
        appliances_csv, app_flags = extract_appliances(appliance_texts, appliances_explicit)

        # Interior/exterior
        interior_features = _join(find_feat(idx, "interior features"))
        exterior_features = _join(p.get("exteriorFeatures") or find_feat(idx, "exterior features", "exterior and lot features"))
        flooring = _join(find_feat(idx, "flooring", "floor covering", "floor covering", "flooring:"))
        window_features = _join(find_feat(idx, "window features"))

        # Porch/patio/deck and areas
        ppd_texts = find_feat(idx, "patio", "porch", "deck", "patio and porch features")
        patio_porch_deck = _join(ppd_texts)
        patio_area = first_number_from_texts(find_feat(idx, "patio size value", "patiosizevalue"))
        porch_area = first_number_from_texts(find_feat(idx, "porch size value", "porchsizevalue"))

        # Pool / spa
        pool_text = _join(find_feat(idx, "pool")) or _join(find_feat(idx, "pool information"))
        has_pool = None if pool_text is None else (not re.search(r'\b(no|false|0)\b', pool_text, re.I))
        spa_text = _join(find_feat(idx, "spa"))
        has_spa = None if spa_text is None else (not re.search(r'\b(no|false|0)\b', spa_text, re.I))

        # Fence / yard
        fence_text = _join(find_feat(idx, "fence", "fencing", "chain link"))
        yard_text = _join(find_feat(idx, "yard", "yard description", "yard space"))

        # Fireplaces
        fp_count = first_number_from_texts(find_feat(idx, "fireplaces total", "fireplaces"))
        fp_info = _join(find_feat(idx, "fireplace information", "fireplace features"))
        has_fireplace = None
        if fp_count is not None:
            has_fireplace = fp_count > 0
        if fp_info and has_fireplace is None:
            has_fireplace = not re.search(r'\b(no|false|0|none)\b', fp_info, re.I)

        # Parking / garage
        garage_spaces = _to_int(p.get("numParkingSpaces")) or _to_int(first_number_from_texts(find_feat(idx, "garage spaces", "parking spaces", "total # parking spaces")))
        garage_type = _join(find_feat(idx, "garage", "garage and parking", "parking"))
        parking_details = _join(p.get("parking"))

        return {
            "appliances": appliances_csv,
            **app_flags,
            "interior_features": interior_features,
            "exterior_features": exterior_features,
            "flooring_types": flooring,
            "window_features": window_features,
            "patio_porch_deck": patio_porch_deck,
            "patio_area_sqft": _to_float(patio_area),
            "porch_area_sqft": _to_float(porch_area),
            "has_pool": has_pool,
            "has_spa": has_spa,
            "fence": fence_text,
            "yard_type": yard_text,
            "has_fireplace": has_fireplace,
            "fireplace_count": _to_int(fp_count),
            "fireplace_locations": fp_info,
            "garage_spaces": garage_spaces,
            "garage_type": garage_type,
            "parking_details": parking_details
        }

    # ---------- Site / view / location ----------
    def site_block(self, p: Dict[str, Any], idx: Dict[str, List[str]]) -> Dict[str, Any]:
        site_location = _join(find_feat(idx, "location information", "directions", "cross street"))
        view_text = _join(find_feat(idx, "view", "views"))
        # Lot location hints (corner/cul-de-sac/key lot)
        lot_loc_hints = []
        for t in (find_feat(idx, "lot features", "lot description", "location information") or []):
            tl = t.lower()
            if "corner" in tl:
                lot_loc_hints.append("corner lot")
            if "cul-de-sac" in tl or "cul de sac" in tl:
                lot_loc_hints.append("cul-de-sac")
            if "key lot" in tl:
                lot_loc_hints.append("key lot")
            if "flag lot" in tl:
                lot_loc_hints.append("flag lot")
            if "near public transit" in tl:
                lot_loc_hints.append("near transit")
        lot_location = ", ".join(sorted(set(lot_loc_hints))) if lot_loc_hints else None
        transport_scores_text = find_feat(idx, "transport scores")
        transport_desc_text = _join(find_feat(idx, "transport description"))
        ts = parse_transport(transport_scores_text)
        return {
            "site_location": site_location,
            "view": view_text,
            "lot_location": lot_location,
            "transport_description": transport_desc_text,
            "walk_score": ts.get("walk_score"),
            "walk_score_desc": ts.get("walk_score_desc"),
            "bike_score": ts.get("bike_score"),
            "bike_score_desc": ts.get("bike_score_desc"),
            "transit_score": ts.get("transit_score"),
            "transit_score_desc": ts.get("transit_score_desc"),
        }

    # ---------- Prices, sale & list history, assessments, taxes, ownership ----------
    def finance_block(self, p: Dict[str, Any], idx: Dict[str, List[str]]) -> Dict[str, Any]:
        # Price events
        price_events = []
        for pr in p.get("prices") or []:
            amt = _to_float(pr.get("amountMax") or pr.get("amountMin"))
            date_iso = _date_any(pr.get("date"))
            sold_flag = str(pr.get("isSold") or '').lower() == 'true'
            status = _norm(pr.get("status")).lower()
            comment = _norm(pr.get("comment")).lower()
            is_sold = sold_flag or "sold" in status or "sold" in comment
            if amt and date_iso:
                domains = pr.get("domains") or []
                domain = domains[0] if domains else None
                price_events.append({
                    "date": date_iso, "amount": amt, "domain": domain, "sold": is_sold, "status": status or None
                })
        # Sort newest first
        price_events.sort(key=lambda x: x["date"], reverse=True)

        # Two most recent list prices (non-sold)
        list_events = [e for e in price_events if not e["sold"]]
        sold_events = [e for e in price_events if e["sold"]]

        def top2(evts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            return evts[:2] if evts else []

        L = top2(list_events)
        S = top2(sold_events)

        # sale_price & sale_date
        sale_price = _to_float(p.get("mostRecentPriceAmount"))
        sale_date = _date_any(p.get("mostRecentPriceDate"))

        # transactions fallback for sale price/date
        if (sale_price is None) and (p.get("transactions")):
            try:
                tx_sorted = sorted(p["transactions"], key=lambda x: _date_any(x.get("saleDate")) or "", reverse=True)
                if tx_sorted and tx_sorted[0].get("saleDate"):
                    sale_date = sale_date or _date_any(tx_sorted[0]["saleDate"])
                    sale_price = sale_price or _to_float(tx_sorted[0].get("price"))
            except Exception:
                pass

        # If still nothing and most recent status is Sold, use mostRecentPriceAmount as last resort
        most_recent_status = _norm(p.get("mostRecentStatus"))
        most_recent_price = _to_float(p.get("mostRecentPriceAmount"))
        most_recent_price_date = _date_any(p.get("mostRecentPriceDate"))
        if (sale_price is None) and most_recent_status.lower() == "sold" and most_recent_price:
            sale_price, sale_date = most_recent_price, most_recent_price_date

        # list_price: newest non-sold; else top-level mostRecentPriceAmount (when not sold)
        list_price = L[0]["amount"] if L else None
        list_date = L[0]["date"] if L else None
        if list_price is None and most_recent_status.lower() != "sold" and most_recent_price:
            list_price = most_recent_price
            list_date = list_date or most_recent_price_date

        price_per_sqft = _to_float(p.get("mostRecentPricePerSquareFoot"))

        # Taxes & assessments
        tax_amount = None
        for t in find_feat(idx, "tax record", "taxes", "tax history"):
            m = MONEY_PAT.search(t)
            if m:
                tax_amount = tax_amount or _to_float(m.group(1))
        if tax_amount is None and p.get("propertyTaxes"):
            try:
                tax_amount = _to_float(sorted(p["propertyTaxes"], key=lambda x: x.get("year", 0), reverse=True)[0].get("amount"))
            except Exception:
                pass

        assessed = {"2024": {}, "2025": {}}
        for a in p.get("assessedValues") or []:
            y = str(a.get("year"))
            if y in assessed:
                assessed[y]["total"] = _to_float(a.get("totalAmount"))
                assessed[y]["land"] = _to_float(a.get("landAmount"))
                assessed[y]["improvements"] = _to_float(a.get("improvementsAmount"))
        # Parse generic assessment lines if missing
        for line in find_feat(idx, "property assessment", "taxable value"):
            ll = line.lower()
            m = MONEY_PAT.search(line)
            if not m:
                continue
            val = _to_float(m.group(1))
            if "land" in ll:
                assessed["2024"].setdefault("land", val)
            elif "improvements" in ll or "additions" in ll:
                assessed["2024"].setdefault("improvements", val)
            elif "total" in ll or "assessment" in ll:
                assessed["2024"].setdefault("total", val)

        tax_exemptions = _join(p.get("taxExemptions"))

        # Ownership, financing & concessions
        ownership_type = _join([_norm(p.get("ownership"))] + find_feat(idx, "ownership type"))
        financing_terms = _join(find_feat(idx, "financing", "selling terms", "financing terms"))
        concessions = _join(find_feat(idx, "concession", "seller paid", "repairs amount", "buyer credit"))

        return {
            "status": _norm(p.get("mostRecentStatus")),
            "status_date": _date_any(p.get("mostRecentStatusDate")),
            "listing_agent": _norm(p.get("mostRecentBrokerAgent")),
            "listing_company": _norm(p.get("mostRecentBrokerCompany")),
            "most_recent_price": most_recent_price,
            "most_recent_price_date": most_recent_price_date,
            "price_per_sqft": price_per_sqft,
            "list_price": list_price,
            "list_date": list_date,
            "recent_list_price_1_amount": L[0]["amount"] if len(L) > 0 else None,
            "recent_list_price_1_date": L[0]["date"] if len(L) > 0 else None,
            "recent_list_price_1_domain": L[0]["domain"] if len(L) > 0 else None,
            "recent_list_price_2_amount": L[1]["amount"] if len(L) > 1 else None,
            "recent_list_price_2_date": L[1]["date"] if len(L) > 1 else None,
            "recent_list_price_2_domain": L[1]["domain"] if len(L) > 1 else None,
            "sale_price": sale_price,
            "sale_date": sale_date,
            "recent_sold_price_1_amount": S[0]["amount"] if len(S) > 0 else None,
            "recent_sold_price_1_date": S[0]["date"] if len(S) > 0 else None,
            "recent_sold_price_1_domain": S[0]["domain"] if len(S) > 0 else None,
            "recent_sold_price_2_amount": S[1]["amount"] if len(S) > 1 else None,
            "recent_sold_price_2_date": S[1]["date"] if len(S) > 1 else None,
            "recent_sold_price_2_domain": S[1]["domain"] if len(S) > 1 else None,
            "annual_taxes": tax_amount,
            "assessed_total_2024": assessed["2024"].get("total"),
            "assessed_land_2024": assessed["2024"].get("land"),
            "assessed_improvements_2024": assessed["2024"].get("improvements"),
            "assessed_total_2025": assessed["2025"].get("total"),
            "assessed_land_2025": assessed["2025"].get("land"),
            "assessed_improvements_2025": assessed["2025"].get("improvements"),
            "tax_exemptions": tax_exemptions,
            "ownership_type": ownership_type,
            "financing_terms": financing_terms,
            "concessions": concessions
        }

    # ---------- Schools/Crime/Weather/Income/Job ----------
    def community_block(self, p: Dict[str, Any], idx: Dict[str, List[str]]) -> Dict[str, Any]:
        descs = p.get("descriptions") or []
        mined = mine_descriptions(descs)
        school_ratings = _join(find_feat(idx, "school ratings"))
        return {
            "school_ratings_text": school_ratings,
            "crime_text": mined["crime_text"],
            "climate_risk_text": mined["climate_risk_text"],
            "schools_text": mined["schools_text"],
            "job_market_text": mined["job_market_text"],
            "unemployment_rate": mined["unemployment_rate"],
            "income_text": mined["income_text"],
            "weather_text": mined["weather_text"],
            "surrounding_community_text": mined["surrounding_community_text"],
        }

    # ---------- One property normalization ----------
    def normalize_one(self, p: Dict[str, Any], role: str, subj_lat: Optional[float] = None, subj_lon: Optional[float] = None) -> Dict[str, Any]:
        features = p.get("features") or []
        idx = features_index(features)
        out: Dict[str, Any] = {"role": role, "record_id": _norm(p.get("id"))}
        blocks = [
            self.id_block(p),
            self.size_block(p, idx),
            self.beds_baths_block(p, idx),
            self.build_block(p, idx),
            self.hvac_block(p, idx),
            self.inout_block(p, idx),
            self.site_block(p, idx),
            self.finance_block(p, idx),
            self.community_block(p, idx),
        ]
        for b in blocks:
            out.update(b)

        # Distance to subject if subject lat/lon provided
        lat, lon = out.get("latitude"), out.get("longitude")
        if subj_lat is not None and subj_lon is not None and lat and lon and role != "Subject":
            out["distance_miles_to_subject"] = _haversine_miles(subj_lat, subj_lon, float(lat), float(lon))
        else:
            out["distance_miles_to_subject"] = 0.0 if role == "Subject" else None
        return out

    # ---------- Main normalization method ----------
    def normalize_all(self) -> Dict[str, Any]:
        """
        Returns normalized data as plain dicts (no pandas).
        Format: {"subject": {...}, "comparables": [{...}, {...}, {...}]}
        """
        rows = []
        
        # Subject
        subj_row = None
        if self.subject:
            subj_row = self.normalize_one(self.subject, "Subject")
            rows.append(subj_row)
        
        # Get subject lat/lon for distance calculations
        subj_lat = subj_row.get("latitude") if subj_row else None
        subj_lon = subj_row.get("longitude") if subj_row else None
        
        # Comparables
        for i, comp in enumerate(self.comparables, 1):
            rows.append(self.normalize_one(comp, f"Comparable_{i}", subj_lat, subj_lon))
        
        return {
            "subject": rows[0] if rows else None,
            "comparables": rows[1:] if len(rows) > 1 else []
        }