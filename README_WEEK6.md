# Week 6 — Supply-Demand Gap-Analysis Engine

Joins the Week 3 demand and supply records on Week 4 taxonomy domains and computes, per domain,
the gap between its share of demand and its share of supply.

## Setup

    pip install pandas numpy pyyaml openpyxl matplotlib reportlab pytest

## Run order (from the repository root)

1. `python src\skillsgap\gap\engine.py` — runs the analysis, writes `data\processed\week6\`
2. `python src\skillsgap\gap\export_xlsx.py` — writes `reports\week6\TeamName_Week6_Analysis.xlsx`
3. `python src\skillsgap\gap\report_pdf.py` — writes `reports\week6\TeamName_Week6_Methodology.pdf`
4. `python -m pytest tests\test_gap_engine.py` — 5 tests, including a reproducibility check

The taxonomy is read from `data\raw\taxonomy\` if unpacked, otherwise straight from the Week 4 zip.
The Week 8 held-out file is never read.

## Metric

    D_c = postings mapped to category c / all mapped in-scope postings
    S_c = graduates mapped to category c / all mapped graduates
    G_c = 100 * (D_c - S_c)      percentage points (primary)
    R_c = D_c / S_c              secondary, blank when S_c = 0

A record mapping to k categories counts 1/k in each. Categories with fewer than 3 postings or
30 graduates are LOW SUPPORT.

## Configuration (edit these, not the code)

| File | What it controls |
|---|---|
| `config\week6\gap_engine.yaml` | input files, scope rules, support thresholds, bootstrap, NDPIV ratios |
| `config\week6\mapping_rules.csv` | title/programme patterns -> taxonomy domain, priority, certainty, rationale |
| `config\week6\categories.csv` | STEM group and NDPIV 9274 ICT flag per domain |
| `config\week6\concept_to_category.csv` | Week 5 concept IDs -> domain, for the cross-check |

## Outputs (`data\processed\week6\`)

| File | Content |
|---|---|
| `joined_records.csv` | one row per record x category, with weights, rules fired, certainty and full lineage |
| `category_results.csv` | D, S, G, R, 90% bootstrap interval, support, contributing record IDs |
| `coverage.csv` | records in, excluded, out of scope, unmapped, uncertain, split |
| `stem_ratio.csv` | NDPIV 441(ii) STEM:humanities variants |
| `sensitivity.csv` | gap under 7 alternative choices |
| `unmatched_uncertain_excluded.csv` | every record that needs review |
| `run_manifest.json` | SHA-256 of every input and output, plus versions |

## Versions used for the submitted result

- Records: `data\processed\week5_working_sample.csv` (Week 3 v0.1.0, working split)
- Taxonomy: Week 4 v0.1, provisional
- Extraction: `data\processed\week5_extractions_v1.csv`, `v1.0-gazetteer-spacy`
- Engine: `w6-gap-0.1.0`
