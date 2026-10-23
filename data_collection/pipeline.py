import argparse,csv,hashlib,json,sqlite3,time,os,urllib.request,urllib.error
from urllib.parse import urlencode
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DB=ROOT/'skills_gap.db'
FIELDS=['posting_id','source','source_url','retrieved_at','sector','title','employer','location','date_posted','raw_text','raw_text_hash','collection_method_version']

def stamp():return datetime.now(timezone.utc).isoformat()
def digest(s):return hashlib.sha256(s.encode('utf-8')).hexdigest()
def connect():
 c=sqlite3.connect(DB)
 c.execute('CREATE TABLE IF NOT EXISTS jobs (posting_id TEXT PRIMARY KEY,source TEXT,source_url TEXT,retrieved_at TEXT,sector TEXT,title TEXT,employer TEXT,location TEXT,date_posted TEXT,raw_text TEXT,raw_text_hash TEXT,collection_method_version TEXT)')
 c.execute('CREATE TABLE IF NOT EXISTS indicators (record_id TEXT PRIMARY KEY,source TEXT,source_url TEXT,retrieved_at TEXT,indicator_name TEXT,value REAL,unit TEXT,region TEXT,level TEXT,year INTEGER,notes TEXT)')
 return c

def save_jobs(records):
 c=connect(); count=0
 for r in records:
  if not r.get('posting_id') or not r.get('raw_text'):continue
  c.execute('INSERT OR REPLACE INTO jobs VALUES ('+','.join('?'*len(FIELDS))+')',[r.get(k,'') for k in FIELDS]);count+=1
 c.commit();c.close();return count

def export():
 c=connect();out=ROOT/'output';out.mkdir(exist_ok=True)
 for table in ('jobs','indicators'):
  cur=c.execute('SELECT * FROM '+table);cols=[d[0] for d in cur.description]
  with (out/(table+'.csv')).open('w',newline='',encoding='utf-8-sig') as f:
   w=csv.writer(f);w.writerow(cols);w.writerows(cur.fetchall())
 c.close()

def demo():
 samples=[('ICT Officer','Maintain computer networks and provide user support.'),('Data Analyst','Use Python, SQL and Excel to analyse datasets.'),('Education Officer','Coordinate teacher training and monitor learning outcomes.')]
 records=[]
 for i,(title,body) in enumerate(samples,1):
  records.append(dict(posting_id='DEMO-'+str(i),source='SYNTHETIC_DEMO',source_url='',retrieved_at=stamp(),sector='demonstration',title=title,employer='',location='Uganda',date_posted='',raw_text=body,raw_text_hash=digest(body),collection_method_version='demo-v1'))
 print('Synthetic demonstration rows:',save_jobs(records));export()

def reliefweb(limit):
 # API access, terms and rate limits must be rechecked before live use.
 appname=os.environ.get('RELIEFWEB_APPNAME','').strip()
 if not appname:raise RuntimeError('Set RELIEFWEB_APPNAME to your pre-approved ReliefWeb application name. See https://apidoc.reliefweb.int/parameters')
 url='https://api.reliefweb.int/v2/jobs?'+urlencode({'appname':appname})
 payload={'filter':{'field':'country.name','value':'Uganda'},'limit':min(limit,100),'fields':{'include':['title','body','date.created','date.original','url','source','country']}}
 req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','User-Agent':'SkillsGapAcademicPrototype/0.1 (contact: configure-team-email)'},method='POST')
 cache=ROOT/'cache';cache.mkdir(exist_ok=True)
 response=None
 for attempt in range(3):
  try:
   with urllib.request.urlopen(req,timeout=35) as r:response=json.load(r)
   break
  except urllib.error.HTTPError as e:
   detail=e.read().decode('utf-8',errors='replace')[:500]
   if e.code in (400,401,403,404,410):raise RuntimeError(f'ReliefWeb API HTTP {e.code}: {detail}. Check approved appname and v2 endpoint.') from e
   if attempt==2:raise RuntimeError('API request failed: '+str(e)) from e
   time.sleep(3*(attempt+1))
  except (urllib.error.URLError,TimeoutError) as e:
   if attempt==2:raise RuntimeError('API request failed; check network/API policy: '+str(e)) from e
   time.sleep(3*(attempt+1))
 (cache/('reliefweb_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json')).write_text(json.dumps(response,ensure_ascii=False,indent=2),encoding='utf-8')
 rows=[]
 for item in response.get('data',[]):
  f=item.get('fields',{});countries=f.get('country',[])
  if not any(isinstance(x,dict) and x.get('name','').casefold()=='uganda' for x in countries):continue
  body=f.get('body','') or ''
  if isinstance(body,dict):body=json.dumps(body)
  title=f.get('title','') or ''
  if not body.strip():continue
  rows.append(dict(posting_id='RW-'+str(item['id']),source='ReliefWeb',source_url=f.get('url') or '',retrieved_at=stamp(),sector='NGO/development',title=title,employer='',location='Uganda',date_posted=(f.get('date',{}).get('original') or f.get('date',{}).get('created') or ''),raw_text=body,raw_text_hash=digest(body),collection_method_version='reliefweb-api-v2'))
 print('Uganda records accepted:',save_jobs(rows),'of',len(response.get('data',[])),'returned');export()

def indicators(path):
 required={'source','source_url','indicator_name','value','unit','region','level','year','notes'}
 c=connect();n=0
 with open(path,encoding='utf-8-sig',newline='') as f:
  reader=csv.DictReader(f)
  if not required.issubset(reader.fieldnames or []):raise ValueError('Required columns: '+', '.join(sorted(required)))
  for row in reader:
   if not row['source'] or not row['indicator_name'] or not row['year']:continue
   key=digest('|'.join(row.get(k,'') for k in sorted(required)))
   c.execute('INSERT OR REPLACE INTO indicators VALUES (?,?,?,?,?,?,?,?,?,?,?)',(key,row['source'],row['source_url'],stamp(),row['indicator_name'],float(row['value']),row['unit'],row['region'],row['level'],int(row['year']),row['notes']));n+=1
 c.commit();c.close();export();print('Indicators imported:',n)

def quality():
 c=connect();total=c.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]
 missing=c.execute("SELECT COUNT(*) FROM jobs WHERE raw_text='' OR posting_id='' OR retrieved_at='' OR raw_text_hash=''").fetchone()[0]
 sources=c.execute('SELECT source,COUNT(*) FROM jobs GROUP BY source').fetchall()
 indicators_count=c.execute('SELECT COUNT(*) FROM indicators').fetchone()[0]
 c.close();print(json.dumps({'jobs':total,'missing_critical_fields':missing,'provenance_completeness_percent':round(100*(total-missing)/total,2) if total else None,'by_source':dict(sources),'indicators':indicators_count},indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['demo','reliefweb','indicators','quality','export']);p.add_argument('--limit',type=int,default=100);p.add_argument('--file');a=p.parse_args()
 if a.action=='demo':demo()
 elif a.action=='reliefweb':reliefweb(a.limit)
 elif a.action=='indicators':
  if not a.file:p.error('--file required for indicators')
  indicators(a.file)
 elif a.action=='quality':quality()
 else:export()
