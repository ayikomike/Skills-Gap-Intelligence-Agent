# Unified Skills-Gap Intelligence Agent — Week 3

**One entry point:** `integrated.py`. Works with Python 3.11 and SQLite; only local PSC PDF parsing requires `pypdf`.

## Run in VS Code (PowerShell)

```powershell
python integrated.py universities-register
python integrated.py quality
python integrated.py demo
python integrated.py export
```

## Real data without ReliefWeb AppName

1. Download authorised public vacancy PDFs from Uganda Public Service Commission. Put files in `psc_pdfs/` and add **the actual public PDF URL**, title and posted date to `psc_pdfs/manifest.csv`. Then:

```powershell
python -m pip install -r requirements.txt
python integrated.py import-psc --file psc_pdfs
```

2. For other sources that permit research reuse, manually enter **verified** job records into `jobs_template.csv`, including original URLs; then:

```powershell
python integrated.py import-jobs --file jobs_template.csv
```

3. For official statistics, enter **published values only** in `indicators_template.csv`, with year, unit and URL:

```powershell
python integrated.py import-indicators --file indicators_template.csv
```

4. Verify programme pages on university sites, enter real programme records into `programmes_template.csv`, then:

```powershell
python integrated.py import-programmes --file programmes_template.csv
python integrated.py quality
python integrated.py export
```

5. Optional: Check university homepage HTTP status (HEAD request only; not a programme scraper):

```powershell
python integrated.py universities-check --limit 5
```

6. ReliefWeb is **optional**, and only usable after receiving a pre-approved `RELIEFWEB_APPNAME`:

```powershell
$env:RELIEFWEB_APPNAME = 'YOUR_APPROVED_NAME'
python integrated.py reliefweb --limit 100
```

## Source and compliance notes

- PSC: manually download and cite source PDFs. Text extraction is not OCR; scanned PDFs need manual processing.
- UBOS, MoES and NCHE: manually transcribe or import officially published statistics, retain year, unit and URL; obey microdata licences.
- Universities: register/check source websites and import verified programme details. **No automated site scraping** is included. Registration alone is not data collection.
- Fuzu excluded; BrighterMonday held pending written permission, consistent with Week 2 plan.
- Do not collect CVs, names of applicants, or personal contact information. Check source conditions before collecting.
- `demo` inserts three **synthetic** rows labelled `SYNTHETIC_DEMO`; exclude from research findings.
- Repeated imports use stable IDs for deduplication. Raw job text remains local and should not be redistributed.
- Quality report distinguishes job records, indicators, programmes, and registered universities.

## Database

`skills_gap.db` holds `jobs`, `indicators`, `university_programmes`, and `university_sources`. `output/` contains CSV exports. Keep your existing database when updating; back it up first.

## Important limitations

Live website/API access was **not** validated in this package. URLs in the university registry are candidate official sites, not independently verified live programme pages. Data templates are intentionally empty. Manual import is a legitimate Week 3 ingestion route, not evidence of automatic harvesting.
