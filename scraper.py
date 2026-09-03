import json
import re
import time
from typing import Optional, Tuple
import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Overpass QL query targeting all ESI/ESIS healthcare infrastructure across India
QUERY = """
[out:json][timeout:90];
area["ISO3166-1"="IN"][admin_level=2]->.india;
(
  node["amenity"~"hospital|clinic|doctors"](area.india)[~"name"~"ESI|ESIC|ESIS|Dispensary|DCBO",i];
  way["amenity"~"hospital|clinic|doctors"](area.india)[~"name"~"ESI|ESIC|ESIS|Dispensary|DCBO",i];
  relation["amenity"~"hospital|clinic|doctors"](area.india)[~"name"~"ESI|ESIC|ESIS|Dispensary|DCBO",i];
  
  node["healthcare"](area.india)[~"name"~"ESI|ESIC|ESIS|Dispensary|DCBO",i];
  way["healthcare"](area.india)[~"name"~"ESI|ESIC|ESIS|Dispensary|DCBO",i];
);
out center tags;
"""

CLINICAL_PATTERNS = [
    r"\b(esic?|esis)\b.*?\b(hospital|model hospital|super\s*speciality\s*hospital|ss\s*hospital)\b",
    r"\b(medical college|pgimsr|dental college|nursing college)\b",
    r"\b(esic?|esis)\b.*?\b(ayush\s*hospital|trauma\s*centre)\b",
    r"\b(esic?|esis)\b.*?\b(dispensary|clinic|health\s*centre|mhu|mobile\s*dispensary)\b",
    r"\b(esi[sc]?)\s*(dispensary|hospital)\b",
    r"\b(dcbo|d\.c\.b\.o)\b",
    r"\bdispensary[\s\-]*(?:cum[\s\-]*branch\s*office|cbo)\b",
]

EXCLUSION_PATTERNS = [
    r"\b(quarters?|qtrs?|residential\s*complex|staff\s*quarters?|colony|officers?\s*mess|hostel)\b",
    r"\b(headquarters?|h\.?q\.?|regional\s*office|sub[\s\-]*regional\s*office|sro|division(?:al)?\s*office|branch\s*office\b(?!.*(?:dispensary|dcbo|cum))|bo\b|directorate)\b",
    r"\b(cash\s*branch|revenue\s*branch|accounts\s*branch|audit\s*branch|recovery\s*office|recovery\s*cell)\b",
    r"\b(esi\s*court|labour\s*court|tribunal|inspection\s*wing|vigilance\s*wing)\b",
    r"\b(guest\s*house|holiday\s*home|transit\s*camp|store\s*depot|engineering\s*wing|pmo\s*cell)\b",
]

COMPILED_CLINICAL = [re.compile(p, re.IGNORECASE) for p in CLINICAL_PATTERNS]
COMPILED_EXCLUSIONS = [re.compile(p, re.IGNORECASE) for p in EXCLUSION_PATTERNS]

def evaluate_and_clean_facility(name: str) -> Tuple[Optional[str], str]:
    clean_name = name.strip()
    for exclusion in COMPILED_EXCLUSIONS:
        if exclusion.search(clean_name):
            return None, clean_name

    if not any(pattern.search(clean_name) for pattern in COMPILED_CLINICAL):
        return None, clean_name

    clean_name = re.sub(
        r"\b(dcbo|d\.c\.b\.o)\b",
        "Dispensary-cum-Branch Office (DCBO)",
        clean_name,
        flags=re.IGNORECASE
    )

    name_lower = clean_name.lower()
    if any(k in name_lower for k in ["medical college", "pgimsr", "dental college"]):
        category = "Tier 1: ESIC Medical College / PGIMSR"
    elif any(k in name_lower for k in ["model hospital", "super speciality", "ss hospital"]):
        category = "Tier 1: ESIC Model / Super Speciality Hospital"
    elif "hospital" in name_lower:
        category = "Tier 2: ESI / ESIS Secondary Hospital"
    elif any(k in name_lower for k in ["dcbo", "dispensary-cum-branch", "dispensary cum branch"]):
        category = "Tier 3: Dispensary-cum-Branch Office (DCBO)"
    elif any(k in name_lower for k in ["dispensary", "clinic", "health centre", "mhu"]):
        category = "Tier 3: ESI / ESIS Dispensary"
    else:
        category = "Tier 3: Primary Clinical Facility"

    return category, clean_name

def run_osm_extraction():
    print("Querying OpenStreetMap Overpass API for all ESI facilities across India (no key required)...")
    try:
        response = requests.post(OVERPASS_URL, data={"data": QUERY}, timeout=120)
        response.raise_for_status()
        elements = response.json().get("elements", [])
    except Exception as e:
        print(f"Extraction error: {e}")
        return

    verified_facilities = {}
    dropped_count = 0

    for el in elements:
        tags = el.get("tags", {})
        raw_name = tags.get("name") or tags.get("name:en")
        if not raw_name:
            continue

        category, clean_name = evaluate_and_clean_facility(raw_name)
        if category is None:
            dropped_count += 1
            continue

        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        osm_id = str(el.get("id"))

        addr_parts = [
            tags.get("addr:street"),
            tags.get("addr:suburb"),
            tags.get("addr:city") or tags.get("addr:district"),
            tags.get("addr:state"),
            tags.get("addr:postcode"),
        ]
        address = ", ".join([p for p in addr_parts if p]) or tags.get("addr:full", "India")

        verified_facilities[osm_id] = {
            "place_id": f"osm_{osm_id}",
            "name": clean_name,
            "category": category,
            "address": address,
            "latitude": lat,
            "longitude": lon,
            "phone": tags.get("phone") or tags.get("contact:phone", ""),
            "maps_url": f"https://www.google.com/maps/search/?api=1&query={lat},{lon}" if lat and lon else "",
            "source": "openstreetmap_overpass_free",
        }

    output_file = "esi_master.json"
    result_list = list(verified_facilities.values())

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result_list, f, indent=2, ensure_ascii=False)

    print(f"\nExtraction complete.")
    print(f"Non-clinical excluded: {dropped_count}")
    print(f"Saved {len(result_list)} verified facilities directly to '{output_file}'.")

if __name__ == "__main__":
    run_osm_extraction()
        
