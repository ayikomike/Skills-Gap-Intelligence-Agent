# Week 5 Error Analysis — Extraction Pipeline v1

**Team:** Ayiko Mike (Data & Infrastructure), Aseki Ali (NLP/ML), Andema Agusto (Product, Policy & Evaluation)
**Date:** 2026-10-28
**Method version:** `v1.0-gazetteer-spacy`
**Week 3 dataset:** `TeamName_Week3_Dataset.csv`, pipeline_version `0.1.0`
**Week 4 taxonomy:** `WEEK 4 SKILLS AND OCCUPATION TAXONOMY.xlsx`, version `0.1`

## Method

- **Review unit:** one extraction case (one span in one record). A posting that yields two spans is reviewed twice, matching the assignment's "posting identifier, source evidence, extracted span, predicted type, normalized label, taxonomy identifier" schema.
- **Sample:** 53 extraction cases, produced by `v1.0-gazetteer-spacy` on the 59-record working sample (after the 17-record Week 8 held-out split). Domain-level matches (`DOM-*`) were retained in the review even though they are taxonomic groupings rather than extraction targets, so that the over-match behaviour is visible and quantified.
- **Reviewer:** Aseki Ali (NLP/ML Lead), reviewed 2026-10-28.
- **Labels:** `TP`, `FP`, `missed`, `incomplete`, `wrong_label`, `wrong_mapping`, `duplicate`, `ambiguous`.
- **Provenance breakdown of the sample:**
  - supply programme → domain: 28
  - supply programme → skill: 13
  - demand title → occupation: 5
  - demand title → domain: 3
  - demand function → domain: 2
  - demand function → skill: 2

## Counts

| Category | Count | % of 53 |
|---|---|---|
| TP | 15 | 28.3% |
| FP | 35 | 66.0% |
| incomplete | 2 | 3.8% |
| wrong_mapping | 1 | 1.9% |
| missed | n/a | reported separately below |
| wrong_label | 0 | 0.0% |
| duplicate | 0 | 0.0% |
| ambiguous | 0 | 0.0% |

**Precision on reviewed cases:** 15 / 53 = **28.3%**.

## Most common false positives

1. **Domain terms matched as if they were skills or occupations (32 of 35 FPs).** The gazetteer includes single common words as `DOM-*` aliases — "Administration", "Education", "Finance", "Technology", "Policy", "Governance", "Logistics", "Transport", "Social Work". Because these words appear in almost every programme title and several posting titles, they fire far more often than meaningful occupation or skill extractions.

   - Example: `IUIU 34th graduation (Kampala campus):68cd185c45097de9` — programme *"Master of Business Administration"* → extracted `Administration → DOM-06 Business, finance and administration`. This is a grouping, not an extraction target.
   - Example: `brightermonday:6203967ce4f62f66` — title *"Administration Supervisor (Hygiene & Facilities)"* → extracted `Administration → DOM-06`. The occupation should be a supervisor role, not a domain.
   - Example: `district_adverts:c4fe913d90f02622` — title *"District Education Officer"* → extracted `Education → DOM-05 Education and human capital`. Should map to a teaching or public-administration occupation.

2. **Job-function labels extracted as skills (2 FPs).** `function_raw` is a category label from the source site, not a skill statement.

   - `brightermonday:62fa8c111aad940b` — `function_raw` = *"Product & Project Management"* → extracted `Project Management → SKL-031`. The field is a category, not evidence of the skill being required.
   - `brightermonday:77adff28a8fc77df` — `function_raw` = *"Management & Business Development"* → extracted `Business Development → SKL-097 Entrepreneurship`. Both the source field and the taxonomy mapping are wrong here.

3. **Single-word span extraction from longer titles (2 incomplete).**

   - `brightermonday:56a4295b9c22eb8e` — title *"AC Technician"* → extracted `Technician → OCC-31` (span should be "AC Technician").
   - `UMI 22nd graduation 2025:875ebb736ac0f563` — programme *"PGD in Project Planning and Management"* → extracted `Project Planning → SKL-031` (span should be "Project Planning and Management").

4. **One arguable mapping.**

   - `UMI 22nd graduation 2025:a5d43f009cbed26f` — programme *"PGD in Information Security Management / PGD in Information Technology"* → extracted `Information Security → SKL-020 Cybersecurity fundamentals`. The taxonomy lacks a dedicated "Information Security" skill concept; `SKL-020` is adjacent but not exact. Marked `wrong_mapping` to flag the taxonomy gap rather than the pipeline behaviour.

## Most common missed / incomplete extractions

The following **missed** occupation terms were observed across the 15 demand postings during review. They are documented separately from the 53-case count because "missed" cases cannot appear as rows in the extraction output — they are absences.

