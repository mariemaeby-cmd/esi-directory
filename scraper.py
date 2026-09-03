import csv
import json
import re
from typing import Dict, List, Optional, Tuple
import requests

# Fast public endpoints with fallback mirrors
OVERPASS_MIRRORS = [
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]

# Fast bounding-box query for India to eliminate server queue delays
COMPACT_QUERY = """
[out:json][timeout:25];
(
  node["amenity"~"hospital|clinic"](6.5,68.0,37.5,97.5)[~"name"~"ESI|ESIC|ESIS|Dispensary",i];
  way["amenity"~"hospital|clinic"](6.5,68.0,37.5,97.5)[~"name"~"ESI|ESIC|ESIS|Dispensary",i];
  node["healthcare"](6.5,68.0,37.5,97.5)[~"name"~"ESI|ESIC|ESIS|Dispensary",i];
);
out center tags 500;
"""

CLINICAL_PATTERNS = [
    r"\b(esic?|esis)\b.*?\b(hospital|model hospital|super\s*speciality|ss\s*hospital|medical college|pgimsr|dental college)\b",
    r"\b(medical college|pgimsr|dental college|nursing college)\b",
    r"\b(esic?|esis)\b.*?\b(dispensary|clinic|health\s*centre|mhu)\b",
    r"\b(esi[sc]?)\s*(dispensary|hospital)\b",
    r"\b(dcbo|d\.c\.b\.o)\b",
    r"\bdispensary[\s\-]*(?:cum[\s\-]*branch\s*office|cbo)\b",
]

EXCLUSION_PATTERNS = [
    r"\b(quarters?|qtrs?|residential|staff\s*quarters?|colony|mess|hostel)\b",
    r"\b(headquarters?|h\.?q\.?|regional\s*office|sub[\s\-]*regional|sro|divisional\s*office|branch\s*office\b(?!.*(?:dispensary|dcbo|cum))|bo\b|directorate)\b",
    r"\b(cash\s*branch|revenue\s*branch|accounts|audit|recovery\s*cell|recovery\s*office)\b",
    r"\b(court|tribunal|inspection|vigilance)\b",
    r"\b(guest\s*house|holiday\s*home|transit\s*camp|depot|engineering)\b",
]

COMPILED_CLINICAL = [re.compile(p, re.IGNORECASE) for p in CLINICAL_PATTERNS]
COMPILED_EXCLUSIONS = [re.compile(p, re.IGNORECASE) for p in EXCLUSION_PATTERNS]


def evaluate_facility(name: str) -> Tuple[Optional[str], str]:
    clean_name = re.sub(r"\s+", " ", name).strip()
    for exclusion in COMPILED_EXCLUSIONS:
        if exclusion.search(clean_name):
            return None, clean_name

    if not any(pattern.search(clean_name) for pattern in COMPILED_CLINICAL):
        return None, clean_name

    clean_name = re.sub(r"\b(dcbo|d\.c\.b\.o)\b", "Dispensary-cum-Branch Office (DCBO)", clean_name, flags=re.IGNORECASE)
    name_lower = clean_name.lower()

    if any(k in name_lower for k in ["medical college", "pgimsr", "dental college"]):
        cat = "Tier 1: ESIC Medical College / PGIMSR"
    elif any(k in name_lower for k in ["model hospital", "super speciality", "ss hospital"]):
        cat = "Tier 1: ESIC Model / Super Speciality Hospital"
    elif "hospital" in name_lower:
        cat = "Tier 2: ESI / ESIS Secondary Hospital"
    elif any(k in name_lower for k in ["dcbo", "dispensary-cum-branch", "dispensary cum branch"]):
        cat = "Tier 3: Dispensary-cum-Branch Office (DCBO)"
    else:
        cat = "Tier 3: ESI / ESIS Dispensary"

    return cat, clean_name


def fetch_data() -> List[Dict]:
    elements = []
    headers = {"User-Agent": "ESI-Clinical-Directory-Fast/1.0"}

    for mirror in OVERPASS_MIRRORS:
        try:
            print(f"Trying mirror: {mirror} ...")
            r = requests.post(mirror, data={"data": COMPACT_QUERY}, headers=headers, timeout=25)
            if r.status_code == 200:
                elements = r.json().get("elements", [])
                print(f"Fetched {len(elements)} items successfully.")
                break
        except Exception as err:
            print(f"Mirror failed: {err}")

    facilities = {}
    dropped = 0

    for el in elements:
        tags = el.get("tags", {})
        raw_name = tags.get("name") or tags.get("name:en")
        if not raw_name:
            continue

        cat, c_name = evaluate_facility(raw_name)
        if not cat:
            dropped += 1
            continue

        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        osm_id = str(el.get("id"))

        addr_parts = [tags.get("addr:street"), tags.get("addr:suburb"), tags.get("addr:city") or tags.get("addr:district"), tags.get("addr:state")]
        address = ", ".join([p for p in addr_parts if p]) or tags.get("addr:full", "India")
        pincode = tags.get("addr:postcode", "")

        key = re.sub(r"[^a-zA-Z0-9]", "", c_name.lower())
        if key not in facilities:
            facilities[key] = {
                "id": f"osm_{osm_id}",
                "name": c_name,
                "category": cat,
                "address": address,
                "pincode": pincode,
                "latitude": lat,
                "longitude": lon,
                "phone": tags.get("phone", ""),
                "maps_url": f"https://www.google.com/maps/search/?api=1&query={lat},{lon}" if lat and lon else "",
            }

    data = list(facilities.values())

    with open("esi_master.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    if data:
        with open("esi_master.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["id", "name", "category", "address", "pincode", "latitude", "longitude", "phone", "maps_url"])
            w.writeheader()
            w.writerows(data)

    print(f"Done. Dropped {dropped} non-clinical. Saved {len(data)} clinical facilities.")
    return data


if __name__ == "__main__":
    fetch_data()
                                     
