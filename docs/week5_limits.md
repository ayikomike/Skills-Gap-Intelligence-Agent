# Week 5 Extraction Pipeline v1 — Limits

**Method:** `v1.0-gazetteer-spacy` (spaCy `PhraseMatcher` over Week 4 taxonomy aliases)
**Date:** 2026-10-28

## What v1 CAN support

- **Occupation extraction from demand posting titles**, where the title contains an alias already present in the Week 4 taxonomy (`OCC-*`). In the 15-review-case sample, 5 occupation extractions were produced, of which 4 were correct and 1 was an incomplete span.
- **Skill extraction from supply programme titles** (`programme` field), where the programme title contains a skill alias (`SKL-*`). In the current sample, 13 skill extractions were produced, of which 12 were correct and 1 was a wrong mapping.
- **Stable taxonomy mapping with provenance**, so any downstream reviewer can trace an extraction back to its source field, source text, and taxonomy concept.
- **Reproducible output** — same taxonomy + same postings → identical CSV, byte for byte, minus the dedup ordering. The method version is stored in every row.

## What v1 CANNOT support

1. **Skill extraction from demand posting bodies.** `description_raw` is empty for all 15 demand records in the Week 3 dataset (`pipeline_version 0.1.0`). The pipeline's `description_raw` branch is wired and correct but never fires on this data. Any claim that v1 extracts *employer-required skills* from postings would be false. v1 extracts skills from **supply programme titles**, which is a different signal.

2. **Recall beyond taxonomy aliases.** The gazetteer can only match strings that appear as preferred labels or aliases in `WEEK 4 SKILLS AND OCCUPATION TAXONOMY.xlsx`. Observed misses include "Program Officer", "MIS Associate", "Stock Controller", "Marketing Officer", "District Education Officer", "Education Assistant II", "Principal Internal Auditor", "Cost and Management Accountant", and "Assistant Law Enforcement Officer". Each of these is a Ugandan labour-market term that the taxonomy does not cover.

3. **Language coverage.** The gazetteer is English-only. Luganda, Runyankole, Swahili, and English–Luganda code-switched text in postings will not be matched unless the taxonomy carries those aliases (it does not, as of v0.1).

4. **Informal-sector coverage.** `DOM-13 Informal economy and microenterprise` exists in the taxonomy, but **no posting in the Week 3 dataset evidences the informal sector**. Online job postings systematically under-represent informal work in Uganda. v1 cannot say anything about informal skills demand, and the Week 6 gap analysis must state this explicitly.

5. **Source coverage.** 15 demand postings from 2 sources (`brightermonday`, `district_adverts`), 44 supply rows from 2 institutions (UMI, IUIU). This is a small convenience sample, not a representative survey. Any quantitative claim must be scoped to "the Week 3 sample" not "the Ugandan labour market".

6. **Taxonomy stability.** Week 4 taxonomy is `version 0.1`, `review_status = provisional`. Concept boundaries (e.g., `OCC-33` vs `OCC-LOG-01` for stock roles; `SKL-020` for information security) may change in later review. Mappings that are correct under v0.1 may become `wrong_mapping` under a future taxonomy version; v1 does not detect this drift.

7. **Domain over-matching.** The gazetteer emits `predicted_type=domain` matches because single-word aliases like "Administration" and "Education" are present in the taxonomy. Domains are groupings, not extraction targets. v1 output therefore contains 32 domain FPs in the 53-case sample (66.0% FP rate). This is documented in `docs/week5_error_analysis_draft.md` and is the #1 v2 correction.

## Consequences for Week 6 (gap analysis)

The gap analysis must be scoped to:

- **Occupation demand signal:** the 5 reviewed occupation extractions from posting titles. Quantitative analysis at the concept level (`OCC-33`, `OCC-12`, `OCC-31`, `OCC-24`) is valid for these postings only.
- **Skill supply signal:** the 12 reviewed skill extractions from programme titles. Any comparison against demand-skill signals cannot be made in v1 because there is no demand-skill signal.
- **Domain matches:** should not be used as a demand or supply signal. They describe which domains the taxonomy has coverage for, not what employers or graduates actually do.

## Ethical and provenance notes

- No personal applicant information is present in the source data. No PII is processed.
- No credentials or API keys are used by the pipeline.
- Collection is ToS-compliant per the Week 3 ETL (`retrieval_method=manual_fetch_tool_capture`, `source_url` retained per row).
- Outputs are policy decision support, not automated decisions, consistent with the project's ethical boundaries in `README.md`.