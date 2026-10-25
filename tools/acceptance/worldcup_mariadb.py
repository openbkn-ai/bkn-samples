"""Disposable local SQL acceptance only; no OpenBKN product or platform credentials."""
import csv, importlib.util, io, json, subprocess, time, uuid
from pathlib import Path
from pymysql.converters import escape_string
import yaml
ROOT=Path(__file__).resolve().parents[2]
import argparse
parser=argparse.ArgumentParser(description="Validate frozen World Cup data in a disposable, network-isolated MariaDB container")
parser.add_argument('--output', required=True, type=Path)
parser.add_argument('--image', default='mariadb:11.4')
args=parser.parse_args()
OUT=args.output.resolve()
OUT.parent.mkdir(parents=True, exist_ok=True)
name='samples021-worldcup-'+uuid.uuid4().hex[:8]
def docker(*args,**kwargs):return subprocess.run(['docker',*args],check=True,capture_output=True,**kwargs)
def sql(statement,database=None):
 args=['exec','-i',name,'mariadb','-uroot','-psamples021-ephemeral','--batch','--raw']
 if database:args.append(database)
 return docker(*args,input=statement.encode()).stdout.decode()
def quote(v):return 'NULL' if v is None else str(v) if isinstance(v,int) else "'"+escape_string(v)+"'"
result={'image':docker('image','inspect',args.image,'--format','{{.Id}}').stdout.decode().strip(),'samples':[]}
created=False
try:
 docker('run','-d','--rm','--pull=never','--network=none','--name',name,'-e','MARIADB_ROOT_PASSWORD=samples021-ephemeral',result['image'])
 created=True
 for _ in range(60):
  try:sql('SELECT 1;');break
  except subprocess.CalledProcessError:time.sleep(0.5)
 else:raise RuntimeError('isolated database did not become ready')
 result['sql_dialect_adapter']='Quote the existing AS rows alias as AS `rows` for MariaDB; frozen business SQL and expected answers unchanged'
 result['server_version']=sql('SELECT VERSION();').splitlines()[1]
 for sample in ('world-cup','world-cup-en'):
  root=ROOT/'samples'/sample
  spec=importlib.util.spec_from_file_location(sample,root/'db/load_worldcup.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  db=sample.replace('-','_');sql('CREATE DATABASE '+db+';')
  counts={}
  for path in sorted((root/'data').glob('*.csv')):
   with path.open(newline='',encoding='utf-8-sig') as f:
    reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
   table=m.table_name(path);kinds=m.column_types(table,fields)
   sql(';'.join(m.create_table_statements(table,fields))+';',db)
   for offset in range(0,len(rows),500):
    batch=rows[offset:offset+500]
    values=','.join('('+','.join(quote(m.convert_value(row[k],kinds[k])) for k in fields)+')' for row in batch)
    sql('INSERT INTO `'+table+'` VALUES '+values+';',db)
   sql('CREATE VIEW `'+path.stem+'` AS SELECT * FROM `'+table+'`;',db);counts[path.stem]=len(rows)
  actual_types=sql("SELECT TABLE_NAME,COLUMN_NAME,DATA_TYPE FROM information_schema.columns WHERE TABLE_SCHEMA='"+db+"' AND TABLE_NAME LIKE 'wc_%' ORDER BY TABLE_NAME,ORDINAL_POSITION;",db)
  numeric=sum(line.endswith('\tbigint') for line in actual_types.splitlines()[1:])
  assert numeric==142,numeric
  count=sql('SELECT COUNT(*) AS count FROM wc_matches WHERE home_team_score >= 3;',db).splitlines()[1]
  independent=sum(int(row['home_team_score'])>=3 for row in csv.DictReader((root/'data/matches.csv').open()))
  assert int(count)==independent
  expected={a['id']:a['rows'] for a in yaml.safe_load((root/'bkn-eval/gold/answer-set-v1.yaml').read_text())['answers']}
  grade_spec=importlib.util.spec_from_file_location('grade',ROOT/'samples/world-cup/bkn-eval/scripts/grade_answers.py');grade=importlib.util.module_from_spec(grade_spec);grade_spec.loader.exec_module(grade)
  checks=[]
  for case in json.loads((root/'bkn-eval/gold/cases.json').read_text()):
   try:
    text=sql(case['sql'].replace(' AS rows', ' AS `rows`')+';',db)
    actual=list(csv.DictReader(io.StringIO(text),delimiter='\t'))
    for row,ref in zip(actual,expected[case['id']]):
     for k,v in row.items():
      if ref.get(k) is None and v=='NULL':row[k]=None
    errors=grade.row_differences(expected[case['id']],actual,0.0005)
    checks.append({'id':case['id'],'passed':not errors,'differences':errors[:2]})
   except subprocess.CalledProcessError as e:checks.append({'id':case['id'],'passed':False,'error':e.stderr.decode()[:500]})
  result['samples'].append({'sample':sample,'table_count':len(counts),'row_count':sum(counts.values()),'numeric_columns':numeric,'score_gte_3':int(count),'independent_score_gte_3':independent,'gold_passed':sum(c['passed'] for c in checks),'gold_total':len(checks),'gold_checks':checks,'column_types_tsv':actual_types})
finally:
 if created:
  subprocess.run(['docker','rm','-f',name],capture_output=True)
 OUT.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps([{k:v for k,v in s.items() if k not in ('column_types_tsv','gold_checks')} for s in result['samples']]))
