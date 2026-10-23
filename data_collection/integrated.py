"""Unified command line entry point for the Week 3 Skills Gap pipeline.
No unauthorised scraping; external PDF files must be downloaded lawfully by user.
"""
import argparse,csv,json,hashlib,re
from pathlib import Path
from urllib.parse import urlparse
import pipeline as jobs
import university_collector as universities

ROOT=Path(__file__).resolve().parent

def import_jobs(path):
    required={'source','source_url','sector','title','employer','location','date_posted','raw_text'}
    rows=[];skipped=[]
    with open(path,encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('Missing columns: '+str(required-set(reader.fieldnames or [])))
        for line,r in enumerate(reader,2):
            source=r['source'].strip();url=r['source_url'].strip();title=r['title'].strip();body=r['raw_text'].strip()
            parsed=urlparse(url)
            if not source or not title or not body or parsed.scheme not in ('https','http') or not parsed.netloc:
                skipped.append(line);continue
            key=jobs.digest(source+'|'+url+'|'+title)
            rows.append(dict(posting_id='MAN-'+key[:24],source=source,source_url=url,retrieved_at=jobs.stamp(),sector=r['sector'],title=title,employer=r['employer'],location=r['location'],date_posted=r['date_posted'],raw_text=body,raw_text_hash=jobs.digest(body),collection_method_version='manual-verified-v1'))
    n=jobs.save_jobs(rows);jobs.export();print(json.dumps({'accepted':n,'skipped_lines':skipped},indent=2))

def import_psc(folder):
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise SystemExit('Install PDF dependency: python -m pip install -r requirements.txt') from e
    folder=Path(folder)
    if not folder.is_dir():raise ValueError('Not a directory: '+str(folder))
    # Provenance URLs are provided in an accompanying manifest, not guessed from filenames.
    manifest=folder/'manifest.csv'
    if not manifest.exists():raise ValueError('Create '+str(manifest)+' with columns filename,source_url,title,date_posted')
    records=[];issues=[]
    with manifest.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if not {'filename','source_url','title','date_posted'}.issubset(reader.fieldnames or []):raise ValueError('PSC manifest columns: filename,source_url,title,date_posted')
        for r in reader:
            filename=Path(r['filename']).name
            pdf=folder/filename
            if pdf.suffix.lower()!='.pdf' or not pdf.is_file():issues.append(filename+': missing PDF');continue
            parsed=urlparse(r['source_url'])
            if parsed.scheme!='https' or not parsed.netloc:issues.append(filename+': missing valid source URL');continue
            try:text='\n'.join(page.extract_text() or '' for page in PdfReader(str(pdf)).pages).strip()
            except Exception as e:issues.append(filename+': '+str(e));continue
            if len(text)<100:issues.append(filename+': insufficient extractable text; manual verification needed');continue
            sha=hashlib.sha256(pdf.read_bytes()).hexdigest()
            records.append(dict(posting_id='PSC-'+sha[:24],source='Uganda Public Service Commission',source_url=r['source_url'],retrieved_at=jobs.stamp(),sector='public',title=r['title'] or pdf.stem,employer='',location='Uganda',date_posted=r['date_posted'],raw_text=text,raw_text_hash=jobs.digest(text),collection_method_version='psc-pdf-pypdf-v1;pdf_sha256='+sha))
    count=jobs.save_jobs(records);jobs.export();print(json.dumps({'accepted':count,'issues':issues},indent=2))

def report():
    import sqlite3
    c=jobs.connect();universities.db().close()
    tables=['jobs','indicators','university_programmes','university_sources']
    result={t:c.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in tables}
    result['jobs_by_source']=dict(c.execute('SELECT source,COUNT(*) FROM jobs GROUP BY source').fetchall())
    result['warning']='University programme listings are not graduate counts; synthetic demo jobs must be excluded from analysis.'
    c.close();print(json.dumps(result,indent=2))

def main():
    p=argparse.ArgumentParser(description='Unified Skills-Gap Week 3 ETL pipeline')
    p.add_argument('action',choices=['demo','reliefweb','import-jobs','import-psc','import-indicators','universities-register','universities-check','import-programmes','quality','export'])
    p.add_argument('--file',help='Input CSV or PSC PDF directory')
    p.add_argument('--limit',type=int,default=100)
    a=p.parse_args()
    if a.action=='demo':jobs.demo()
    elif a.action=='reliefweb':jobs.reliefweb(a.limit)
    elif a.action=='import-jobs':import_jobs(a.file or str(ROOT/'jobs_template.csv'))
    elif a.action=='import-psc':import_psc(a.file or str(ROOT/'psc_pdfs'))
    elif a.action=='import-indicators':jobs.indicators(a.file or str(ROOT/'indicators_template.csv'))
    elif a.action=='universities-register':universities.register_sources(str(ROOT/'universities.csv'))
    elif a.action=='universities-check':universities.check_sources(str(ROOT/'universities.csv'),a.limit)
    elif a.action=='import-programmes':universities.import_programmes(a.file or str(ROOT/'programmes_template.csv'))
    elif a.action=='quality':report();jobs.quality();universities.quality()
    elif a.action=='export':jobs.export();universities.export();print('CSV files exported to output/')
if __name__=='__main__':main()
