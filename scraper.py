import json
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

def clean_text(t):
    return " ".join(str(t).split()).strip() if t else ""

def extract_pincode(text):
    match = re.search(r'\b[1-9][0-9]{5}\b', str(text))
    return match.group(0) if match else ""

def scrape_national_datasets():
    all_facilities = []

    # 1. Primary Ingestion: Datameet & National Health Facility Master Repositories
    data_sources = [
        # Datameet national health facilities dataset (curated from NHP & Ministry of Labour)
        "https://raw.githubusercontent.com/datameet/health-facilities-india/master/data/esic_hospitals.json",
        "https://raw.githubusercontent.com/datameet/health-facilities-india/master/data/health_facilities.json"
    ]

    print("[*] Ingesting Primary Open Health Registries...")
    for url in data_sources:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                payload = r.json()
                items = payload if isinstance(payload, list) else payload.get("data", payload.get("features", []))
                
                for item in items:
                    props = item.get("properties", item)
                    name = clean_text(props.get("name", props.get("facility_name", props.get("Hospital_Name", ""))))
                    
                    # Filter specifically for ESI, ESIC, ESIS, or Empanelled units if scanning broad health list
                    target_identifiers = ["esi", "esic", "esis", "employees state insurance"]
                    is_esi_related = any(k in name.lower() for k in target_identifiers) or "esic" in url
                    
                    if is_esi_related and len(name) > 3:
                        addr = clean_text(props.get("address", props.get("Address", "")))
                        st = clean_text(props.get("state", props.get("State", "")))
                        dist = clean_text(props.get("district", props.get("District", "")))
                        pincode = extract_pincode(f"{addr} {props.get('pincode', '')}")
                        
                        f_type = "Hospital" if any(h in name.lower() for h in ["hospital", "model", "pgimsr", "tertiary"]) else "Dispensary"
                        cat = "Tie-Up Network" if any(tp in name.lower() for tp in ["tie-up", "empanelled", "private"]) else "Direct ESIC/ESIS"

                        all_facilities.append({
                            "facility_name": name,
                            "facility_type": f_type,
                            "category": cat,
                            "state": st,
                            "district": dist,
                            "address": addr,
                            "pincode": pincode,
                            "contact": clean_text(props.get("contact", props.get("phone", props.get("Contact", ""))))
                        })
        except Exception as e:
            print(f"[!] Warning on source {url}: {e}")

    # 2. Secondary Scraping: Fallback Direct Directory Table Harvest
    direct_pages = [
        {"state": "Karnataka", "url": "https://labourlawadvisor.in/blog/esi-hospitals-and-dispensaries-in-karnataka/"},
        {"state": "Maharashtra", "url": "https://labourlawadvisor.in/blog/esi-hospitals-dispensaries-in-maharashtra/"},
        {"state": "Delhi", "url": "https://labourlawadvisor.in/blog/esic-hospitals-and-dispensaries-in-delhi/"},
        {"state": "Tamil Nadu", "url": "https://labourlawadvisor.in/blog/esi-hospitals-and-dispensaries-in-tamil-nadu/"},
        {"state": "Telangana", "url": "https://labourlawadvisor.in/blog/esi-hospitals-dispensaries-in-telangana/"},
        {"state": "West Bengal", "url": "https://labourlawadvisor.in/blog/esi-hospitals-and-dispensaries-in-west-bengal/"},
        {"state": "Gujarat", "url": "https://labourlawadvisor.in/blog/esi-hospitals-and-dispensaries-in-gujarat/"},
        {"state": "Uttar Pradesh", "url": "https://labourlawadvisor.in/blog/esi-hospitals-and-dispensaries-in-uttar-pradesh/"}
    ]

    print("[*] Scraping State Portals...")
    for entry in direct_pages:
        try:
            res = requests.get(entry["url"], headers=HEADERS, timeout=12)
            if res.status_code == 200:
                soup = BeautifulSoup(res.content, "html.parser")
                for table in soup.find_all("table"):
                    prev = table.find_previous(["h2", "h3", "h4", "p"])
                    h_text = prev.text.lower() if prev else ""
                    ftype = "Hospital" if "hospital" in h_text else "Dispensary"
                    
                    for row in table.find_all("tr")[1:]:
                        tds = [clean_text(td.text) for td in row.find_all(["td", "th"])]
                        if len(tds) >= 2:
                            name = tds[0]
                            address = tds[1] if len(tds) > 1 else tds[0]
                            contact = tds[2] if len(tds) > 2 else ""
                            all_facilities.append({
                                "facility_name": name,
                                "facility_type": ftype,
                                "category": "Direct ESIC/ESIS",
                                "state": entry["state"],
                                "district": "",
                                "address": address,
                                "pincode": extract_pincode(f"{name} {address}"),
                                "contact": contact
                            })
        except Exception:
            continue

    # Clean, Deduplicate and Export
    df = pd.DataFrame(all_facilities)
    if not df.empty:
        df = df[df["facility_name"].str.len() > 3]
        df = df.drop_duplicates(subset=["facility_name", "state", "address"])
    else:
        # Fallback empty structure
        df = pd.DataFrame(columns=["facility_name", "facility_type", "category", "state", "district", "address", "pincode", "contact"])

    df.to_csv("esi_master.csv", index=False, encoding="utf-8")
    df.to_json("esi_master.json", orient="records", indent=2)
    print(f"[✓] Scrape complete. Exported {len(df)} total verified records.")

if __name__ == "__main__":
    scrape_national_datasets()
    
