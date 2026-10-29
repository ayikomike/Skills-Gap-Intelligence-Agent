"""Reserve the Week 8 held-out validation sample. RUN THIS FIRST."""
import hashlib
from pathlib import Path

import pandas as pd
import yaml


def main(cfg_path="config/week5_pipeline.yaml"):
    cfg = yaml.safe_load(open(cfg_path, encoding="utf-8"))
    df = pd.read_csv(cfg["data"]["week3_dataset"], dtype=str).fillna("")
    id_col = cfg["columns"]["postings"]["id"]
    df = df.sort_values(id_col).reset_index(drop=True)

    held_mask = df[id_col].apply(
        lambda x: int(hashlib.md5(x.encode()).hexdigest(), 16) % 5 == 0
    )
    held = df[held_mask].copy()
    train = df[~held_mask].copy()

    Path("data/processed").mkdir(parents=True, exist_ok=True)
    held.to_csv(cfg["heldout"]["output"], index=False)
    train.to_csv("data/processed/week5_working_sample.csv", index=False)

    sha = hashlib.sha256(Path(cfg["heldout"]["output"]).read_bytes()).hexdigest()
    Path("docs").mkdir(exist_ok=True)
    Path(cfg["heldout"]["checksum_log"]).write_text(
        "# Week 8 Held-Out Validation Sample\n\n"
        f"- Selection method: {cfg['heldout']['method']} on `{id_col}`\n"
        f"- Size: {len(held)} of {len(df)} records ({len(held) / len(df):.1%})\n"
        f"- Location: `{cfg['heldout']['output']}`\n"
        f"- SHA-256: `{sha}`\n"
        f"- Week 3 dataset version: {cfg['data']['week3_pipeline_version']}\n"
        f"- Week 4 taxonomy version: {cfg['data']['week4_version']}\n\n"
        "**Do not open, tune on, or report results from this file before Week 8.**\n",
        encoding="utf-8",
    )
    print(f"Held out {len(held)} of {len(df)} records.")
    print(f"SHA-256: {sha}")
    print(f"Working sample: {len(train)} records")


if __name__ == "__main__":
    main()