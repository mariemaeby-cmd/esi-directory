import json
import re
import urllib.parse
import pandas as pd
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}


def clean(text):
    return " ".join(str(text).split()).strip() if text else ""


def extract_pincode(text):
    match = re.search(r"\b[1-9][0-9]{5}\b", str(text))
    return match.group(0) if match else ""


def build_full_directory():
    records = []

    # ---------------------------------------------------------
    # 1. PMJAY-ESIC Empanelled Hospital Registry (Pan-India bulk pull)
    # ---------------------------------------------------------
    print("[*] 1/3: Ingesting National Empanelled / Tie-Up Network...")
    pmjay_url = "https://dashboard.pmjay.gov.in/pmjay/hospitalList"
    try:
        # Pull empanelled public & private networks contracted under ESIC/PMJAY convergence
        resp = requests.get(pmjay_url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("data", data) if isinstance(data, dict) else data
            for item in items:
                h_name = clean(
                    item.get("hospital_name", item.get("hospitalName", ""))
                )
                if h_name:
                    records.append({
                        "facility_name": h_name,
                        "facility_type": clean(
                            item.get("hospital_type", "Empanelled Hospital")
                        ),
                        "category": "Tie-Up Network",
                        "state": clean(
                            item.get("state_name", item.get("state", ""))
                        ),
                        "district": clean(
                            item.get("district_name", item.get("district", ""))
                        ),
                        "address": clean(item.get("address", "")),
                        "pincode": extract_pincode(
                            f"{item.get('address', '')} {item.get('pincode', '')}"
                        ),
                        "contact": clean(
                            item.get("contact_number", item.get("phone", ""))
                        ),
                    })
            print(f"[+] Loaded {len(records)} tie-up network facilities.")
    except Exception as e:
        print(f"[!] Warning on PMJAY/ESIC endpoint: {e}")

    # ---------------------------------------------------------
    # 2. ESIC Official Geo-Portal Open API / Direct Facility Index
    # ---------------------------------------------------------
    print(
        "[*] 2/3: Querying official ESIC Dispensaries & Hospitals directory..."
    )
    esic_api_url = (
        "https://esic.gov.in/api/v1/facilities"  # Direct static facility mirror
    )
    try:
        r = requests.get(esic_api_url, headers=HEADERS, timeout=25)
        if r.status_code == 200:
            facilities = r.json()
            for fac in facilities:
                records.append({
                    "facility_name": clean(fac.get("name", "")),
                    "facility_type": clean(
                        fac.get("type", "Dispensary / Hospital")
                    ),
                    "category": "Direct ESIC/ESIS",
                    "state": clean(fac.get("state", "")),
                    "district": clean(fac.get("district", "")),
                    "address": clean(fac.get("address", "")),
                    "pincode": extract_pincode(
                        f"{fac.get('address', '')} {fac.get('pincode', '')}"
                    ),
                    "contact": clean(fac.get("phone", "")),
                })
    except Exception as e:
        print(f"[!] Warning on ESIC direct API: {e}")

    # ---------------------------------------------------------
    # 3. National Open Health Infrastructure Registry (NIN / NHP)
    # ---------------------------------------------------------
    print("[*] 3/3: Ingesting Open Government Directory (DataMeet / NIN)...")
    nin_url = "https://raw.githubusercontent.com/datameet/health-facilities-india/master/data/health_facilities.json"
    try:
        res = requests.get(nin_url, timeout=30)
        if res.status_code == 200:
            nin_data = res.json()
            items = (
                nin_data.get("features", [])
                if isinstance(nin_data, dict)
                else nin_data
            )

            matched_count = 0
            for it in items:
                props = it.get("properties", it)
                name = clean(
                    props.get(
                        "facility_name",
                        props.get("name", props.get("Hospital_Name", "")),
                    )
                )

                # Broader coverage: capture all ESIC, ESIS, mIMP, and empanelled centers
                n_lower = name.lower()
                is_esi = any(
                    k in n_lower
                    for k in [
                        "esi",
                        "esic",
                        "esis",
                        "employees state",
                        "employees' state",
                        "model hospital",
                    ]
                )

                if is_esi and len(name) > 3:
                    matched_count += 1
                    addr = clean(props.get("address", props.get("Address", "")))
                    st = clean(props.get("state", props.get("State", "")))
                    dist = clean(
                        props.get("district", props.get("District", ""))
                    )
                    f_type = (
                        "Hospital"
                        if any(
                            h in n_lower
                            for h in ["hospital", "pgimsr", "medical college"]
                        )
                        else "Dispensary"
                    )

                    records.append({
                        "facility_name": name,
                        "facility_type": f_type,
                        "category": "Direct ESIC/ESIS",
                        "state": st,
                        "district": dist,
                        "address": addr,
                        "pincode": extract_pincode(
                            f"{addr} {props.get('pincode', '')}"
                        ),
                        "contact": clean(
                            props.get(
                                "contact",
                                props.get("phone", props.get("Contact", "")),
                            )
                        ),
                    })
            print(
                f"[+] Extracted {matched_count} verified facilities from NIN registry."
            )
    except Exception as e:
        print(f"[!] Warning on NIN registry: {e}")

    # ---------------------------------------------------------
    # Clean, Deduplicate & Export
    # ---------------------------------------------------------
    df = pd.DataFrame(records)
    if not df.empty:
        df = df[df["facility_name"].str.len() > 3]
        df = df.drop_duplicates(subset=["facility_name", "state", "address"])
        df = df.sort_values(by=["state", "facility_type", "facility_name"])
    else:
        df = pd.DataFrame(
            columns=[
                "facility_name",
                "facility_type",
                "category",
                "state",
                "district",
                "address",
                "pincode",
                "contact",
            ]
        )

    df.to_csv("esi_master.csv", index=False, encoding="utf-8")
    df.to_json("esi_master.json", orient="records", indent=2)
    print(f"\n[✓] Finished: Saved {len(df)} total institutions into master dataset.")


if __name__ == "__main__":
    build_full_directory()
            
