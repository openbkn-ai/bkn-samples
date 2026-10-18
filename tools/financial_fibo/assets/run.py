#!/usr/bin/env python3
"""Replay 100 frozen read-only answers on local SQLite; not an LLM/online acceptance claim."""
import csv, hashlib, json, sqlite3, sys, time
from pathlib import Path
from decimal import Decimal
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from verify import load, verify_data, verify_model

def database(T,C):
 db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
 from decimal_sql import register
 register(db)
 for t,rows in T.items():
  fields=list(C['object_types'][t]['fields']);types=C['object_types'][t]['fields']
  db.execute('CREATE TABLE '+t+' ('+','.join('"'+f+'" '+('REAL' if types[f]=='decimal' else 'INTEGER' if types[f]=='integer' else 'TEXT') for f in fields)+')')
  db.executemany('INSERT INTO '+t+' VALUES ('+','.join('?' for _ in fields)+')',[[None if r[f]=='' else r[f] for f in fields] for r in rows])
 for t,c in C['object_types'].items():
  for f in c['fields']:
   if f.endswith('_id') or f.endswith('_date'):
    db.execute('CREATE INDEX idx_'+t+'_'+f+' ON '+t+' ("'+f+'")')
 db.execute('ANALYZE')
 from settlement_views import create_views
 create_views(db,actual=C['localized_values']['actual'] if T['trade_orders'][0]['view_kind']==C['localized_values']['actual'] else 'actual')
 db.set_authorizer(lambda action,*_:sqlite3.SQLITE_OK if action in (sqlite3.SQLITE_SELECT,sqlite3.SQLITE_READ,sqlite3.SQLITE_FUNCTION) else sqlite3.SQLITE_DENY)
 return db

def same(a,b,tolerance):
 if type(a) in (int,float) and type(b) in (int,float):return abs(Decimal(str(a))-Decimal(str(b)))<=Decimal(str(tolerance))
 if type(a)!=type(b):return False
 if isinstance(a,list):return len(a)==len(b) and all(same(x,y,tolerance) for x,y in zip(a,b))
 if isinstance(a,dict):return a.keys()==b.keys() and all(same(a[k],b[k],tolerance) for k in a)
 return a==b

def evaluate(root=ROOT):
 T,C=load(root);verify_model(root,T,C);report=verify_data(T,C,'zh-cn' in root.name)
 Q=json.loads((root/'bkn-eval/questions.json').read_text(encoding='utf-8'));gold=json.loads((root/'bkn-eval/expected-results.json').read_text(encoding='utf-8'))
 assert len(Q)==len(gold)==100 and len({q['id'] for q in Q})==100
 assert len({q['question'] for q in Q})==100
 from collections import Counter
 assert Counter(q['level'] for q in Q)=={'easy_basic':30,'intermediate':40,'hard_complex':30}
 assert Counter(q['scenario_id'] for q in Q)=={f'S{i:02}':10 for i in range(1,11)}
 assert set().union(*(set(q['evidence_tables']) for q in Q))==set(T),'question table coverage'
 db=database(T,C);relations={r['id'] for r in C['relations']};results=[]
 assert set().union(*(set(q['required_relations']) for q in Q))==relations,'question relation coverage'
 for q in Q:
  assert set(q['required_relations'])<=relations,q['id']
  started=time.monotonic()
  db.set_progress_handler(lambda: int(time.monotonic()-started>30),100000)
  try:actual=[dict(r) for r in db.execute(q['evidence_sql'])]
  except sqlite3.Error as exc:raise AssertionError(q['id']+' evidence query failed: '+str(exc)) from exc
  finally:db.set_progress_handler(None,0)
  assert same(actual,gold[q['id']]['rows'],q['numeric_tolerance']),q['id']+' frozen answer mismatch'
  results.append({'id':q['id'],'passed':True,'evidence_rows':len(actual),'duration_ms':round((time.monotonic()-started)*1000,3)})
 db.close()
 bound_paths=['dataset.lock','model-contract.json','bkn-eval/questions.json','bkn-eval/expected-results.json','tools/verify.py','tools/settlement_views.py','tools/decimal_sql.py','bkn-eval/run.py']
 bound_paths += sorted(str(p.relative_to(root)) for p in (root/'kn').rglob('*.bkn'))
 bindings={p:'sha256:'+hashlib.sha256((root/p).read_bytes()).hexdigest() for p in bound_paths}
 return {'ok':True,'evidence_binding':bindings,'tables_covered':len(set().union(*(set(q['evidence_tables']) for q in Q))),'sample':root.name,**report,'questions_passed':len(results),'levels':dict(Counter(q['level'] for q in Q)),'results':results,'boundary':'Local deterministic verification; platform import and independent agent evaluation not performed.'}

if __name__=='__main__':
 r=evaluate();print(json.dumps({k:v for k,v in r.items() if k!='results'},ensure_ascii=False))
 if '--report' in sys.argv:
  index=sys.argv.index('--report');Path(sys.argv[index+1]).write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
