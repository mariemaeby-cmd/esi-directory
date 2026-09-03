import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean(text):
    return " ".join(text.split()).strip() if text else ""

def extract_pincode(text):
    match = re.search(r'\b[1-9][0-9]{5}\b', text)
    return match.group(0) if match else ""

def scrape_all_states():
    records = []
    sources = [
        {"state": "Karnataka", "url": "https://labourlawadvisor.in/blog/esi-hospitals-and-dispensaries-in-karnataka/"},
        {"state": "Delhi", "url": "https://labourlawadvisor.in/blog/esic-hospitals-and-dispensaries-in-delhi/"},
        {"state": "Maharashtra", "url": "https://labourlawadvisor.in/blog/esi-hospitals-dispensaries-in-maharashtra/"},
        {"state": "Telangana", "url": "https://labourlawadvisor.in/blog/esi-hospitals-dispensaries-in-telangana/"},
        {"state": "Tamil Nadu", "url": "https://labourlawadvisor.in/blog/esi-hospitals-and-dispensaries-in-tamil-nadu/"},
        {"state": "West Bengal", "url": "https://labourlawadvisor.in/blog/esi-hospitals-and-dispensaries-in-west-bengal/"},
        {"state": "Gujarat", "url": "https://labourlawadvisor.in/blog/esi-hospitals-and-dispensaries-in-gujarat/"},
        {"state": "Uttar Pradesh", "url": "https://labourlawadvisor.in/blog/esi-hospitals-and-dispensaries-in-uttar-pradesh/"},
        {"state": "Haryana", "url": "https://labourlawadvisor.in/blog/esic-hospitals-and-dispensaries-in-haryana/"},
        {"state": "Rajasthan", "url": "https://labourlawadvisor.in/blog/esi-hospitals-and-dispensaries-in-rajasthan/"},
        {"state": "Punjab", "url": "https://labourlawadvisor.in/blog/esi-hospitals-and-dispensaries-in-punjab/"},
        {"state": "Kerala", "url": "https://labourlawadvisor.in/blog/esi-hospitals-and-dispensaries-in-kerala/"},
        {"state": "Madhya Pradesh", "url": "https://labourlawadvisor.in/blog/esi-hospitals-and-dispensaries-in-madhya-pradesh/"},
        {"state": "Andhra Pradesh", "url": "https://labourlawadvisor.in/blog/esi-hospitals-and-dispensaries-in-andhra-pradesh/"}
    ]
    
    print(f"[*] Starting All-India ESI scrape across {len(sources)} states...")
    
    for src in sources:
        state_name = src["state"]
        url = src["url"]
        print(f"[*] Scraping {state_name}...")
        
        try:
            resp = requests.get(url, headers=HEADERS, timeout=25)
            if resp.status_code != 200:
                continue
                
            soup = BeautifulSoup(resp.content, "html.parser")
            tables = soup.find_all("table")
            
            for table in tables:
                prev = table.find_previous(["h2", "h3", "h4"])
                heading = prev.text.lower() if prev else ""
                ftype = "Hospital" if any(k in heading for k in ["hospital", "tie-up", "pgimsr", "model"]) else "Dispensary"
                
                rows = table.find_all("tr")
                for row in rows[1:]:
                    cols = [clean(td.text) for td in row.find_all(["td", "th"])]
                    if not cols or len(cols) < 2:
                        continue
                    
                    name = cols[0]
                    address = cols[1] if len(cols) > 1 else cols[0]
                    contact = cols[2] if len(cols) > 2 else ""
                    
                    full_text = f"{name} {address} {contact}"
                    pincode = extract_pincode(full_text)
                    
                    records.append({
                        "facility_name": name,
                        "facility_type": ftype,
                        "state": state_name,
                        "address": address,
                        "pincode": pincode,
                        "contact": contact
                    })
            time.sleep(0.5)
        except Exception as e:
            print(f"[!] Error on {state_name}: {e}")

    df = pd.DataFrame(records).drop_duplicates(subset=["facility_name", "state", "address"])
    df.to_csv("esi_master.csv", index=False, encoding="utf-8")
    df.to_json("esi_master.json", orient="records", indent=2)
    print(f"[+] Done! Saved {len(df)} records.")

if __name__ == "__main__":
    scrape_all_states()
  
