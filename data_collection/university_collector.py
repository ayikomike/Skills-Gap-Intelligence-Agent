"""University supply-side data module. Standard library only. No automatic site crawling."""
import argparse,csv,hashlib,json,sqlite3,urllib.request,urllib.error,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parent
DB=ROOT/'skills_gap.db'
COLUMNS=['institution','programme_name','award_level','faculty','study_mode','duration_years','skills_text','academic_year','source_url','notes']
def now(): return datetime.now(timezone.utc).isoformat()
def sha(text): return hashlib.sha256(text.encode('utf-8')).hexdigest()
def db():
 c=sqlite3.connect(DB)
 c.execute("CREATE TABLE IF NOT EXISTS university_programmes (record_id TEXT PRIMARY KEY,institution TEXT,programme_name TEXT,award_level TEXT,faculty TEXT,study_mode TEXT,duration_years TEXT,skills_text TEXT,academic_year TEXT,source_url TEXT,notes TEXT,retrieved_at TEXT,collection_method_version TEXT,raw_text_hash TEXT)")
 c.execute("CREATE TABLE IF NOT EXISTS university_sources (institution TEXT PRIMARY KEY,homepage TEXT,programme_catalogue_url TEXT,permission_status TEXT,notes TEXT,checked_at TEXT,http_status TEXT)")
 return c
def valid_url(s):
 p=urlparse(s)
 return p.scheme=='https' and bool(p.netloc) and not p.username and not p.password

def import_programmes(path):
 c=db();count=0;skipped=[]
 with open(path,encoding='utf-8-sig',newline='') as f:
  reader=csv.DictReader(f)
  if not set(COLUMNS).issubset(reader.fieldnames or []): raise ValueError('Missing columns: '+str(set(COLUMNS)-set(reader.fieldnames or [])))
  for line,r in enumerate(reader,2):
   if not all(r.get(k,'').strip() for k in ('institution','programme_name','source_url','academic_year')) or not valid_url(r['source_url']):
    skipped.append(line);continue
   # preserve distinct source and academic year; same programme may appear in multiple years
   key=sha('|'.join(r.get(k,'').strip().casefold() for k in ('institution','programme_name','award_level','academic_year','source_url')))
   desc=' | '.join(r.get(k,'').strip() for k in COLUMNS)
   vals=[r.get(k,'').strip() for k in COLUMNS]+[now(),'university-manual-v1',sha(desc)]
   c.execute('INSERT OR REPLACE INTO university_programmes VALUES ('+','.join('?'*14)+')',[key]+vals)
   count+=1
 c.commit();c.close();export();print(json.dumps({'imported':count,'skipped_rows':skipped}))
def register_sources(path):
 c=db();n=0
 with open(path,encoding='utf-8-sig',newline='') as f:
  for r in csv.DictReader(f):
   if not r.get('institution') or not valid_url(r.get('homepage','')):continue
   c.execute('INSERT OR REPLACE INTO university_sources VALUES (?,?,?,?,?,?,?)',(r['institution'],r['homepage'],r.get('programme_catalogue_url',''),r.get('permission_status',''),r.get('notes',''),now(),'NOT_CHECKED'));n+=1
 c.commit();c.close();print('University source catalogue registered:',n)
def check_sources(path,limit):
 # HEAD only; no scraping or automatic following of links
 rows=list(csv.DictReader(open(path,encoding='utf-8-sig',newline='')))
 c=db();results=[]
 for r in rows[:limit]:
  url=r.get('programme_catalogue_url','').strip() or r.get('homepage','').strip()
  if not valid_url(url):continue
  status='UNKNOWN'
  try:
   req=urllib.request.Request(url,method='HEAD',headers={'User-Agent':'SkillsGapResearch/0.1 (academic metadata check; contact project team)'})
   with urllib.request.urlopen(req,timeout=12) as res:status=str(res.status)
  except urllib.error.HTTPError as e:status='HTTP '+str(e.code)
  except Exception as e:status=type(e).__name__
  c.execute('UPDATE university_sources SET checked_at=?,http_status=? WHERE institution=?',(now(),status,r['institution']))
  results.append({'institution':r['institution'],'url':url,'status':status})
  time.sleep(2)
 c.commit();c.close();print(json.dumps(results,indent=2))
def export():
 c=db();out=ROOT/'output';out.mkdir(exist_ok=True)
 for name in ('university_programmes','university_sources'):
  cur=c.execute('SELECT * FROM '+name)
  with (out/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.writer(f);w.writerow([d[0] for d in cur.description]);w.writerows(cur.fetchall())
 c.close()
def quality():
 c=db();n=c.execute('SELECT COUNT(*) FROM university_programmes').fetchone()[0]
 missing=c.execute("SELECT COUNT(*) FROM university_programmes WHERE source_url='' OR academic_year='' OR raw_text_hash='' OR institution='' OR programme_name=''").fetchone()[0]
 by_source=dict(c.execute('SELECT institution,COUNT(*) FROM university_programmes GROUP BY institution').fetchall())
 print(json.dumps({'programme_rows':n,'missing_critical_fields':missing,'by_institution':by_source,'note':'Programme counts are not graduate output or skills proficiency measures'},indent=2));c.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['register','check','import','export','quality']);p.add_argument('--file');p.add_argument('--limit',type=int,default=5);a=p.parse_args()
 if a.action=='register':register_sources(a.file or str(ROOT/'universities.csv'))
 elif a.action=='check':check_sources(a.file or str(ROOT/'universities.csv'),a.limit)
 elif a.action=='import':
  if not a.file:p.error('import requires --file')
  import_programmes(a.file)
 elif a.action=='export':export()
 else:quality()
