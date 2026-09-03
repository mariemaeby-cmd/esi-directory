import json
import re
import time
from typing import Dict, List, Optional, Tuple
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
}

# Positive patterns matching authorized clinical care facilities
CLINICAL_PATTERNS = [
    r"\b(esic?|esis)\b.*?\b(hospital|model hospital|super\s*speciality|ss\s*hospital|medical college|pgimsr|dental college)\b",
    r"\b(medical college|pgimsr|dental college|nursing college)\b",
    r"\b(esic?|esis)\b.*?\b(dispensary|clinic|health\s*centre|mhu|mobile\s*dispensary)\b",
    r"\b(esi[sc]?)\s*(dispensary|hospital)\b",
    r"\b(dcbo|d\.c\.b\.o)\b",
    r"\bdispensary[\s\-]*(?:cum[\s\-]*branch\s*office|cbo)\b",
]

# Strict exclusions: Drop residential, administrative, judicial, and financial offices
EXCLUSION_PATTERNS = [
    r"\b(quarters?|qtrs?|residential|colony|staff\s*quarters?|hostel|mess)\b",
    r"\b(headquarters?|h\.?q\.?|regional\s*office|sub[\s\-]*regional\s*office|sro|divisional\s*office|branch\s*office\b(?!.*(?:dispensary|dcbo|cum))|bo\b|directorate)\b",
    r"\b(cash\s*branch|revenue\s*branch|accounts|audit|recovery\s*cell|recovery\s*office)\b",
    r"\b(court|tribunal|inspection|vigilance)\b",
    r"\b(guest\s*house|holiday\s*home|transit\s*camp|depot|engineering|cell)\b",
]

COMPILED_CLINICAL = [re.compile(p, re.IGNORECASE) for p in CLINICAL_PATTERNS]
COMPILED_EXCLUSIONS = [re.compile(p, re.IGNORECASE) for p in EXCLUSION_PATTERNS]


def evaluate_and_clean_facility(name: str) -> Tuple[Optional[str], str]:
    clean_name = re.sub(r"\s+", " ", name).strip()

    # 1. Reject administrative/residential keywords
    for exclusion in COMPILED_EXCLUSIONS:
        if exclusion.search(clean_name):
            return None, clean_name

    # 2. Check clinical pattern match
    if not any(pattern.search(clean_name) for pattern in COMPILED_CLINICAL):
        return None, clean_name

    # 3. Standardize and expand DCBO acronyms
    clean_name = re.sub(
        r"\b(dcbo|d\.c\.b\.o)\b",
        "Dispensary-cum-Branch Office (DCBO)",
        clean_name,
        flags=re.IGNORECASE,
    )

    # 4. Assign tier classification
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


