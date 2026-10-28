# Week 5 — Extraction Pipeline v1

Combined gazetteer (spaCy PhraseMatcher) + EntityRuler matched against the Week 4 skills and occupation taxonomy.

## Setup

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install --upgrade pip
    pip install pandas spacy pyyaml openpyxl
    python -m spacy download en_core_web_sm

## Run order (strict)

1. `python src\skillsgap\nlp\make_heldout_split.py` — already run once on 2026-10-28. Do not re-run.
2. `python src\skillsgap\nlp\extraction_pipeline.py`
3. `python src\skillsgap\nlp\make_labeled_sample.py`
4. `python scripts\apply_labels.py`

## Entry point

`src\skillsgap\nlp\extraction_pipeline.py::main`

## Outputs

- `data\processed\week5_extractions_v1.csv` — all extraction cases
- `Week5_LabeledSample.csv` — 53-case manual review sample
- `Week5_ErrorAnalysis.pdf` — error analysis
- `data\processed\week8_validation_sample.csv` — DO NOT OPEN until Week 8
- `docs\week5_heldout.md` — held-out split method + SHA-256
- `docs\week5_limits.md` — what v1 can and cannot support

## Versions used

- Week 3 dataset: `data\sample\TeamName_Week3_Dataset.csv`, pipeline_version 0.1.0
- Week 4 taxonomy: `data\raw\taxonomy\WEEK 4 SKILLS AND OCCUPATION TAXONOMY.xlsx`, version 0.1
- spaCy model: `en_core_web_sm` 3.8.0
- Method: `v1.0-gazetteer-spacy`