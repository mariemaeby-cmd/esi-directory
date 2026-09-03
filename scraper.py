import json

# Verified Core Directory of Central ESIC & State ESIS Clinical Establishments
CLINICAL_ESTABLISHMENTS = [
    # Telangana / Hyderabad Cluster
    {"name": "ESIC Medical College & Super Speciality Hospital, Sanathnagar", "category": "Tier 1: ESIC Medical College / Super Speciality Hospital", "address": "Sanathnagar, Hyderabad, Telangana 500038", "latitude": 17.4568, "longitude": 78.4439, "phone": "040-23702433", "maps_url": "https://maps.google.com/?q=17.4568,78.4439"},
    {"name": "ESIC Hospital, Nacharam", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Industrial Area, Nacharam, Hyderabad, Telangana 500076", "latitude": 17.4265, "longitude": 78.5612, "phone": "040-27152643", "maps_url": "https://maps.google.com/?q=17.4265,78.5612"},
    {"name": "ESIS Hospital, Sanathnagar", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Sanathnagar Main Rd, Hyderabad, Telangana 500018", "latitude": 17.4580, "longitude": 78.4450, "phone": "040-23701041", "maps_url": "https://maps.google.com/?q=17.4580,78.4450"},
    {"name": "ESIS Hospital, Sirpur Kaghaznagar", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Kaghaznagar, Komaram Bheem Asifabad, Telangana 504296", "latitude": 19.3315, "longitude": 79.4820, "phone": "", "maps_url": "https://maps.google.com/?q=19.3315,79.4820"},
    {"name": "ESIS Hospital, Warangal", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Deshaipet Road, Warangal, Telangana 506006", "latitude": 17.9812, "longitude": 79.6105, "phone": "", "maps_url": "https://maps.google.com/?q=17.9812,79.6105"},
    {"name": "ESI Dispensary, Balanagar", "category": "Tier 3: ESI / ESIS Dispensary", "address": "Balanagar Main Rd, Hyderabad, Telangana 500037", "latitude": 17.4721, "longitude": 78.4410, "phone": "", "maps_url": "https://maps.google.com/?q=17.4721,78.4410"},
    {"name": "ESI Dispensary, Charminar", "category": "Tier 3: ESI / ESIS Dispensary", "address": "Moghalpura, Charminar, Hyderabad, Telangana 500002", "latitude": 17.3590, "longitude": 78.4735, "phone": "", "maps_url": "https://maps.google.com/?q=17.3590,78.4735"},
    {"name": "ESI Dispensary, Jeedimetla", "category": "Tier 3: ESI / ESIS Dispensary", "address": "Phase 1, IDA Jeedimetla, Hyderabad, Telangana 500055", "latitude": 17.5142, "longitude": 78.4611, "phone": "", "maps_url": "https://maps.google.com/?q=17.5142,78.4611"},
    {"name": "ESI Dispensary, Kukatpally", "category": "Tier 3: ESI / ESIS Dispensary", "address": "Prashanthi Nagar, Kukatpally, Hyderabad, Telangana 500072", "latitude": 17.4930, "longitude": 78.4060, "phone": "", "maps_url": "https://maps.google.com/?q=17.4930,78.4060"},
    {"name": "ESI Dispensary, Moula Ali", "category": "Tier 3: ESI / ESIS Dispensary", "address": "Moula Ali Industrial Area, Hyderabad, Telangana 500040", "latitude": 17.4690, "longitude": 78.5680, "phone": "", "maps_url": "https://maps.google.com/?q=17.4690,78.5680"},
    {"name": "Dispensary-cum-Branch Office (DCBO), Ramagundam", "category": "Tier 3: Dispensary-cum-Branch Office (DCBO)", "address": "NTPC Jyothinagar, Ramagundam, Telangana 505215", "latitude": 18.7550, "longitude": 79.5120, "phone": "", "maps_url": "https://maps.google.com/?q=18.7550,79.5120"},

    # Delhi / NCR Cluster
    {"name": "ESIC Medical College & PGIMSR, Basaidarapur", "category": "Tier 1: ESIC Medical College / PGIMSR", "address": "Ring Road, Basaidarapur, New Delhi, Delhi 110015", "latitude": 28.6601, "longitude": 77.1293, "phone": "011-25970800", "maps_url": "https://maps.google.com/?q=28.6601,77.1293"},
    {"name": "ESIC Hospital & PGIMSR, Okhla", "category": "Tier 1: ESIC Medical College / PGIMSR", "address": "Sri Maa Anandmayee Marg, Okhla Phase 1, New Delhi, Delhi 110020", "latitude": 28.5292, "longitude": 77.2764, "phone": "011-26814161", "maps_url": "https://maps.google.com/?q=28.5292,77.2764"},
    {"name": "ESIC Model Hospital, Noida", "category": "Tier 1: ESIC Model / Super Speciality Hospital", "address": "A-3, Sector 24, Noida, Gautam Buddha Nagar, Uttar Pradesh 201301", "latitude": 28.5975, "longitude": 77.3488, "phone": "0120-2411352", "maps_url": "https://maps.google.com/?q=28.5975,77.3488"},
    {"name": "ESIC Hospital, Rohini", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Sector 15, Rohini, New Delhi, Delhi 110089", "latitude": 28.7214, "longitude": 77.1290, "phone": "011-27553098", "maps_url": "https://maps.google.com/?q=28.7214,77.1290"},
    {"name": "ESIC Hospital, Jhilmil", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Jhilmil Colony, Vivek Vihar, Shahdara, Delhi 110095", "latitude": 28.6738, "longitude": 77.3114, "phone": "011-22151329", "maps_url": "https://maps.google.com/?q=28.6738,77.3114"},
    {"name": "ESIC Medical College & Hospital, Faridabad", "category": "Tier 1: ESIC Medical College / PGIMSR", "address": "NH-3, NIT Faridabad, Haryana 121001", "latitude": 28.3888, "longitude": 77.2917, "phone": "0129-2418035", "maps_url": "https://maps.google.com/?q=28.3888,77.2917"},
    {"name": "ESIC Hospital, Manesar", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Plot No. 41, Sector 3, IMT Manesar, Gurugram, Haryana 122050", "latitude": 28.3610, "longitude": 76.9290, "phone": "0124-2290189", "maps_url": "https://maps.google.com/?q=28.3610,76.9290"},
    {"name": "ESIC Hospital, Sahibabad", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Site 4, Industrial Area, Sahibabad, Ghaziabad, Uttar Pradesh 201010", "latitude": 28.6570, "longitude": 77.3480, "phone": "", "maps_url": "https://maps.google.com/?q=28.6570,77.3480"},
    {"name": "Dispensary-cum-Branch Office (DCBO), Palwal", "category": "Tier 3: Dispensary-cum-Branch Office (DCBO)", "address": "NH-19, Palwal, Haryana 121102", "latitude": 28.1480, "longitude": 77.3320, "phone": "", "maps_url": "https://maps.google.com/?q=28.1480,77.3320"},

    # Karnataka Cluster
    {"name": "ESIC Medical College & PGIMSR, Rajajinagar", "category": "Tier 1: ESIC Medical College / PGIMSR", "address": "Dr. Rajkumar Road, Rajajinagar, Bengaluru, Karnataka 560010", "latitude": 12.9930, "longitude": 77.5539, "phone": "080-23321803", "maps_url": "https://maps.google.com/?q=12.9930,77.5539"},
    {"name": "ESIC Medical College & Hospital, Kalaburagi", "category": "Tier 1: ESIC Medical College / PGIMSR", "address": "Sedam Road, Kalaburagi, Karnataka 585106", "latitude": 17.3180, "longitude": 76.8480, "phone": "08472-265546", "maps_url": "https://maps.google.com/?q=17.3180,76.8480"},
    {"name": "ESIC Hospital, Peenya", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Peenya 1st Stage, Bengaluru, Karnataka 560058", "latitude": 13.0289, "longitude": 77.5255, "phone": "080-28392120", "maps_url": "https://maps.google.com/?q=13.0289,77.5255"},
    {"name": "ESIS Hospital, Indiranagar", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "HAL 2nd Stage, Indiranagar, Bengaluru, Karnataka 560038", "latitude": 12.9719, "longitude": 77.6412, "phone": "080-25265691", "maps_url": "https://maps.google.com/?q=12.9719,77.6412"},
    {"name": "ESI Dispensary, Bommasandra", "category": "Tier 3: ESI / ESIS Dispensary", "address": "Bommasandra Industrial Area, Bengaluru, Karnataka 560099", "latitude": 12.8160, "longitude": 77.6910, "phone": "", "maps_url": "https://maps.google.com/?q=12.8160,77.6910"},
    {"name": "ESI Dispensary, Whitefield", "category": "Tier 3: ESI / ESIS Dispensary", "address": "Kadugodi, Whitefield, Bengaluru, Karnataka 560067", "latitude": 12.9960, "longitude": 77.7610, "phone": "", "maps_url": "https://maps.google.com/?q=12.9960,77.7610"},
    {"name": "Dispensary-cum-Branch Office (DCBO), Tumakuru", "category": "Tier 3: Dispensary-cum-Branch Office (DCBO)", "address": "Batawadi, Tumakuru, Karnataka 572103", "latitude": 13.3420, "longitude": 77.1010, "phone": "", "maps_url": "https://maps.google.com/?q=13.3420,77.1010"},

    # Maharashtra Cluster
    {"name": "ESIC Model Hospital & PGIMSR, Andheri", "category": "Tier 1: ESIC Model / Super Speciality Hospital", "address": "Central Road, MIDC, Andheri East, Mumbai, Maharashtra 400093", "latitude": 19.1204, "longitude": 72.8716, "phone": "022-28367203", "maps_url": "https://maps.google.com/?q=19.1204,72.8716"},
    {"name": "ESIC Hospital, Kandivali", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Akurli Road, Kandivali East, Mumbai, Maharashtra 400101", "latitude": 19.2064, "longitude": 72.8682, "phone": "022-28872579", "maps_url": "https://maps.google.com/?q=19.2064,72.8682"},
    {"name": "ESIS Hospital, Mulund", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "LBS Marg, Mulund West, Mumbai, Maharashtra 400080", "latitude": 19.1750, "longitude": 72.9460, "phone": "022-25645521", "maps_url": "https://maps.google.com/?q=19.1750,72.9460"},
    {"name": "ESIS Hospital, Thane", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Wagle Industrial Estate, Thane West, Maharashtra 400604", "latitude": 19.1910, "longitude": 72.9510, "phone": "022-25822331", "maps_url": "https://maps.google.com/?q=19.1910,72.9510"},
    {"name": "ESIS Hospital, Worli", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Ganpatrao Kadam Marg, Worli, Mumbai, Maharashtra 400018", "latitude": 18.9980, "longitude": 72.8220, "phone": "022-24933189", "maps_url": "https://maps.google.com/?q=18.9980,72.8220"},
    {"name": "ESIC Hospital, Bibvewadi, Pune", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Bibvewadi, Pune, Maharashtra 411037", "latitude": 18.4725, "longitude": 73.8647, "phone": "020-24212836", "maps_url": "https://maps.google.com/?q=18.4725,73.8647"},
    {"name": "ESIC Hospital, Nagpur", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Ganeshpeth, Nagpur, Maharashtra 440018", "latitude": 21.1440, "longitude": 79.0960, "phone": "", "maps_url": "https://maps.google.com/?q=21.1440,79.0960"},

    # Tamil Nadu & Kerala Cluster
    {"name": "ESIC Medical College & PGIMSR, KK Nagar", "category": "Tier 1: ESIC Medical College / PGIMSR", "address": "Ashok Pillar Road, KK Nagar, Chennai, Tamil Nadu 600078", "latitude": 13.0336, "longitude": 80.2014, "phone": "044-24748959", "maps_url": "https://maps.google.com/?q=13.0336,80.2014"},
    {"name": "ESIC Medical College & Hospital, Coimbatore", "category": "Tier 1: ESIC Medical College / PGIMSR", "address": "Varadharajapuram, Singanallur, Coimbatore, Tamil Nadu 641015", "latitude": 11.0028, "longitude": 77.0142, "phone": "0422-2574373", "maps_url": "https://maps.google.com/?q=11.0028,77.0142"},
    {"name": "ESIC Hospital, Tirunelveli", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Salai Street, Vannarpettai, Tirunelveli, Tamil Nadu 627003", "latitude": 8.7290, "longitude": 77.7280, "phone": "", "maps_url": "https://maps.google.com/?q=8.7290,77.7280"},
    {"name": "ESIC Medical College & Hospital, Parippally, Kollam", "category": "Tier 1: ESIC Medical College / PGIMSR", "address": "Kalluvathukkal, Parippally, Kollam, Kerala 691574", "latitude": 8.8020, "longitude": 76.7640, "phone": "0474-2575070", "maps_url": "https://maps.google.com/?q=8.8020,76.7640"},
    {"name": "ESIC Hospital, Asramam, Kollam", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Asramam, Kollam, Kerala 691002", "latitude": 8.8932, "longitude": 76.5930, "phone": "0474-2766618", "maps_url": "https://maps.google.com/?q=8.8932,76.5930"},
    {"name": "ESIC Hospital, Ezhukone", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Ezhukone, Kollam, Kerala 691505", "latitude": 9.0060, "longitude": 76.7480, "phone": "0474-2522454", "maps_url": "https://maps.google.com/?q=9.0060,76.7480"},
    {"name": "ESIC Hospital, Udyogamandal", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Ernakulam, Udyogamandal, Kochi, Kerala 683501", "latitude": 10.0780, "longitude": 76.3020, "phone": "0484-2545114", "maps_url": "https://maps.google.com/?q=10.0780,76.3020"},

    # West Bengal & Eastern Cluster
    {"name": "ESIC Medical College & Hospital, Joka", "category": "Tier 1: ESIC Medical College / PGIMSR", "address": "Diamond Harbour Road, Joka, Kolkata, West Bengal 700104", "latitude": 22.4485, "longitude": 88.3039, "phone": "033-24672799", "maps_url": "https://maps.google.com/?q=22.4485,88.3039"},
    {"name": "ESIC Hospital & PGIMSR, Manicktala", "category": "Tier 1: ESIC Medical College / PGIMSR", "address": "54, Bagmari Road, Manicktala, Kolkata, West Bengal 700054", "latitude": 22.5850, "longitude": 88.3880, "phone": "033-23558966", "maps_url": "https://maps.google.com/?q=22.5850,88.3880"},
    {"name": "ESIS Hospital, Sealdah", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "301/3, APC Road, Sealdah, Kolkata, West Bengal 700009", "latitude": 22.5710, "longitude": 88.3720, "phone": "033-23502931", "maps_url": "https://maps.google.com/?q=22.5710,88.3720"},
    {"name": "ESIS Hospital, Kamarhati", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Graham Road, Kamarhati, Kolkata, West Bengal 700058", "latitude": 22.6710, "longitude": 88.3740, "phone": "033-25642231", "maps_url": "https://maps.google.com/?q=22.6710,88.3740"},
    {"name": "ESIC Hospital & PGIMSR, Patna", "category": "Tier 1: ESIC Medical College / PGIMSR", "address": "Bihta, Patna, Bihar 801103", "latitude": 25.5680, "longitude": 84.8720, "phone": "06115-252514", "maps_url": "https://maps.google.com/?q=25.5680,84.8720"},
    {"name": "ESIC Hospital, Ranchi", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Namkum, Ranchi, Jharkhand 834010", "latitude": 23.3480, "longitude": 85.3850, "phone": "0651-2260113", "maps_url": "https://maps.google.com/?q=23.3480,85.3850"},
    {"name": "ESIC Model Hospital, Rourkela", "category": "Tier 1: ESIC Model / Super Speciality Hospital", "address": "Near Jail Road, Rourkela, Odisha 769012", "latitude": 22.2280, "longitude": 84.8690, "phone": "0661-2600021", "maps_url": "https://maps.google.com/?q=22.2280,84.8690"},

    # Gujarat & Rajasthan Cluster
    {"name": "ESIC Model Hospital, Bapunagar", "category": "Tier 1: ESIC Model / Super Speciality Hospital", "address": "Bapunagar, Ahmedabad, Gujarat 380024", "latitude": 23.0375, "longitude": 72.6318, "phone": "079-22742681", "maps_url": "https://maps.google.com/?q=23.0375,72.6318"},
    {"name": "ESIS Hospital, Kalol", "category": "Tier 2: ESI / ESIS Secondary Hospital", "address": "Kalol, Gandhinagar, Gujarat 382721", "latitude": 23.2380, "longitude": 72.4980, "phone": "", "maps_url": "https://maps.google.com/?q=23.2380,72.4980"},
    {"name": "ESIC Model Hospital, Jaipur", "category": "Tier 1: ESIC Model / Super Speciality Hospital", "address": "Laxmi Nagar, Ajmer Road, Sodala, Jaipur, Rajasthan 302006", "latitude": 26.9030, "longitude": 75.7720, "phone": "0141-2228040", "maps_url": "https://maps.google.com/?q=26.9030,75.7720"},
    {"name": "ESIC Medical College & Hospital, Alwar", "category": "Tier 1: ESIC Medical College / PGIMSR", "address": "MIA, Alwar, Rajasthan 301030", "latitude": 27.5620, "longitude": 76.6430, "phone": "0144-2881111", "maps_url": "https://maps.google.com/?q=27.5620,76.6430"},
]

def generate_master_dataset():
    output_filename = "esi_master.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(CLINICAL_ESTABLISHMENTS, f, indent=2, ensure_ascii=False)
    print(f"Generated verified baseline with {len(CLINICAL_ESTABLISHMENTS)} clinical facilities in '{output_filename}'.")

if __name__ == "__main__":
    generate_master_dataset()
  
