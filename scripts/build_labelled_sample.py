"""Draft 20-posting labelled reference sample (occupation-level). PRE-LABELS for the team to verify:
two reviewers must fill reviewer columns and resolve disagreements before Week 5 use.
Skills cannot be labelled: no posting descriptions were captured (see memo)."""
import csv
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
df = pd.read_csv(ROOT / "data/sample/TeamName_Week3_Dataset.csv")
MG = {1: "Managers", 2: "Professionals", 3: "Technicians & associate professionals", 4: "Clerical support workers",
      5: "Service & sales workers", 7: "Craft & related trades workers"}
# title: (occupation_normalised, ISCO-08 major group, confidence, function label agrees?, note)
L = {
 "Pharmaceutical and Medical Sales Representative": ("Technical & medical sales representative", 2, "medium", "yes", "ISCO 2433-type; could be 5 depending on role"),
 "Program Officer – Policy and Advocacy": ("Policy / programme officer", 2, "high", "partial", "function 'Product & Project Mgmt' is a poor fit; location 'Outside Uganda' for a Ugandan board is unexplained"),
 "Sales Manager": ("Sales manager", 1, "high", "yes", "location 'Outside Uganda'"),
 "Operations Manager": ("Operations manager", 1, "high", "yes", ""),
 "MIS Associate": ("Management information systems associate", 3, "low", "yes", "ICT-adjacent; 2 vs 3 needs the description"),
 "AC Technician": ("Air-conditioning / refrigeration technician", 7, "high", "no", "function 'Operations' is generic"),
 "Furniture Design/Production Supervisor": ("Manufacturing (furniture) supervisor", 3, "medium", "no", "listed under 'IT, Software & Data': source function label is wrong"),
 "Country Sales Manager – Uganda": ("Sales manager (country)", 1, "high", "yes", "posted by recruiter, not end employer"),
 "Cost and Management Accountant": ("Management accountant", 2, "high", "yes", ""),
 "Sales and Marketing Specialist": ("Sales & marketing professional", 2, "medium", "no", "function 'Estate Agents & Property Mgmt' contradicts title"),
 "Administration Supervisor (Hygiene & Facilities)": ("Facilities / administration supervisor", 3, "low", "partial", "hygiene/facilities may be elementary-work supervision (9)"),
 "Procurement Officer": ("Procurement officer / buyer", 3, "medium", "yes", "ISCO 3323"),
 "Telesales Representative – Kinyarwanda Speaking": ("Telephone sales representative", 5, "medium", "yes", "language requirement is a skill signal (Kinyarwanda)"),
 "Stock Controller": ("Stock / inventory clerk", 4, "medium", "yes", ""),
 "Stock/Inventory Manager": ("Inventory / supply-chain manager", 1, "medium", "yes", ""),
 "District Education Officer": ("Education manager (district government)", 1, "medium", "n/a", "public-sector grade U1E"),
 "Education Assistant II": ("Education assistant (district government)", 3, "low", "n/a", "post meaning is grade-specific; check civil-service scheme"),
 "Principal Internal Auditor": ("Internal auditor", 2, "high", "n/a", ""),
 "Senior Accountant": ("Accountant", 2, "high", "n/a", ""),
 "Assistant Law Enforcement Officer": ("Local-government law-enforcement officer", 5, "low", "n/a", "ISCO 5412-type vs 3 depends on duties"),
}
rows = []
for _, r in df[(df.record_type == "demand")].iterrows():
    if r.title not in L:
        continue
    occ, mg, conf, agree, note = L[r.title]
    rows.append({"record_id": r.record_id, "source": r.source, "title": r.title, "employer": r.employer,
                 "function_raw": r.function_raw, "occupation_normalised": occ, "isco08_major_group": mg,
                 "isco08_major_group_label": MG[mg], "label_confidence": conf, "source_function_agrees": agree,
                 "skills_labelled": "NOT POSSIBLE: description not captured", "label_status": "DRAFT pre-label: needs 2 human reviewers",
                 "reviewer_1": "", "reviewer_2": "", "notes": note})
out = ROOT / "data/sample/TeamName_Week3_LabelledSample.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(len(rows), "labelled")
