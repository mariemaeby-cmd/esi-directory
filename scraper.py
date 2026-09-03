import json
import os
import re
import time
from typing import Optional, Tuple
import requests

API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "YOUR_API_KEY_HERE")
PLACES_URL = "https://places.googleapis.com/v1/places:searchText"

SEARCH_QUERIES = [
    "ESIC Hospital",
    "ESIS Hospital",
    "ESIC Medical College PGIMSR",
    "ESI Dispensary",
    "ESIS Dispensary",
    "ESIC DCBO",
    "ESI Dispensary cum Branch Office",
]

REGION_ANCHORS = [
    {"name": "North (NCR/PB/HR/RJ)", "lat": 28.6139, "lng": 77.2090, "radius": 450000.0},
    {"name": "West (MH/GJ/GA)", "lat": 19.0760, "lng": 72.8777, "radius": 450000.0},
    {"name": "South-1 (KA/TN/KL)", "lat": 12.9716, "lng": 77.5946, "radius": 450000.0},
    {"name": "South-2 (AP/TS)", "lat": 17.3850, "lng": 78.4867, "radius": 350000.0},
    {"name": "East (WB/OD/JH/BR)", "lat": 22.5726, "lng": 88.3639, "radius": 450000.0},
    {"name": "Central (MP/CG/UP)", "lat": 23.2599, "lng": 77.4126, "radius": 450000.0},
    {"name": "North-East (AS/TR/ML)", "lat": 26.1445, "lng": 91.7362, "radius": 350000.0},
]

HEADERS = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": API_KEY,
    "X-Goog-FieldMask": (
        "places.id,"
        "places.displayName,"
        "places.formattedAddress,"
        "places.location,"
        "places.nationalPhoneNumber,"
        "places.internationalPhoneNumber,"
        "places.types,"
        "places.googleMapsUri"
    ),
}

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
    
    # 1. Reject non-clinical keywords
    for exclusion in COMPILED_EXCLUSIONS:
        if exclusion.search(clean_name):
            return None, clean_name

    # 2. Require positive clinical match
    if not any(pattern.search(clean_name) for pattern in COMPILED_CLINICAL):
        return None, clean_name

    # 3. Expand DCBO
    clean_name = re.sub(
        r"\b(dcbo|d\.c\.b\.o)\b",
        "Dispensary-cum-Branch Office (DCBO)",
        clean_name,
        flags=re.IGNORECASE
    )

    # 4. Categorize Tier
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

def run_extraction():
    if API_KEY == "YOUR_API_KEY_HERE":
        print("[!] Set your GOOGLE_MAPS_API_KEY environment variable or edit the script with your API key.")
        return

    verified_facilities = {}
    dropped_entries = 0

    for anchor in REGION_ANCHORS:
        print(f"Scanning region: {anchor['name']}...")
        for query in SEARCH_QUERIES:
            payload = {
                "textQuery": query,
                "locationBias": {
                    "circle": {
                        "center": {"latitude": anchor["lat"], "longitude": anchor["lng"]},
                        "radius": anchor["radius"],
                    }
                },
                "maxResultCount": 20,
            }

            try:
                response = requests.post(PLACES_URL, headers=HEADERS, json=payload, timeout=10)
                if response.status_code != 200:
                    continue

                places = response.json().get("places", [])
                for place in places:
                    place_id = place.get("id")
                    if not place_id or place_id in verified_facilities:
                        continue

                    raw_name = place.get("displayName", {}).get("text", "")
                    category, clean_name = evaluate_and_clean_facility(raw_name)

                    if category is None:
                        dropped_entries += 1
                        continue

                    verified_facilities[place_id] = {
                        "place_id": place_id,
                        "name": clean_name,
                        "category": category,
                        "address": place.get("formattedAddress", ""),
                        "latitude": place.get("location", {}).get("latitude"),
                        "longitude": place.get("location", {}).get("longitude"),
                        "phone": place.get("nationalPhoneNumber") or place.get("internationalPhoneNumber", ""),
                        "maps_url": place.get("googleMapsUri", ""),
                        "source": "google_places_api_filtered",
                    }

                time.sleep(0.2)
            except Exception as e:
                print(f"  [X] Request error on query '{query}': {e}")

    output_filename = "verified_esi_clinical_facilities.json"
    result_list = list(verified_facilities.values())

    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(result_list, f, indent=2, ensure_ascii=False)

    print(f"\nCompleted.")
    print(f"Administrative/Quarters excluded: {dropped_entries}")
    print(f"Saved {len(result_list)} verified clinical facilities to '{output_filename}'.")

if __name__ == "__main__":
    run_extraction()
    
