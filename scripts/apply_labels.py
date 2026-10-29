"""Apply pre-suggested review labels to the Week 5 labeled sample."""
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "data" / "processed" / "week5_extractions_v1.csv"
OUT = REPO_ROOT / "TeamName_Week5_LabeledSample.csv"

# Pre-suggested labels, keyed by "posting_id|taxonomy_id|extracted_span"
PRE = {
    # --- Group A: supply programme -> domain (all FP) ---
    "IUIU 34th graduation (Kampala campus):22bb45023b33e248|DOM-11|Social Work": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    "IUIU 34th graduation (Kampala campus):22bb45023b33e248|DOM-06|Administration": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    "IUIU 34th graduation (Kampala campus):33e7de703656d2b9|DOM-06|Administration": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    "IUIU 34th graduation (Kampala campus):428cf064dec40ee2|DOM-06|Administration": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    "IUIU 34th graduation (Kampala campus):50e66454e9c0424d|DOM-06|Administration": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    "IUIU 34th graduation (Kampala campus):52a56a41dac0db6a|DOM-05|Education": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    "IUIU 34th graduation (Kampala campus):68cd185c45097de9|DOM-06|Administration": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    "IUIU 34th graduation (Kampala campus):6f4237b4167eacb9|DOM-02|Technology": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    "IUIU 34th graduation (Kampala campus):87e007991e09f45e|DOM-05|Education": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    "IUIU 34th graduation (Kampala campus):94081c9e5ff58f18|DOM-06|Administration": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    "UMI 22nd graduation 2025:233d69f1117c4d2b|DOM-06|Administration": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    "UMI 22nd graduation 2025:239829075638b536|DOM-05|Education": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    "UMI 22nd graduation 2025:239829075638b536|DOM-06|Administration": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    "UMI 22nd graduation 2025:27a391a5b207810a|DOM-06|Administration": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    "UMI 22nd graduation 2025:27a391a5b207810a|DOM-07|Governance": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    "UMI 22nd graduation 2025:4759fef9fd973114|DOM-06|Administration": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    "UMI 22nd graduation 2025:910a8b1dff0d1a3a|DOM-05|Education": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    "UMI 22nd graduation 2025:910a8b1dff0d1a3a|DOM-07|Governance": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    "UMI 22nd graduation 2025:9f68ac53ee2f7eac|DOM-05|Education": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    "UMI 22nd graduation 2025:9f68ac53ee2f7eac|DOM-06|Administration": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    "UMI 22nd graduation 2025:a0659c6a04ca5cde|DOM-06|Administration": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    "UMI 22nd graduation 2025:a5d43f009cbed26f|DOM-02|Technology": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    "UMI 22nd graduation 2025:a7bbe158757167ce|DOM-06|Administration": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    "UMI 22nd graduation 2025:ac7ef8c4a1449f7a|DOM-06|Administration": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    "UMI 22nd graduation 2025:b6b1d30e824df88b|DOM-06|Administration": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    "UMI 22nd graduation 2025:bb38f736f1eee49a|DOM-10|Logistics": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    "UMI 22nd graduation 2025:bb38f736f1eee49a|DOM-10|Transport": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    "UMI 22nd graduation 2025:bf23e458c2c04e62|DOM-06|Administration": ("FP", "Domain match on programme title; DOM is grouping not extraction target."),
    # --- Group B: supply programme -> skill ---
    "IUIU 34th graduation (Kampala campus):33e7de703656d2b9|SKL-053|Public Administration": ("TP", "Correct skill extraction from programme title."),
    "IUIU 34th graduation (Kampala campus):428cf064dec40ee2|SKL-053|Public Administration": ("TP", "Correct skill extraction from programme title."),
    "IUIU 34th graduation (Kampala campus):50e66454e9c0424d|SKL-053|Public Administration": ("TP", "Correct skill extraction from programme title."),
    "IUIU 34th graduation (Kampala campus):94081c9e5ff58f18|SKL-053|Public Administration": ("TP", "Correct skill extraction from programme title."),
    "UMI 22nd graduation 2025:233d69f1117c4d2b|SKL-053|Public Administration": ("TP", "Correct skill extraction from programme title."),
    "UMI 22nd graduation 2025:27a391a5b207810a|SKL-053|Public Administration": ("TP", "Correct skill extraction from programme title."),
    "UMI 22nd graduation 2025:ac7ef8c4a1449f7a|SKL-053|Public Administration": ("TP", "Correct skill extraction from programme title."),
    "UMI 22nd graduation 2025:bf23e458c2c04e62|SKL-053|Public Administration": ("TP", "Correct skill extraction from programme title."),
    "UMI 22nd graduation 2025:532557794783281d|SKL-045|Human Resource Management": ("TP", "Correct skill extraction from programme title."),
    "UMI 22nd graduation 2025:9f68ac53ee2f7eac|SKL-045|HR": ("TP", "Alias HR correctly mapped to Human resource management."),
    "UMI 22nd graduation 2025:5f81a5eb7457b5f2|SKL-030|Monitoring and Evaluation": ("TP", "Correct skill extraction from programme title."),
    "UMI 22nd graduation 2025:875ebb736ac0f563|SKL-031|Project Planning": ("incomplete", "Programme title is Project Planning and Management; span should be longer."),
    "UMI 22nd graduation 2025:a5d43f009cbed26f|SKL-020|Information Security": ("wrong_mapping", "Information Security is more specific than Cybersecurity fundamentals; taxonomy lacks exact concept."),
    # --- Group C: demand title -> occupation ---
    "brightermonday:1b6bd9658205bc01|OCC-33|Procurement Officer": ("TP", "Correct occupation extraction."),
    "brightermonday:1de899f29554c3ba|OCC-33|Sales Representative": ("TP", "Correct occupation extraction (title: Pharmaceutical and Medical Sales Representative)."),
    "brightermonday:569f45cce4b03c69|OCC-12|Operations Manager": ("TP", "Correct occupation extraction."),
    "brightermonday:56a4295b9c22eb8e|OCC-31|Technician": ("incomplete", "Title is AC Technician; span should include AC."),
    "district_adverts:3398bab368e4d2c0|OCC-24|Accountant": ("TP", "Correct occupation extraction (title: Senior Accountant)."),
    # --- Group D: demand function_raw -> skill/domain (all FP) ---
    "brightermonday:62fa8c111aad940b|SKL-031|Project Management": ("FP", "function_raw is Product & Project Management (job function, not skill)."),
    "brightermonday:77adff28a8fc77df|SKL-097|Business Development": ("FP", "function_raw is Management & Business Development (job function); Entrepreneurship is also a wrong concept."),
    "district_adverts:3398bab368e4d2c0|DOM-06|Finance": ("FP", "function_raw is Finance; DOM is grouping not extraction target."),
    "district_adverts:3ad6610252ce31f4|DOM-06|Administration": ("FP", "function_raw is Administration; DOM is grouping not extraction target."),
    # --- Group E: demand title -> domain (all FP) ---
    "brightermonday:6203967ce4f62f66|DOM-06|Administration": ("FP", "Title is Administration Supervisor (Hygiene & Facilities); DOM is grouping not extraction target."),
    "brightermonday:62fa8c111aad940b|DOM-07|Policy": ("FP", "Title is Program Officer - Policy and Advocacy; Policy alone is not an occupation. Also missed: Program Officer."),
    "district_adverts:c4fe913d90f02622|DOM-05|Education": ("FP", "Title is District Education Officer; DOM is grouping not extraction target."),
}


def main():
    if not SRC.exists():
        raise SystemExit(f"Missing {SRC}. Run extraction_pipeline.py first.")
    df = pd.read_csv(SRC, dtype=str).fillna("")
    df["review_status"] = "unreviewed"
    df["notes"] = ""

    unmatched = []
    for i, row in df.iterrows():
        key = f"{row['posting_id']}|{row['taxonomy_id']}|{row['extracted_span']}"
        if key in PRE:
            df.at[i, "review_status"] = PRE[key][0]
            df.at[i, "notes"] = PRE[key][1]
        else:
            unmatched.append(key)

    df.to_csv(OUT, index=False)
    print(f"Wrote {OUT.name} with {len(df)} rows")
    print()
    print("Review status counts:")
    print(df["review_status"].value_counts())
    print()
    if unmatched:
        print(f"WARNING: {len(unmatched)} rows had no pre-suggested label:")
        for u in unmatched:
            print(f"  - {u}")
    else:
        print("All rows received a pre-suggested label.")


if __name__ == "__main__":
    main()