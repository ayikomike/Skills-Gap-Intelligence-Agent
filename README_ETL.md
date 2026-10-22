# Skills-Gap Intelligence: ETL Pipeline v1 (Week 3)

Re-runnable collection pipeline for the Skills-Gap Intelligence capstone (MSc CS & AI, Muni University).
Collects **demand** signals (job postings) and **supply** signals (published university graduation lists),
keeps provenance on every record, and writes a data-quality report. Decision support only: no personal data.

## Setup (fresh machine)
```bash
git clone https://github.com/ayikomike/Skills-Gap-Intelligence-Agent && cd Skills-Gap-Intelligence-Agent
python3 -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env     # then edit: SKILLSGAP_CONTACT_EMAIL=<your student email>  (never commit .env)
export $(grep -v '^#' .env | xargs)                      # Windows PowerShell: $env:SKILLSGAP_CONTACT_EMAIL="..."
```
Python 3.10+ (developed on 3.13).

## Run
```bash
export PYTHONPATH=src
python -m skillsgap.pipeline --out out/                          # fresh run, all approved sources
python -m skillsgap.pipeline --out out/ --sources graduation_lists   # one source
python -m skillsgap.pipeline --out out/ --offline                # re-run from cache, zero network requests
python -m pytest -q tests                                        # 15 tests
```
Entry point: `src/skillsgap/pipeline.py`. Config: `config/sources.yaml`.
Outputs in `out/`: `dataset.csv`, `dataset.json`, `quality_report.json`, `compliance_run_log.csv`,
`run_manifest.json`, `logs/pipeline.log`.

## Responsible-collection controls (all in `src/skillsgap/http.py`)
| Control | Behaviour |
|---|---|
| Honest user agent | `MuniUni-SkillsGapCapstone/0.1 (+repo URL; contact email from env)` |
| robots.txt | fetched per host and obeyed; disallowed URLs are skipped and logged |
| Rate limit | at most 1 request / 3 s per host (`min_delay_seconds`) |
| Cache | every response cached on disk 24 h; `--offline` replays the cache |
| Retry/backoff | 3 retries on 429/5xx/network errors, waits 2, 4, 8 s plus jitter |
| Logging | `out/logs/pipeline.log`; per-source failures never stop the run |
| Approval gate | a source runs only if `enabled: true` and an `approval` string is recorded |
| Secrets | none in the repo; contact address and any future keys come from `.env` |
| Privacy | graduation lists reduced to programme counts; names are never stored (tested) |

## Layout
`src/skillsgap/` http, schema, demand parsers, supply parser, quality, pipeline · `config/` source registry ·
`tests/` unit + end-to-end tests with synthetic structural fixtures · `data/seed/` captured rows ·
`data/sample/` first dataset, quality report, labelled sample · `docs/` schema + compliance log · `scripts/` builders.

## Known limits (be honest in reports)
- BrighterMonday selectors were written against the card text seen on the live page, **not yet validated on the
  live HTML**; first live run must check `quality_report.json -> parse_failure_detail`.
- Listing descriptions are not collected yet (`fetch_descriptions: false`): skills cannot be extracted until this is approved/enabled.
- Graduation-list parser handles **numbered** lists; unnumbered or scanned lists are logged as failures (need custom rule/OCR).
- Sample data in `data/sample/` was captured through a fetch tool, not this pipeline (see `retrieval_method`).
