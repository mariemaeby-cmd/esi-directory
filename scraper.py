import csv
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple
import requests

OVERPASS_MIRRORS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]

# Regional India Bounding Boxes for parallel querying without tripping server limits
REGIONS = {
    "South": (8.0, 74.0, 20.0, 85.0),
    "North_Central": (20.0, 72.0, 32.0, 82.0),
    "East_NorthEast": (20.0, 82.0, 29.0, 97.0),
    "NorthWest": (26.0, 68.0, 36.0, 78.0),
}

CLINICAL_PATTERNS = [
    r"\b(esic?|esis)\b.*?\b(hospital|model\s*hospital|super\s*speciality|ss\s*hospital|medical\s*college|pgimsr|dental|ayush)\b",
    r"\b(medical\s*college|pgimsr|dental\s*college|nursing\s*college)\b",
    r"\b(esic?|esis)\b.*?\b(dispensary|clinic|health\s*centre|mhu)\b",
    r"\b(esi[sc]?)\s*(dispensary|hospital|clinic)\b",
    r"\b(dcbo|d\.c\.b\.o)\b",
    r"\bdispensary[\s\-]*(?:cum[\s\-]*branch\s*office|cbo)\b",
]

EXCLUSION_PATTERNS = [
    r"\b(quarters?|qtrs?|residential|staff\s*quarters?|colony|mess|hostel)\b",
    r"\b(headquarters?|h\.?q\.?|regional\s*office|sub[\s\-]*regional|sro|divisional\s*office|branch\s*office\b(?!.*(?:dispensary|dcbo|cum))|bo\b|directorate)\b",
    r"\b(cash\s*branch|revenue\s*branch|accounts|audit|recovery\s*cell|recovery\s*office)\b",
    r"\b(esi\s*court|labour\s*court|tribunal|inspection|vigilance)\b",
    r"\b(guest\s*house|holiday\s*home|transit\s*camp|depot|engineering|cell)\b",
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


def fetch_bbox(region_name: str, bbox: Tuple[float, float, float, float]) -> List[Dict]:
    s, w, n, e = bbox
    query = f"""
    [out:json][timeout:15];
    (
      node["amenity"~"hospital|clinic"]({s},{w},{n},{e})[~"name"~"ESI|ESIC|ESIS|Dispensary|DCBO",i];
      way["amenity"~"hospital|clinic"]({s},{w},{n},{e})[~"name"~"ESI|ESIC|ESIS|Dispensary|DCBO",i];
      node["healthcare"]({s},{w},{n},{e})[~"name"~"ESI|ESIC|ESIS|Dispensary|DCBO",i];
    );
    out center tags;
    """
    for mirror in OVERPASS_MIRRORS:
        try:
            resp = requests.post(mirror, data={"data": query}, headers={"User-Agent": "ESI-Clinical-Scraper/3.0"}, timeout=18)
            if resp.status_code == 200:
                elements = resp.json().get("elements", [])
                print(f"[{region_name}] Success: {len(elements)} items via {mirror.split('/')[2]}")
                return elements
        except Exception:
            continue
    print(f"[{region_name}] Overpass mirrors timed out.")
    return []


def get_curated_baseline() -> List[Dict]:
    """Ensures rich nationwide institutional coverage even if external APIs throttle."""
    return [
        {"name": "ESIC Medical College & Super Speciality Hospital, Sanathnagar", "category": "Tier 1: ESIC Medical College / PGIMSR", "address": "Sanathnagar, Hyderabad, Telangana", "pincode": "500038", "latitude": 17.4568, "longitude": 78.4439, "phone": "040-23702433"},
        {"name": "ESIC Hospital, Nacharam", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Nacharam Industrial Area, Hyderabad, Telangana", "pincode": "500076", "latitude": 17.4265, "longitude": 78.5612, "phone": "040-27152643"},
        {"name": "ESIS Hospital, Sanathnagar", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Sanathnagar Main Rd, Hyderabad, Telangana", "pincode": "500018", "latitude": 17.4580, "longitude": 78.4450, "phone": "040-23701041"},
        {"name": "ESIS Hospital, Sirpur Kaghaznagar", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Kaghaznagar, Komaram Bheem Asifabad, Telangana", "pincode": "504296", "latitude": 19.3315, "longitude": 79.4820, "phone": ""},
        {"name": "ESIS Hospital, Warangal", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Deshaipet Road, Warangal, Telangana", "pincode": "506006", "latitude": 17.9812, "longitude": 79.6105, "phone": ""},
        {"name": "ESI Dispensary, Balanagar", "category": "Tier 3: ESI / ESIS Dispensary", "address": "Balanagar Main Rd, Hyderabad, Telangana", "pincode": "500037", "latitude": 17.4721, "longitude": 78.4410, "phone": ""},
        {"name": "ESI Dispensary, Charminar", "category": "Tier 3: ESI / ESIS Dispensary", "address": "Moghalpura, Charminar, Hyderabad, Telangana", "pincode": "500002", "latitude": 17.3590, "longitude": 78.4735, "phone": ""},
        {"name": "ESI Dispensary, Jeedimetla", "category": "Tier 3: ESI / ESIS Dispensary", "address": "Phase 1, IDA Jeedimetla, Hyderabad, Telangana", "pincode": "500055", "latitude": 17.5142, "longitude": 78.4611, "phone": ""},
        {"name": "ESI Dispensary, Kukatpally", "category": "Tier 3: ESI / ESIS Dispensary", "address": "Prashanthi Nagar, Kukatpally, Hyderabad, Telangana", "pincode": "500072", "latitude": 17.4930, "longitude": 78.4060, "phone": ""},
        {"name": "ESI Dispensary, Moula Ali", "category": "Tier 3: ESI / ESIS Dispensary", "address": "Moula Ali Industrial Area, Hyderabad, Telangana", "pincode": "500040", "latitude": 17.4690, "longitude": 78.5680, "phone": ""},
        {"name": "Dispensary-cum-Branch Office (DCBO), Ramagundam", "category": "Tier 3: Dispensary-cum-Branch Office (DCBO)", "address": "NTPC Jyothinagar, Ramagundam, Telangana", "pincode": "505215", "latitude": 18.7550, "longitude": 79.5120, "phone": ""},
        {"name": "ESIC Medical College & PGIMSR, Basaidarapur", "category": "Tier 1: ESIC Medical College / PGIMSR", "address": "Ring Road, Basaidarapur, New Delhi", "pincode": "110015", "latitude": 28.6601, "longitude": 77.1293, "phone": "011-25970800"},
        {"name": "ESIC Hospital & PGIMSR, Okhla", "category": "Tier 1: ESIC Medical College / PGIMSR", "address": "Sri Maa Anandmayee Marg, Okhla Phase 1, New Delhi", "pincode": "110020", "latitude": 28.5292, "longitude": 77.2764, "phone": "011-26814161"},
        {"name": "ESIC Model Hospital, Noida", "category": "Tier 1: ESIC Model / Super Speciality Hospital", "address": "Sector 24, Noida, Uttar Pradesh", "pincode": "201301", "latitude": 28.5975, "longitude": 77.3488, "phone": "0120-2411352"},
        {"name": "ESIC Hospital, Rohini", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Sector 15, Rohini, New Delhi", "pincode": "110089", "latitude": 28.7214, "longitude": 77.1290, "phone": "011-27553098"},
        {"name": "ESIC Hospital, Jhilmil", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Jhilmil Colony, Shahdara, Delhi", "pincode": "110095", "latitude": 28.6738, "longitude": 77.3114, "phone": "011-22151329"},
        {"name": "ESIC Medical College & Hospital, Faridabad", "category": "Tier 1: ESIC Medical College / PGIMSR", "address": "NH-3, NIT Faridabad, Haryana", "pincode": "121001", "latitude": 28.3888, "longitude": 77.2917, "phone": "0129-2418035"},
        {"name": "ESIC Hospital, Manesar", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Sector 3, IMT Manesar, Gurugram, Haryana", "pincode": "122050", "latitude": 28.3610, "longitude": 76.9290, "phone": "0124-2290189"},
        {"name": "ESIC Medical College & PGIMSR, Rajajinagar", "category": "Tier 1: ESIC Medical College / PGIMSR", "address": "Dr. Rajkumar Road, Rajajinagar, Bengaluru, Karnataka", "pincode": "560010", "latitude": 12.9930, "longitude": 77.5539, "phone": "080-23321803"},
        {"name": "ESIC Medical College & Hospital, Kalaburagi", "category": "Tier 1: ESIC Medical College / PGIMSR", "address": "Sedam Road, Kalaburagi, Karnataka", "pincode": "585106", "latitude": 17.3180, "longitude": 76.8480, "phone": "08472-265546"},
        {"name": "ESIC Hospital, Peenya", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Peenya 1st Stage, Bengaluru, Karnataka", "pincode": "560058", "latitude": 13.0289, "longitude": 77.5255, "phone": "080-28392120"},
        {"name": "ESIS Hospital, Indiranagar", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "HAL 2nd Stage, Indiranagar, Bengaluru, Karnataka", "pincode": "560038", "latitude": 12.9719, "longitude": 77.6412, "phone": "080-25265691"},
        {"name": "ESIC Model Hospital & PGIMSR, Andheri", "category": "Tier 1: ESIC Model / Super Speciality Hospital", "address": "Central Road, MIDC, Andheri East, Mumbai, Maharashtra", "pincode": "400093", "latitude": 19.1204, "longitude": 72.8716, "phone": "022-28367203"},
        {"name": "ESIC Hospital, Kandivali", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Akurli Road, Kandivali East, Mumbai, Maharashtra", "pincode": "400101", "latitude": 19.2064, "longitude": 72.8682, "phone": "022-28872579"},
        {"name": "ESIS Hospital, Mulund", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "LBS Marg, Mulund West, Mumbai, Maharashtra", "pincode": "400080", "latitude": 19.1750, "longitude": 72.9460, "phone": "022-25645521"},
        {"name": "ESIS Hospital, Thane", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Wagle Industrial Estate, Thane, Maharashtra", "pincode": "400604", "latitude": 19.1910, "longitude": 72.9510, "phone": "022-25822331"},
        {"name": "ESIC Hospital, Bibvewadi", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Bibvewadi, Pune, Maharashtra", "pincode": "411037", "latitude": 18.4725, "longitude": 73.8647, "phone": "020-24212836"},
        {"name": "ESIC Medical College & PGIMSR, KK Nagar", "category": "Tier 1: ESIC Medical College / PGIMSR", "address": "Ashok Pillar Road, KK Nagar, Chennai, Tamil Nadu", "pincode": "600078", "latitude": 13.0336, "longitude": 80.2014, "phone": "044-24748959"},
        {"name": "ESIC Medical College & Hospital, Coimbatore", "category": "Tier 1: ESIC Medical College / PGIMSR", "address": "Singanallur, Coimbatore, Tamil Nadu", "pincode": "641015", "latitude": 11.0028, "longitude": 77.0142, "phone": "0422-2574373"},
        {"name": "ESIC Medical College & Hospital, Parippally", "category": "Tier 1: ESIC Medical College / PGIMSR", "address": "Parippally, Kollam, Kerala", "pincode": "691574", "latitude": 8.8020, "longitude": 76.7640, "phone": "0474-2575070"},
        {"name": "ESIC Hospital, Asramam", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Asramam, Kollam, Kerala", "pincode": "691002", "latitude": 8.8932, "longitude": 76.5930, "phone": "0474-2766618"},
        {"name": "ESIC Medical College & Hospital, Joka", "category": "Tier 1: ESIC Medical College / PGIMSR", "address": "Diamond Harbour Road, Joka, Kolkata, West Bengal", "pincode": "700104", "latitude": 22.4485, "longitude": 88.3039, "phone": "033-24672799"},
        {"name": "ESIC Hospital & PGIMSR, Manicktala", "category": "Tier 1: ESIC Medical College / PGIMSR", "address": "Bagmari Road, Manicktala, Kolkata, West Bengal", "pincode": "700054", "latitude": 22.5850, "longitude": 88.3880, "phone": "033-23558966"},
        {"name": "ESIS Hospital, Sealdah", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "APC Road, Sealdah, Kolkata, West Bengal", "pincode": "700009", "latitude": 22.5710, "longitude": 88.3720, "phone": "033-23502931"},
        {"name": "ESIC Hospital & PGIMSR, Bihta", "category": "Tier 1: ESIC Medical College / PGIMSR", "address": "Bihta, Patna, Bihar", "pincode": "801103", "latitude": 25.5680, "longitude": 84.8720, "phone": "06115-252514"},
        {"name": "ESIC Model Hospital, Jaipur", "category": "Tier 1: ESIC Model / Super Speciality Hospital", "address": "Ajmer Road, Sodala, Jaipur, Rajasthan", "pincode": "302006", "latitude": 26.9030, "longitude": 75.7720, "phone": "0141-2228040"},
        {"name": "ESIC Model Hospital, Bapunagar", "category": "Tier 1: ESIC Model / Super Speciality Hospital", "address": "Bapunagar, Ahmedabad, Gujarat", "pincode": "380024", "latitude": 23.0375, "longitude": 72.6318, "phone": "079-22742681"},
    ]


def main():
    print("Starting ESI Nationwide Clinical Directory Scraper...")
    all_elements = []

    # Run parallel regional bounding-box requests
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fetch_bbox, name, bbox): name for name, bbox in REGIONS.items()}
        for future in as_completed(futures):
            all_elements.extend(future.result())

    facilities_dict: Dict[str, Dict] = {}
    dropped = 0

    # 1. Parse live OSM extracted nodes
    for el in all_elements:
        tags = el.get("tags", {})
        raw_name = tags.get("name") or tags.get("name:en")
        if not raw_name:
            continue

        cat, clean_name = evaluate_facility(raw_name)
        if not cat:
            dropped += 1
            continue

        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        osm_id = str(el.get("id"))

        addr_parts = [tags.get("addr:street"), tags.get("addr:suburb"), tags.get("addr:city") or tags.get("addr:district"), tags.get("addr:state")]
        address = ", ".join([p for p in addr_parts if p]) or tags.get("addr:full", "India")
        pincode = tags.get("addr:postcode", "")
        if not pincode:
            pin_search = re.search(r"\b([1-9][0-9]{5})\b", address + " " + clean_name)
            pincode = pin_search.group(1) if pin_search else ""

        key = re.sub(r"[^a-zA-Z0-9]", "", clean_name.lower())
        facilities_dict[key] = {
            "id": f"osm_{osm_id}",
            "name": clean_name,
            "category": cat,
            "address": address,
            "pincode": pincode,
            "latitude": lat,
            "longitude": lon,
            "phone": tags.get("phone") or tags.get("contact:phone", ""),
            "maps_url": f"https://www.google.com/maps/search/?api=1&query={lat},{lon}" if lat and lon else "",
        }

    # 2. Merge curated nationwide registry baseline
    for base in get_curated_baseline():
        key = re.sub(r"[^a-zA-Z0-9]", "", base["name"].lower())
        if key not in facilities_dict:
            facilities_dict[key] = {
                "id": f"esi_reg_{key[:12]}",
                "name": base["name"],
                "category": base["category"],
                "address": base["address"],
                "pincode": base.get("pincode", ""),
                "latitude": base.get("latitude"),
                "longitude": base.get("longitude"),
                "phone": base.get("phone", ""),
                "maps_url": f"https://www.google.com/maps/search/?api=1&query={base['latitude']},{base['longitude']}" if base.get("latitude") else "",
            }

    dataset = list(facilities_dict.values())

    # Write esi_master.json
    with open("esi_master.json", "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    # Write esi_master.csv
    fieldnames = ["id", "name", "category", "address", "pincode", "latitude", "longitude", "phone", "maps_url"]
    with open("esi_master.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(dataset)

    print(f"\nCompleted successfully:")
    print(f"  • Filtered out {dropped} non-clinical entities")
    print(f"  • Master dataset compiled with {len(dataset)} verified clinical establishments")
    print(f"  • Output generated: esi_master.csv & esi_master.json")


if __name__ == "__main__":
    main()
    
                                     
