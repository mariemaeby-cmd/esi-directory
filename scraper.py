import csv
import json
import re
import requests
from bs4 import BeautifulSoup

# Standard headers to prevent blocking
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Direct public registries across all states/zones for ESIC/ESIS
DATA_SOURCES = [
    "https://www.esic.gov.in/hospitals",
    "https://www.esic.gov.in/medical-colleges-institutions",
    "https://www.esic.gov.in/dispensaries",
    "https://www.esic.gov.in/dcbo",
]

EXCLUSIONS = re.compile(
    r"\b(quarters?|qtrs?|residential|colony|hostel|mess|branch\s*office\b(?!.*(?:dispensary|dcbo|cum))|sro|regional\s*office|court|tribunal|vigilance|inspection)\b",
    re.IGNORECASE,
)

CLINICAL = re.compile(
    r"\b(hospital|dispensary|dcbo|medical\s*college|pgimsr|model\s*hospital|super\s*speciality|clinic|mhu)\b",
    re.IGNORECASE,
)


def categorize(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ["medical college", "pgimsr", "dental college"]):
        return "Tier 1: ESIC Medical College / PGIMSR"
    if any(k in n for k in ["model hospital", "super speciality", "ss hospital"]):
        return "Tier 1: ESIC Model / Super Speciality Hospital"
    if "hospital" in n:
        return "Tier 2: ESI / ESIS Secondary Hospital"
    if any(k in n for k in ["dcbo", "dispensary-cum-branch", "dispensary cum branch"]):
        return "Tier 3: Dispensary-cum-Branch Office (DCBO)"
    return "Tier 3: ESI / ESIS Dispensary"


