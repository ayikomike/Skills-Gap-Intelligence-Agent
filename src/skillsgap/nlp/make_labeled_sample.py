"""Stratified sample of extraction cases for the 50+ manual review."""
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
EXTRACTIONS = REPO_ROOT / "data" / "processed" / "week5_extractions_v1.csv"
OUTPUT = REPO_ROOT / "TeamName_Week5_LabeledSample.csv"
TARGET = 60


def main():
    if not EXTRACTIONS.exists():
        raise SystemExit(
            f"Missing {EXTRACTIONS}\n"
            "Run: python src/skillsgap/nlp/extraction_pipeline.py  first."
        )
    df = pd.read_csv(EXTRACTIONS)
    if df.empty:
        raise SystemExit("Extraction file is empty. Check extraction_pipeline.py output.")
    df["review_status"] = "unreviewed"

    parts = []
    for _, grp in df.groupby(["predicted_type", "provenance"]):
        n = max(2, round(TARGET * len(grp) / len(df)))
        parts.append(grp.sample(min(n, len(grp)), random_state=42))

    sample = pd.concat(parts).drop_duplicates(
        subset=["posting_id", "extracted_span", "taxonomy_id"]
    ).head(TARGET)
    sample.to_csv(OUTPUT, index=False)

    print(f"Wrote {len(sample)} cases -> {OUTPUT.name}")
    if len(sample) < 50:
        print(f"WARNING: only {len(sample)} cases available (< 50 required).")
        print("Document this in docs/week5_limits.md and the ErrorAnalysis PDF.")
    print("Fill the review_status column. Allowed values:")
    print("  TP, FP, missed, incomplete, wrong_label, wrong_mapping, duplicate, ambiguous")


if __name__ == "__main__":
    main()