def clean_text(text: Optional[str]) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def scrape_all_esi_facilities() -> List[Dict]:
    session = requests.Session()
    session.headers.update(HEADERS)
    facilities_dict: Dict[str, Dict] = {}
    dropped_count = 0

    # Source endpoints across ESIC portal
    ENDPOINTS = [
        {"url": "https://www.esic.gov.in/hospitals", "type": "hospital"},
        {"url": "https://www.esic.gov.in/medical-colleges-institutions", "type": "medical_college"},
        {"url": "https://www.esic.gov.in/dispensaries", "type": "dispensary"},
        {"url": "https://www.esic.gov.in/dcbo", "type": "dcbo"},
        {"url": "https://www.esic.gov.in/ayush", "type": "hospital"},
    ]

    for ep in ENDPOINTS:
        url = ep["url"]
        print(f"Scraping endpoint: {url} ...")
        try:
            resp = session.get(url, timeout=25)
            if resp.status_code != 200:
                print(f"  [!] HTTP {resp.status_code} received from {url}")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            tables = soup.find_all("table")

            for table in tables:
                rows = table.find_all("tr")
                for row in rows[1:]:  # skip header row
                    cols = [clean_text(td.get_text()) for td in row.find_all("td")]
                    if len(cols) < 2:
                        continue

                    raw_name = ""
                    address = ""
                    phone = ""
                    state = ""

                    # Dynamic column matching based on table shape
                    if len(cols) >= 4:
                        state = cols[1] if len(cols[1]) < 30 else ""
                        raw_name = cols[2] if len(cols[2]) > 3 else cols[1]
                        address = cols[3] if len(cols) > 3 else ""
                        phone = cols[4] if len(cols) > 4 else ""
                    elif len(cols) == 3:
                        raw_name = cols[1]
                        address = cols[2]
                    else:
                        raw_name = cols[0]
                        address = cols[1]

                    category, clean_name = evaluate_and_clean_facility(raw_name)

                    if category is None:
                        dropped_count += 1
                        continue

                    # Extract standard 6-digit PIN code
                    pin_match = re.search(r"\b([1-9][0-9]{5})\b", address + " " + clean_name)
                    pincode = pin_match.group(1) if pin_match else ""

                    # Clean phone numbers
                    phone_match = re.search(r"(\+?\d[\d\s\-]{7,14}\d)", phone)
                    clean_phone = phone_match.group(1).replace(" ", "") if phone_match else ""

                    # Deduplication key
                    unique_key = re.sub(r"[^a-zA-Z0-9]", "", (clean_name + pincode).lower())

                    if unique_key and unique_key not in facilities_dict:
                        full_address = f"{address}, {state}".strip(", ")
                        facilities_dict[unique_key] = {
                            "name": clean_name,
                            "category": category,
                            "address": full_address,
                            "pincode": pincode,
                            "phone": clean_phone,
                            "maps_url": f"https://www.google.com/maps/search/?api=1&query={requests.utils.quote(clean_name + ' ' + full_address)}",
                            "source": "esic_portal_scraped",
                        }

            time.sleep(1)

        except Exception as e:
            print(f"  [X] Failed scraping {url}: {e}")

    # Fallback / Overpass augmentation if government portals throttle
    if len(facilities_dict) < 50:
        print("Government portal throttled/blocked. Pulling complete geospatial nodes...")
        try:
            overpass_url = "https://overpass-api.de/api/interpreter"
            query = """
            [out:json][timeout:60];
            area["ISO3166-1"="IN"][admin_level=2]->.india;
            (
              node["amenity"~"hospital|clinic|doctors"](area.india)[~"name"~"ESI|ESIC|ESIS|Dispensary",i];
              way["amenity"~"hospital|clinic|doctors"](area.india)[~"name"~"ESI|ESIC|ESIS|Dispensary",i];
            );
            out center tags;
            """
            r = session.post(overpass_url, data={"data": query}, timeout=90)
            if r.status_code == 200:
                nodes = r.json().get("elements", [])
                for node in nodes:
                    tags = node.get("tags", {})
                    name = tags.get("name") or tags.get("name:en")
                    if not name:
                        continue
                    cat, c_name = evaluate_and_clean_facility(name)
                    if not cat:
                        dropped_count += 1
                        continue

                    lat = node.get("lat") or node.get("center", {}).get("lat")
                    lon = node.get("lon") or node.get("center", {}).get("lon")
                    addr = tags.get("addr:full") or tags.get("addr:street") or "India"

                    k = re.sub(r"[^a-zA-Z0-9]", "", c_name.lower())
                    if k not in facilities_dict:
                        facilities_dict[k] = {
                            "name": c_name,
                            "category": cat,
                            "address": addr,
                            "latitude": lat,
                            "longitude": lon,
                            "pincode": tags.get("addr:postcode", ""),
                            "phone": tags.get("phone", ""),
                            "maps_url": f"https://www.google.com/maps/search/?api=1&query={lat},{lon}" if lat and lon else "",
                            "source": "geospatial_augmented",
                        }
        except Exception as err:
            print(f"Augmentation error: {err}")

    results = list(facilities_dict.values())
    output_file = "esi_master.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nProcessing Complete:")
    print(f"  • Excluded non-clinical (offices/quarters): {dropped_count}")
    print(f"  • Verified clinical institutions saved: {len(results)}")
    print(f"  • Written to: {output_file}")
    return results


if __name__ == "__main__":
    scrape_all_esi_facilities()
                    
