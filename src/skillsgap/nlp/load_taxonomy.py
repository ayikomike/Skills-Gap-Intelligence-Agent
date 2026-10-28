"""Load the Week 4 taxonomy into matcher-ready term records."""
from pathlib import Path

import pandas as pd
import yaml

# Anchor all relative paths to the repository root, regardless of CWD
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CFG = REPO_ROOT / "config" / "week5_pipeline.yaml"


def load_taxonomy(cfg_path=None):
    cfg_path = Path(cfg_path) if cfg_path else DEFAULT_CFG
    cfg = yaml.safe_load(open(cfg_path, encoding="utf-8"))
    tx = cfg["columns"]["taxonomy"]
    xlsx = Path(cfg["data"]["week4_taxonomy"])
    if not xlsx.is_absolute():
        xlsx = REPO_ROOT / xlsx
    df = pd.read_excel(xlsx, sheet_name=cfg["data"]["week4_sheet"])
    df = df.rename(columns={
        tx["id"]: "concept_id",
        tx["type"]: "concept_type",
        tx["label"]: "preferred_label",
        tx["aliases"]: "aliases",
        tx["parent"]: "parent_id",
        tx["version"]: "version",
    })
    records = []
    for _, r in df.iterrows():
        terms = [str(r["preferred_label"])]
        if isinstance(r["aliases"], str):
            terms += [a.strip() for a in r["aliases"].split(";") if a.strip()]
        for t in terms:
            records.append({
                "term": t.lower().strip(),
                "concept_id": r["concept_id"],
                "concept_type": r["concept_type"],
                "preferred_label": r["preferred_label"],
                "version": r["version"],
            })
    out = pd.DataFrame(records).drop_duplicates(subset=["term", "concept_id"])
    return out


if __name__ == "__main__":
    tx = load_taxonomy()
    print(f"Loaded {len(tx)} term records")
    print(tx.groupby("concept_type").size())