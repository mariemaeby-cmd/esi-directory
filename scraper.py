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

def scrape_master_esi():
    records = []
    
    # 1. State-wise comprehensive portals (Dispensaries + State Hospitals)
    states = [
        "andhra-pradesh", "assam", "bihar", "chandigarh", "chhattisgarh", 
        "delhi", "goa", "gujarat", "haryana", "himachal-pradesh", 
        "jammu-kashmir", "jharkhand", "karnataka", "kerala", "madhya-pradesh", 
        "maharashtra", "odisha", "puducherry", "punjab", "rajasthan", 
        "tamil-nadu", "telangana", "uttarakhand", "uttar-pradesh", "west-bengal"
    ]
    
    print("[*] Scraping State ESI Dispensaries & Hospitals...")
    for st in states:
        url = f"https://labourlawadvisor.in/blog/esi-hospitals-and-dispensaries-in-{st}/"
        # Fallback URL format check
        alt_url = f"https://labourlawadvisor.in/blog/esi-hospitals-dispensaries-in-{st}/"
        
        for target_url in [url, alt_url]:
            try:
                resp = requests.get(target_url, headers=HEADERS, timeout=15)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.content, "html.parser")
                    for table in soup.find_all("table"):
                        prev = table.find_previous(["h2", "h3", "h4", "p"])
                        h_text = prev.text.lower() if prev else ""
                        
                        ftype = "Hospital" if any(x in h_text for x in ["hospital", "tie-up", "model", "super"]) else "Dispensary"
                        
                        for row in table.find_all("tr")[1:]:
                            cols = [clean(td.text) for td in row.find_all(["td", "th"])]
                            if len(cols) >= 2:
                                name = cols[0]
                                addr = cols[1] if len(cols) > 1 else cols[0]
                                contact = cols[2] if len(cols) > 2 else ""
                                pcode = extract_pincode(f"{name} {addr}")
                                
                                records.append({
                                    "facility_name": name,
                                    "facility_type": ftype,
                                    "category": "Direct ESIC/ESIS",
                                    "state": st.replace("-", " ").title(),
                                    "address": addr,
                                    "pincode": pcode,
                                    "contact": contact
                                })
                    break
            except Exception:
                continue
            time.sleep(0.2)

    # 2. Add National Health Portal (NHP) Open Directory for CGHS/ESI Empanelled Centers
    print("[*] Fetching empanelled network facilities...")
    nhp_url = "https://raw.githubusercontent.com/datameet/health-facilities-india/master/data/esic_hospitals.json"
    try:
        r = requests.get(nhp_url, timeout=20)
        if r.status_code == 200:
            data = r.json()
            for item in data:
                records.append({
                    "facility_name": item.get("name", ""),
                    "facility_type": item.get("type", "Empanelled Hospital"),
                    "category": "Tie-Up Network",
                    "state": item.get("state", ""),
                    "address": item.get("address", ""),
                    "pincode": item.get("pincode", ""),
                    "contact": item.get("contact", "")
                })
    except Exception:
        pass

    df = pd.DataFrame(records).drop_duplicates(subset=["facility_name", "state", "address"])
    df.to_csv("esi_master.csv", index=False, encoding="utf-8")
    df.to_json("esi_master.json", orient="records", indent=2)
    print(f"\n[+] Master compilation complete: Saved {len(df)} total institutions.")

if __name__ == "__main__":
    scrape_master_esi()
                            
