# Schema v0.2 (revised after labelling 20 postings)

One flat table, `record_type` = `demand` | `supply`.

**Provenance (all records, must be non-empty):** `record_id` (stable: `source:` + hash of URL/ref/title or title+employer),
`record_type`, `source`, `source_url` (page/PDF collected), `record_url` (individual record where one exists),
`retrieved_at`, `retrieval_method` (`http_get` | `cache_replay` | `manual_fetch_tool_capture`), `pipeline_version`, `raw_hash`.

**Demand:** `title`, `employer`, `location`, `posted_text` (as shown), `posted_date_est` (ESTIMATE from "4 days ago"),
`function_raw` (source label, **noisy**), `department`, `ref_no`, `salary_scale`, `vacancies`, `deadline`, `description_raw`.

**Supply:** `institution`, `ceremony`, `award_level`, `programme`, `graduate_count`,
`count_basis` (`numbered_rows_counted` | `exact` | `approx` | `combined`), `field_group_provisional` (`STEM` | `NON_STEM` | `REVIEW_HEALTH`).

## Changes from v0.1 and why (from the labelling exercise)
1. `description_raw` is mandatory for the NLP work but was empty for 100% of captured postings, so the next run must collect it.
2. Added `employer` quality note: 6 of 16 BrighterMonday postings come from a recruiter (BrighterMonday Consulting) or an
   "Anonymous Employer"; plan a derived `employer_is_intermediary` flag in Week 4.
3. `function_raw` disagrees with the title in 5 of 15 labelled BrighterMonday postings, so it must not be used as an occupation label.
4. `posted_date_est` replaces a plain date, since the site gives only relative ages.
5. Supply `count_basis` added so approximate and combined counts are never summed silently.
6. `field_group_provisional` is a placeholder for the NDPIV STEM:humanities ratio; health programmes need a supervisor decision.
7. Labelling scheme for Week 4: ISCO-08 major group now, O*NET/ESCO-aligned skills once descriptions exist.
