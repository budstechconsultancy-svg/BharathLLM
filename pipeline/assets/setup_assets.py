import os
import json
from pathlib import Path

# Healthcare
health_dirs = [
    "drugs", "nabh", "clinical_guidelines", "medical_coding", "cghs",
    "insurance", "cdsco", "schemes", "ayush", "medical_education"
]
for d in health_dirs:
    os.makedirs(f"c:/TNLLM/pipeline/assets/healthcare_corpus/{d}", exist_ok=True)

# Real Estate
re_dirs = [
    "rera", "land_records", "registration", "stamp_duty", "urban_planning",
    "property_tax", "builder_disputes", "agreements", "nri_property"
]
for d in re_dirs:
    os.makedirs(f"c:/TNLLM/pipeline/assets/realestate_corpus/{d}", exist_ok=True)

stamp_duty_matrix = {
    "TN": {
        "residential_sale": {
            "male_buyer": "7%",
            "female_buyer": "5%",
            "joint_female_first": "6%",
            "registration_fee": "4%",
            "maximum_registration_fee": None,
            "concessions": [{"type": "affordable_housing", "threshold": "₹50L", "rate": "4%"}]
        },
        "commercial_sale": {"rate": "7%", "registration_fee": "4%"},
        "rental_1_year": {"rate": "1% of total rent"},
        "gift_deed_family": {"rate": "1%"},
        "partition_deed": {"rate": "1% per share"},
        "power_of_attorney": {"rate": "₹100 to ₹500 fixed"}
    }
}
with open("c:/TNLLM/pipeline/assets/realestate_corpus/stamp_duty_matrix.json", "w", encoding="utf-8") as f:
    json.dump(stamp_duty_matrix, f, indent=4)

# HR
hr_dirs = [
    "labour_codes", "epf_esic", "minimum_wages", "posh", "gratuity_bonus",
    "factories_shops", "industrial_disputes", "contract_labour", "maternity",
    "child_labour", "old_labour_laws"
]
for d in hr_dirs:
    os.makedirs(f"c:/TNLLM/pipeline/assets/hr_corpus/{d}", exist_ok=True)

minimum_wages = {
    "TN": {
        "effective_from": "2024-04-01",
        "revision_frequency": "annual",
        "categories": {
            "unskilled": {"daily_rate": 450.0, "monthly_rate": 11700.0, "sectors": {"agriculture": {"daily": 400.0, "monthly": 10400.0}, "construction": {"daily": 500.0, "monthly": 13000.0}, "shops_commercial": {"daily": 450.0, "monthly": 11700.0}}},
            "semi_skilled": {"daily_rate": 500.0, "monthly_rate": 13000.0, "sectors": {}},
            "skilled": {"daily_rate": 600.0, "monthly_rate": 15600.0, "sectors": {}},
            "highly_skilled": {"daily_rate": 700.0, "monthly_rate": 18200.0, "sectors": {}}
        }
    }
}
with open("c:/TNLLM/pipeline/assets/hr_corpus/minimum_wages.json", "w", encoding="utf-8") as f:
    json.dump(minimum_wages, f, indent=4)

labour_code_map = {
    "Payment of Wages Act 1936": {"new_code": "Code on Wages 2019", "effective_date": "Pending notification"},
    "Industrial Disputes Act 1947": {"new_code": "Industrial Relations Code 2020", "effective_date": "Pending notification"},
    "EPF & MP Act 1952": {"new_code": "Code on Social Security 2020", "effective_date": "Pending notification"},
    "Factories Act 1948": {"new_code": "OSH Code 2020", "effective_date": "Pending notification"}
}
with open("c:/TNLLM/pipeline/assets/hr_corpus/labour_code_map.json", "w", encoding="utf-8") as f:
    json.dump(labour_code_map, f, indent=4)

print("Directories and JSON assets created.")