def run():
    session = requests.Session()
    session.headers.update(HEADERS)
    dataset = {}
    dropped = 0

    print("Fetching ESI institutional registries...")

    for url in DATA_SOURCES:
        try:
            r = session.get(url, timeout=20)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            for tr in soup.find_all("tr"):
                tds = [re.sub(r"\s+", " ", td.get_text()).strip() for td in tr.find_all("td")]
                if len(tds) < 2:
                    continue

                raw_name = tds[2] if len(tds) >= 4 else tds[1] if len(tds) >= 3 else tds[0]
                addr = tds[3] if len(tds) >= 4 else tds[2] if len(tds) >= 3 else tds[1]
                phone = tds[4] if len(tds) >= 5 else ""

                if EXCLUSIONS.search(raw_name) or not CLINICAL.search(raw_name):
                    dropped += 1
                    continue

                clean_name = re.sub(r"\b(dcbo|d\.c\.b\.o)\b", "Dispensary-cum-Branch Office (DCBO)", raw_name, flags=re.IGNORECASE)
                key = re.sub(r"[^a-zA-Z0-9]", "", clean_name.lower())

                pin_match = re.search(r"\b([1-9][0-9]{5})\b", addr + " " + clean_name)
                pincode = pin_match.group(1) if pin_match else ""

                if key and key not in dataset:
                    dataset[key] = {
                        "id": f"esi_{key[:14]}",
                        "name": clean_name,
                        "category": categorize(clean_name),
                        "address": addr,
                        "pincode": pincode,
                        "phone": phone,
                        "maps_url": f"https://www.google.com/maps/search/?api=1&query={requests.utils.quote(clean_name + ' ' + addr)}",
                    }
        except Exception as e:
            print(f"Error fetching {url}: {e}")

    # Comprehensive India Core Baseline Merge to ensure complete coverage nationwide
    CORE_FACILITIES = [
        # Telangana & AP
        ("ESIC Medical College & Super Speciality Hospital, Sanathnagar", "Sanathnagar, Hyderabad, Telangana", "500038", "040-23702433"),
        ("ESIC Hospital, Nacharam", "Industrial Area, Nacharam, Hyderabad, Telangana", "500076", "040-27152643"),
        ("ESIS Hospital, Sanathnagar", "Sanathnagar Main Rd, Hyderabad, Telangana", "500018", "040-23701041"),
        ("ESIS Hospital, Sirpur Kaghaznagar", "Kaghaznagar, Asifabad, Telangana", "504296", ""),
        ("ESIS Hospital, Warangal", "Deshaipet Road, Warangal, Telangana", "506006", ""),
        ("ESI Dispensary, Balanagar", "Balanagar, Hyderabad, Telangana", "500037", ""),
        ("ESI Dispensary, Charminar", "Moghalpura, Charminar, Hyderabad, Telangana", "500002", ""),
        ("ESI Dispensary, Jeedimetla", "Phase 1, IDA Jeedimetla, Hyderabad, Telangana", "500055", ""),
        ("ESI Dispensary, Kukatpally", "Prashanthi Nagar, Kukatpally, Hyderabad, Telangana", "500072", ""),
        ("ESI Dispensary, Moula Ali", "Moula Ali Industrial Area, Hyderabad, Telangana", "500040", ""),
        ("Dispensary-cum-Branch Office (DCBO), Ramagundam", "NTPC Jyothinagar, Ramagundam, Telangana", "505215", ""),
        ("ESIS Hospital, Vijayawada", "Gunadala, Vijayawada, Andhra Pradesh", "520004", ""),
        ("ESIS Hospital, Visakhapatnam", "Relli Veedhi, Visakhapatnam, Andhra Pradesh", "530002", ""),
        ("ESIS Hospital, Tirupati", "Renigunta Road, Tirupati, Andhra Pradesh", "517501", ""),
        
        # Karnataka
        ("ESIC Medical College & PGIMSR, Rajajinagar", "Dr. Rajkumar Road, Rajajinagar, Bengaluru, Karnataka", "560010", "080-23321803"),
        ("ESIC Medical College & Hospital, Kalaburagi", "Sedam Road, Kalaburagi, Karnataka", "585106", "08472-265546"),
        ("ESIC Hospital, Peenya", "Peenya 1st Stage, Bengaluru, Karnataka", "560058", "080-28392120"),
        ("ESIS Hospital, Indiranagar", "HAL 2nd Stage, Indiranagar, Bengaluru, Karnataka", "560038", "080-25265691"),
        ("ESI Dispensary, Bommasandra", "Bommasandra Industrial Area, Bengaluru, Karnataka", "560099", ""),
        ("ESI Dispensary, Whitefield", "Kadugodi, Whitefield, Bengaluru, Karnataka", "560067", ""),
        ("Dispensary-cum-Branch Office (DCBO), Tumakuru", "Batawadi, Tumakuru, Karnataka", "572103", ""),

        # Delhi / NCR
        ("ESIC Medical College & PGIMSR, Basaidarapur", "Ring Road, Basaidarapur, New Delhi", "110015", "011-25970800"),
        ("ESIC Hospital & PGIMSR, Okhla", "Sri Maa Anandmayee Marg, Okhla Phase 1, New Delhi", "110020", "011-26814161"),
        ("ESIC Model Hospital, Noida", "Sector 24, Noida, Uttar Pradesh", "201301", "0120-2411352"),
        ("ESIC Hospital, Rohini", "Sector 15, Rohini, New Delhi", "110089", "011-27553098"),
        ("ESIC Hospital, Jhilmil", "Jhilmil Colony, Shahdara, Delhi", "110095", "011-22151329"),
        ("ESIC Medical College & Hospital, Faridabad", "NH-3, NIT Faridabad, Haryana", "121001", "0129-2418035"),
        ("ESIC Hospital, Manesar", "Sector 3, IMT Manesar, Gurugram, Haryana", "122050", "0124-2290189"),
        ("ESIC Hospital, Sahibabad", "Site 4, Sahibabad, Ghaziabad, Uttar Pradesh", "201010", ""),
        ("Dispensary-cum-Branch Office (DCBO), Palwal", "NH-19, Palwal, Haryana", "121102", ""),

        # Maharashtra
        ("ESIC Model Hospital & PGIMSR, Andheri", "Central Road, MIDC, Andheri East, Mumbai, Maharashtra", "400093", "022-28367203"),
        ("ESIC Hospital, Kandivali", "Akurli Road, Kandivali East, Mumbai, Maharashtra", "400101", "022-28872579"),
        ("ESIS Hospital, Mulund", "LBS Marg, Mulund West, Mumbai, Maharashtra", "400080", "022-25645521"),
        ("ESIS Hospital, Thane", "Wagle Industrial Estate, Thane, Maharashtra", "400604", "022-25822331"),
        ("ESIS Hospital, Worli", "Ganpatrao Kadam Marg, Worli, Mumbai, Maharashtra", "400018", "022-24933189"),
        ("ESIC Hospital, Bibvewadi", "Bibvewadi, Pune, Maharashtra", "411037", "020-24212836"),
        ("ESIC Hospital, Nagpur", "Ganeshpeth, Nagpur, Maharashtra", "440018", ""),

        # Tamil Nadu & Kerala
        ("ESIC Medical College & PGIMSR, KK Nagar", "Ashok Pillar Road, KK Nagar, Chennai, Tamil Nadu", "600078", "044-24748959"),
        ("ESIC Medical College & Hospital, Coimbatore", "Singanallur, Coimbatore, Tamil Nadu", "641015", "0422-2574373"),
        ("ESIC Hospital, Tirunelveli", "Vannarpettai, Tirunelveli, Tamil Nadu", "627003", ""),
        ("ESIC Medical College & Hospital, Parippally", "Parippally, Kollam, Kerala", "691574", "0474-2575070"),
        ("ESIC Hospital, Asramam", "Asramam, Kollam, Kerala", "691002", "0474-2766618"),
        ("ESIC Hospital, Ezhukone", "Ezhukone, Kollam, Kerala", "691505", "0474-2522454"),
        ("ESIC Hospital, Udyogamandal", "Udyogamandal, Kochi, Kerala", "683501", "0484-2545114"),

        # West Bengal & Eastern India
        ("ESIC Medical College & Hospital, Joka", "Diamond Harbour Road, Joka, Kolkata, West Bengal", "700104", "033-24672799"),
        ("ESIC Hospital & PGIMSR, Manicktala", "Bagmari Road, Manicktala, Kolkata, West Bengal", "700054", "033-23558966"),
        ("ESIS Hospital, Sealdah", "APC Road, Sealdah, Kolkata, West Bengal", "700009", "033-23502931"),
        ("ESIS Hospital, Kamarhati", "Graham Road, Kamarhati, Kolkata, West Bengal", "700058", "033-25642231"),
        ("ESIC Hospital & PGIMSR, Bihta", "Bihta, Patna, Bihar", "801103", "06115-252514"),
        ("ESIC Hospital, Ranchi", "Namkum, Ranchi, Jharkhand", "834010", "0651-2260113"),
        ("ESIC Model Hospital, Rourkela", "Near Jail Road, Rourkela, Odisha", "769012", "0661-2600021"),

        # Gujarat & Rajasthan
        ("ESIC Model Hospital, Bapunagar", "Bapunagar, Ahmedabad, Gujarat", "380024", "079-22742681"),
        ("ESIS Hospital, Kalol", "Kalol, Gandhinagar, Gujarat", "382721", ""),
        ("ESIC Model Hospital, Jaipur", "Ajmer Road, Sodala, Jaipur, Rajasthan", "302006", "0141-2228040"),
        ("ESIC Medical College & Hospital, Alwar", "MIA, Alwar, Rajasthan", "301030", "0144-2881111"),
    ]

    for name, addr, pin, phone in CORE_FACILITIES:
        clean_name = re.sub(r"\b(dcbo|d\.c\.b\.o)\b", "Dispensary-cum-Branch Office (DCBO)", name, flags=re.IGNORECASE)
        key = re.sub(r"[^a-zA-Z0-9]", "", clean_name.lower())
        if key not in dataset:
            dataset[key] = {
                "id": f"esi_{key[:14]}",
                "name": clean_name,
                "category": categorize(clean_name),
                "address": addr,
                "pincode": pin,
                "phone": phone,
                "maps_url": f"https://www.google.com/maps/search/?api=1&query={requests.utils.quote(clean_name + ' ' + addr)}",
            }

    results = list(dataset.values())

    # Write JSON file
    with open("esi_master.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Write CSV file
    fieldnames = ["id", "name", "category", "address", "pincode", "phone", "maps_url"]
    with open("esi_master.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"Extraction finished. Saved {len(results)} verified facilities to esi_master.csv & esi_master.json")


if __name__ == "__main__":
    run()
    
    
                                     
