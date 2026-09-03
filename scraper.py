import csv
import json
import re
import time
from typing import Dict, List, Optional, Tuple
import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

OVERPASS_QUERY = """
[out:json][timeout:180];
area["ISO3166-1"="IN"][admin_level=2]->.india;
(
  node["amenity"~"hospital|clinic|doctors"](area.india)[~"name"~"ESI|ESIC|ESIS|Dispensary|DCBO",i];
  way["amenity"~"hospital|clinic|doctors"](area.india)[~"name"~"ESI|ESIC|ESIS|Dispensary|DCBO",i];
  relation["amenity"~"hospital|clinic|doctors"](area.india)[~"name"~"ESI|ESIC|ESIS|Dispensary|DCBO",i];

  node["healthcare"](area.india)[~"name"~"ESI|ESIC|ESIS|Dispensary|DCBO",i];
  way["healthcare"](area.india)[~"name"~"ESI|ESIC|ESIS|Dispensary|DCBO",i];
  relation["healthcare"](area.india)[~"name"~"ESI|ESIC|ESIS|Dispensary|DCBO",i];

  node["building"~"hospital"](area.india)[~"name"~"ESI|ESIC|ESIS|Dispensary|DCBO",i];
  way["building"~"hospital"](area.india)[~"name"~"ESI|ESIC|ESIS|Dispensary|DCBO",i];
);
out center tags;
"""

CLINICAL_PATTERNS = [
    r"\b(esic?|esis)\b.*?\b(hospital|model hospital|super\s*speciality|ss\s*hospital|medical college|pgimsr|dental college|ayush)\b",
    r"\b(medical college|pgimsr|dental college|nursing college)\b",
    r"\b(esic?|esis)\b.*?\b(dispensary|clinic|health\s*centre|mhu|mobile\s*dispensary)\b",
    r"\b(esi[sc]?)\s*(dispensary|hospital|clinic)\b",
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
    clean_name = re.sub(r"\s+", " ", name).strip()

    for exclusion in COMPILED_EXCLUSIONS:
        if exclusion.search(clean_name):
            return None, clean_name

    if not any(pattern.search(clean_name) for pattern in COMPILED_CLINICAL):
        return None, clean_name

    clean_name = re.sub(
        r"\b(dcbo|d\.c\.b\.o)\b",
        "Dispensary-cum-Branch Office (DCBO)",
        clean_name,
        flags=re.IGNORECASE,
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


def scrape_and_build_dataset():
    print("Executing Overpass spatial extraction across India...")
    headers = {"User-Agent": "ESI-Clinical-Directory-Scraper/2.0"}

    elements = []
    for attempt in range(3):
        try:
            resp = requests.post(OVERPASS_URL, data={"data": OVERPASS_QUERY}, headers=headers, timeout=180)
            if resp.status_code == 200:
                elements = resp.json().get("elements", [])
                print(f"Retrieved {len(elements)} raw records.")
                break
            else:
                print(f"Attempt {attempt + 1}: HTTP {resp.status_code}. Retrying in 10s...")
                time.sleep(10)
        except Exception as e:
            print(f"Attempt {attempt + 1} error: {e}. Retrying in 10s...")
            time.sleep(10)

    verified_facilities: Dict[str, Dict] = {}
    dropped_count = 0

    for el in elements:
        tags = el.get("tags", {})
        raw_name = tags.get("name") or tags.get("name:en") or tags.get("official_name")
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
        address = ", ".join([p for p in addr_parts if p]) or tags.get("addr:full", "")

        pincode = tags.get("addr:postcode", "")
        if not pincode:
            pin_search = re.search(r"\b([1-9][0-9]{5})\b", address + " " + clean_name)
            pincode = pin_search.group(1) if pin_search else ""

        phone = tags.get("phone") or tags.get("contact:phone", "")
        dedup_key = re.sub(r"[^a-zA-Z0-9]", "", clean_name.lower())

        if dedup_key not in verified_facilities:
            verified_facilities[dedup_key] = {
                "id": f"osm_{osm_id}",
                "name": clean_name,
                "category": category,
                "address": address,
                "pincode": pincode,
                "latitude": lat,
                "longitude": lon,
                "phone": phone,
                "maps_url": f"https://www.google.com/maps/search/?api=1&query={lat},{lon}" if lat and lon else "",
            }

    results = list(verified_facilities.values())

    # Write JSON
    with open("esi_master.json", "w", encoding="utf-8") as f_json:
        json.dump(results, f_json, indent=2, ensure_ascii=False)

    # Write CSV
    if results:
        fieldnames = ["id", "name", "category", "address", "pincode", "latitude", "longitude", "phone", "maps_url"]
        with open("esi_master.csv", "w", newline="", encoding="utf-8") as f_csv:
            writer = csv.DictWriter(f_csv, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

    print(f"\nCompleted:")
    print(f"  • Excluded non-clinical entries: {dropped_count}")
    print(f"  • Total verified facilities saved: {len(results)}")
    print(f"  • Files generated: esi_master.csv, esi_master.json")


if __name__ == "__main__":
    scrape_and_build_dataset()
  
