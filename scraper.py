import json
import re
import sys
import unicodedata
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# --- Normalization & De-Duplication Utilities ---

def clean_text(text: str) -> str:
    """Normalize unicode characters, strip extra whitespace, and cleanup."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    cleaned = re.sub(r"\s+", " ", normalized)
    return cleaned.strip()

def extract_pincode(text: str) -> str:
    """Extract standard 6-digit Indian PIN code."""
    match = re.search(r"\b([1-9][0-9]{5})\b", text)
    return match.group(1) if match else ""

def generate_dedup_key(name: str, state: str, district: str, pincode: str) -> str:
    """
    Creates a composite key stripping institutional noise prefixes
    to catch cross-directory overlaps.
    """
    noise = r"\b(esic|esis|esi|model|hospital|dispensary|dcbo|clinic|no|no\.|branch)\b"
    sanitized_name = re.sub(noise, "", name.lower())
    sanitized_name = re.sub(r"[^a-z0-9]", "", sanitized_name)
    sanitized_state = re.sub(r"[^a-z0-9]", "", state.lower())
    
    # Primary match on sanitized name + pincode if available
    if pincode:
        return f"{sanitized_name}_{pincode}"
    return f"{sanitized_name}_{sanitized_state}_{district.lower()}"


# --- Scraping Passes ---

def scrape_pass_1_hospitals() -> list[dict]:
    """
    Pass 1: Targets Central ESIC Model Hospitals, PGIMSRs, Medical Colleges,
    and State ESIS secondary hospitals.
    """
    print("[+] Running Pass 1: Central & State ESI Hospitals...")
    hospitals = []
    
    # Official ESIC directory endpoints
    urls = [
        "https://www.esic.gov.in/hospitals",
        "https://www.esic.gov.in/medical-institutions"
    ]
    
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                print(f"[!] Warning: HTTP {resp.status_code} on {url}")
                continue
            
            soup = BeautifulSoup(resp.text, "html.parser")
            tables = soup.find_all("table")
            
            for table in tables:
                rows = table.find_all("tr")[1:]  # skip header
                for row in rows:
                    cols = [clean_text(td.get_text()) for td in row.find_all("td")]
                    if len(cols) >= 3:
                        # Extract table fields flexibly
                        name = cols[1] if len(cols) > 1 else cols[0]
                        address = cols[2] if len(cols) > 2 else ""
                        state = cols[3] if len(cols) > 3 else ""
                        
                        pin = extract_pincode(address) or extract_pincode(name)
                        
                        # Institutional Tier Classification
                        name_upper = name.upper()
                        if "MEDICAL COLLEGE" in name_upper or "PGIMSR" in name_upper:
                            ftype = "CENTRAL_ESIC_COLLEGE"
                        elif "MODEL HOSPITAL" in name_upper:
                            ftype = "CENTRAL_ESIC_MODEL_HOSPITAL"
                        elif "ESIS" in name_upper or "STATE" in name_upper:
                            ftype = "STATE_ESIS_HOSPITAL"
                        else:
                            ftype = "GOVT_ESI_HOSPITAL"

                        hospitals.append({
                            "name": name,
                            "facility_type": ftype,
                            "address": address,
                            "state": state,
                            "district": "",
                            "pincode": pin,
                            "is_government_owned": True,
                            "source_tier": "TIER_1_2_HOSPITAL"
                        })
        except Exception as e:
            print(f"[!] Error in Pass 1 for {url}: {e}")
            
    print(f"[✓] Pass 1 complete. Found {len(hospitals)} raw hospital records.")
    return hospitals


def scrape_pass_2_dispensaries_statewise() -> list[dict]:
    """
    Pass 2: State-wise sweep for all ESI Dispensaries, DCBOs, and regional
    medical centers.
    """
    print("[+] Running Pass 2: State-wise Dispensaries and DCBOs...")
    dispensaries = []
    
    urls = [
        "https://www.esic.gov.in/dispensaries",
        "https://www.esic.gov.in/dcbo"
    ]
    
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=25)
            if resp.status_code != 200:
                print(f"[!] Warning: HTTP {resp.status_code} on {url}")
                continue
                
            soup = BeautifulSoup(resp.text, "html.parser")
            tables = soup.find_all("table")
            
            for table in tables:
                rows = table.find_all("tr")[1:]
                for row in rows:
                    cols = [clean_text(td.get_text()) for td in row.find_all("td")]
                    if len(cols) >= 3:
                        name = cols[1] if len(cols) > 1 else cols[0]
                        address = cols[2] if len(cols) > 2 else ""
                        state = cols[3] if len(cols) > 3 else ""
                        district = cols[4] if len(cols) > 4 else ""
                        
                        pin = extract_pincode(address) or extract_pincode(name)
                        
                        name_upper = name.upper()
                        if "DCBO" in name_upper or "BRANCH" in name_upper:
                            ftype = "DISPENSARY_CUM_BRANCH_OFFICE"
                        else:
                            ftype = "STATE_ESI_DISPENSARY"

                        dispensaries.append({
                            "name": name,
                            "facility_type": ftype,
                            "address": address,
                            "state": state,
                            "district": district,
                            "pincode": pin,
                            "is_government_owned": True,
                            "source_tier": "TIER_3_PRIMARY_DISPENSARY"
                        })
        except Exception as e:
            print(f"[!] Error in Pass 2 for {url}: {e}")
            
    print(f"[✓] Pass 2 complete. Found {len(dispensaries)} raw dispensary records.")
    return dispensaries


# --- Main Pipeline & Deduplication ---

def main():
    pass1_records = scrape_pass_1_hospitals()
    pass2_records = scrape_pass_2_dispensaries_statewise()
    
    combined_raw = pass1_records + pass2_records
    total_raw_count = len(combined_raw)
    print(f"\n[+] Total raw records extracted: {total_raw_count}")
    
    # Deduplication
    unique_facilities = {}
    for item in combined_raw:
        key = generate_dedup_key(
            item["name"], 
            item["state"], 
            item["district"], 
            item["pincode"]
        )
        # Prefer higher-tier classification if duplicate exists
        if key not in unique_facilities or "HOSPITAL" in item["facility_type"]:
            unique_facilities[key] = item
            
    deduped_records = list(unique_facilities.values())
    print(f"[✓] De-duplicated down to: {len(deduped_records)} canonical records.")
    
    # --- CIRCUIT BREAKER SAFEGUARD ---
    # Prevents empty commits from wiping master data on runner failure
    MIN_THRESHOLD = 100
    if len(deduped_records) < MIN_THRESHOLD:
        print(f"\n[!] CIRCUIT BREAKER TRIPPED:")
        print(f"    Expected >= {MIN_THRESHOLD} records, but only parsed {len(deduped_records)}.")
        print("    Aborting write to preserve existing master database.")
        sys.exit(1)
        
    output_filename = "esi_master_directory.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(deduped_records, f, indent=2, ensure_ascii=False)
        
    print(f"\n[🚀] SUCCESS: Clean dataset saved to '{output_filename}' ({len(deduped_records)} facilities).")


if __name__ == "__main__":
    main()
    