1. **Program Officer** — `brightermonday:62fa8c111aad940b`, title *"Program Officer – Policy and Advocacy"*. No taxonomy concept covers "Program Officer"; the closest is `OCC-33 Business and administration associate professionals`, which is too broad.
2. **MIS Associate** — `brightermonday:d38a3d95a5fb86c2`, title *"MIS Associate"*. Not matched. Closest concept: `OCC-ICT-01 Data and analytics occupations`, but the literal string "MIS Associate" is not an alias.
3. **Stock Controller / Stock/Inventory Manager** — `brightermonday:f631066f36aa6cfd` and `brightermonday:e0b06d46fb390658`. Both plausibly map to `OCC-33` or `OCC-LOG-01`, but neither string appears as an alias.
4. **Marketing Officer** — `brightermonday:66c9273abdbeda8e`. Not matched to `OCC-33` despite being a sales/marketing role.
5. **District Education Officer, Education Assistant II** — `district_adverts:c4fe913d90f02622`, `district_adverts:7bf48083f770f86c`. Public-sector teaching/administration roles; `OCC-23 Teaching professionals` does not list these Ugandan civil-service titles as aliases.
6. **Principal Internal Auditor, Senior Accountant, Cost and Management Accountant** — `district_adverts:eccce28b5af35f47`, `district_adverts:3398bab368e4d2c0`, `brightermonday:3ef2e4d09d6bc0fb`. Only "Accountant" matched (where present in title); "Internal Auditor" and "Cost and Management Accountant" are not aliases under `OCC-24`.
7. **Assistant Law Enforcement Officer** — `district_adverts:3ad6610252ce31f4`. No matching taxonomy concept; `OCC-26 Legal, social and cultural professionals` does not cover law enforcement.
8. **No skill extractions from posting bodies** — `description_raw` is empty for all 15 demand records in Week 3 (`pipeline_version 0.1.0`). Skills were extracted only from supply `programme` titles. This is the single largest limitation of v1 and is reported in `docs/week5_limits.md`.

## Wrong labels and wrong mappings

- **wrong_label:** 0 cases.
- **wrong_mapping:** 1 case — `Information Security → SKL-020 Cybersecurity fundamentals`. See § "Most common false positives" item 4.
- **duplicate:** 0 cases. The extractor deduplicates on `(posting_id, taxonomy_id, extracted_span)`.
- **ambiguous:** 0 cases. Every reviewed case had a defensible label under the decision rules below.

## Taxonomy mappings and source-data problems that caused difficulty

1. **Single-word domain aliases dominate matches.** `DOM-06 Business, finance and administration` has aliases "finance", "commerce", "administration" — all of which appear in many programme titles and functions. `DOM-05 Education and human capital` has alias "education", present in most teacher-training programmes. These single-word aliases are the direct cause of 32 of 35 FPs.

2. **No skill text in demand postings.** `description_raw` is empty across all 15 demand records in the Week 3 ETL output. The pipeline therefore extracts skills only from supply programme titles, which is a weaker signal (a programme title says what was studied, not what an employer requires).

3. **Ugandan civil-service titles are not in the taxonomy.** "District Education Officer", "Assistant Law Enforcement Officer", "Principal Internal Auditor", "Education Assistant II" are all standard Ugandan public-service designations but none appear as aliases. This is a taxonomy coverage issue, not a pipeline bug — but the pipeline cannot recover from it.

4. **`function_raw` is a site category, not a skill statement.** Treating it as extraction input is a method error. For v2, `function_raw` should be treated as an occupation *hint only*, never as skill evidence.

## Planned v2 corrections (ranked)

1. **Remove `predicted_type=domain` from the extraction output entirely.** Domains are grouping concepts, not extraction targets. This alone raises precision from ~28% to ~60% on the current sample (16 of 25 non-domain cases are TP). The taxonomy remains the source of `DOM-*` groupings for Week 6 gap analysis — they are simply not emitted by the NLP step.

2. **Restrict `function_raw` to occupation matching only**, and only when it matches an `OCC-*` alias. Never emit skills from a function category.

3. **Add a length/word-count rule for aliases.** Single-word aliases shorter than 5 characters, or aliases appearing in more than 3 taxonomy concepts, are excluded from matching unless accompanied by a longer co-located match.

4. **Populate `description_raw` in the Week 3 ETL before Week 6.** Without posting text, skill extraction is a proxy at best. This is the single most impactful data-side fix.

5. **Expand Ugandan public-service title aliases** in `OCC-23` (Teaching professionals), `OCC-24` (Business and administration professionals), and add a new occupation concept for law-enforcement roles if the taxonomy review supports it.

6. **Add a v2 comparison using embedding-assisted semantic matching (`SKL-118`).** Measure precision/recall delta against v1 on the same labelled 53 cases. This becomes the Week 6 evaluation narrative.

## Validation discipline

- The Week 8 held-out sample (17 records, SHA-256 `0637fdc3b45a8a46e703885a9abc4919953531db54c1cbb2904128679bdfcddc`) was created **before** any pipeline runs. It has not been opened, tuned on, or reported on in this document.
- See `docs/week5_heldout.md` for the selection method, size, location, and checksum.

## Limits

See `docs/week5_limits.md` for the full statement of what v1 can and cannot support, including language, terminology, source-coverage, informal-sector, and taxonomy limitations.