"""Week 5 Extraction Pipeline v1.

Combined gazetteer (spaCy PhraseMatcher) + EntityRuler against Week 4 taxonomy.

Extracts:
  - OCCUPATIONS from demand posting `title` and `function_raw`
  - SKILLS from demand posting `description_raw` (no-op in v1: field is empty)
  - SKILL proxies from supply `programme` titles (flagged provenance=supply_programme)

Inputs: data/processed/week5_working_sample.csv  (produced by make_heldout_split.py)
Output: data/processed/week5_extractions_v1.csv
"""
from pathlib import Path

import pandas as pd
import spacy
import yaml
from spacy.matcher import PhraseMatcher

from load_taxonomy import load_taxonomy

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CFG = REPO_ROOT / "config" / "week5_pipeline.yaml"
WORKING_SAMPLE = REPO_ROOT / "data" / "processed" / "week5_working_sample.csv"
OUTPUT_PATH = REPO_ROOT / "data" / "processed" / "week5_extractions_v1.csv"

METHOD = "v1.0-gazetteer-spacy"

OUTPUT_COLS = [
    "posting_id", "source_evidence", "extracted_span", "predicted_type",
    "normalized_label", "taxonomy_id", "method_version", "review_status",
    "provenance",
]


def build_matcher(nlp, taxonomy):
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    for ctype, group in taxonomy.groupby("concept_type"):
        patterns = [nlp.make_doc(t) for t in group["term"].unique() if t]
        if patterns:
            matcher.add(ctype.upper(), patterns)
    return matcher


def extract_from_text(nlp, matcher, taxonomy, text, posting_id, field_name, provenance):
    if not text or not text.strip():
        return []
    doc = nlp(text)
    rows = []
    seen = set()
    for match_id, start, end in matcher(doc):
        span = doc[start:end]
        term = span.text.lower().strip()
        hits = taxonomy[taxonomy["term"] == term]
        if hits.empty:
            continue
        hit = hits.iloc[0]
        key = (posting_id, hit["concept_id"], span.text)
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "posting_id": posting_id,
            "source_evidence": f"{field_name}: {text}",
            "extracted_span": span.text,
            "predicted_type": hit["concept_type"],
            "normalized_label": hit["preferred_label"],
            "taxonomy_id": hit["concept_id"],
            "method_version": METHOD,
            "review_status": "unreviewed",
            "provenance": provenance,
        })
    return rows


def main(cfg_path=None):
    cfg_path = Path(cfg_path) if cfg_path else DEFAULT_CFG
    cfg = yaml.safe_load(open(cfg_path, encoding="utf-8"))

    if not WORKING_SAMPLE.exists():
        raise SystemExit(
            f"Missing {WORKING_SAMPLE}\n"
            "Run: python src/skillsgap/nlp/make_heldout_split.py  (once, from repo root)"
        )

    nlp = spacy.load(cfg["spacy"]["model"])
    taxonomy = load_taxonomy(cfg_path)
    matcher = build_matcher(nlp, taxonomy)

    df = pd.read_csv(WORKING_SAMPLE, dtype=str).fillna("")
    P = cfg["columns"]["postings"]

    all_rows = []
    for _, r in df.iterrows():
        pid = r[P["id"]]
        rtype = r[P["type"]]

        if rtype == "demand":
            all_rows += extract_from_text(
                nlp, matcher, taxonomy, r[P["title"]], pid, "title", "posting_title"
            )
            all_rows += extract_from_text(
                nlp, matcher, taxonomy, r[P["function"]], pid, "function_raw", "posting_function"
            )
            all_rows += extract_from_text(
                nlp, matcher, taxonomy, r[P["description"]], pid, "description_raw", "posting_body"
            )
        elif rtype == "supply":
            all_rows += extract_from_text(
                nlp, matcher, taxonomy, r[P["programme"]], pid, "programme", "supply_programme"
            )

    out = pd.DataFrame(all_rows, columns=OUTPUT_COLS).drop_duplicates(
        subset=["posting_id", "extracted_span", "taxonomy_id"]
    )
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_PATH, index=False)

    print(f"Wrote {len(out)} extraction cases -> {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    if len(out):
        print()
        print("By predicted_type / provenance:")
        print(out.groupby(["predicted_type", "provenance"]).size())
        print()
        print("Unique postings covered:", out["posting_id"].nunique(), "of", len(df))


if __name__ == "__main__":
    main()