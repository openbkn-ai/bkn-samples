"""Development invariants and hand-calculated edge checks, not formal Q&A."""
import copy,csv,json,hashlib
from pathlib import Path
from decimal import Decimal
from schema import TABLES,FKS
from retail_core import execute
ROOT=Path(__file__).resolve().parents[2]
def load(lang):
 p=ROOT/'samples'/('retail-gs1-'+lang)
 return {t:list(csv.DictReader((p/'data'/(t+'.csv')).open())) for t in TABLES},json.loads((p/'model-contract.json').read_text())
def main():
 results={};checks=[]
 def check(name,condition):
  if not condition:raise AssertionError(name)
  checks.append(name)
 for lang in ('en-us','zh-cn'):
  tables,c=load(lang);count={}
  for t,rows in tables.items():
   pk=TABLES[t][0];check(lang+':unique:'+t,len({r[pk] for r in rows})==len(rows));check(lang+':minimum:'+t,len(rows)>=50);count[t]=len(rows)
   for f,(dest,key) in FKS.get(t,{}).items():
    keys={r[key] for r in tables[dest]};check(lang+':fk:'+t+'.'+f,all(not r[f] or r[f] in keys for r in rows))
  scope={'product_ids':['PRD-001'],'as_of_date':'2027-02-28','knowledge_date':'2027-02-28','view_kind':'actual'}
  def run(op='inventory_asof',s=None,t=None):return execute(op,t or tables,c,s or scope)
  inv=run();by={(r['lot_id'],r['location_id']):r for r in inv['rows']}
  wh=by[('LOT-001-C','WH-001')];store=by[('LOT-001-C','STORE-001')]
  check(lang+':C-wh-stock',wh['on_hand']=='141.000000');check(lang+':C-wh-reserved',wh['reserved']=='30.000000');check(lang+':C-wh-available',wh['available']=='111.000000')
  check(lang+':return-hold-union',store['on_hand']=='27.000000' and store['quarantined']=='5.000000' and store['available']=='22.000000')
  check(lang+':expired-block',by[('LOT-001-A','WH-001')]['available']=='0.000000')
  check(lang+':recall-descendant-block',by[('LOT-001-D','WH-001')]['available']=='0.000000')
  alloc=run('fulfillment_plan')['rows'];aa={r['order_id']:r for r in alloc}
  check(lang+':shared-allocation',aa['ORD-001-A']['allocated_quantity']=='111.000000' and aa['ORD-001-B']['allocated_quantity']=='30.000000' and aa['ORD-001-B']['shortage_quantity']=='71.000000')
  plan=run('fulfillment_plan',dict(scope,mode='replenishment'))['rows'];check(lang+':planned-supply',plan[0]['eligible_supply_quantity']=='137.000000' and plan[0]['allocated_quantity']=='81.000000')
  check(lang+':forecast-end-date',plan[-1]['demand_date']=='2027-03-31' and plan[-1]['eligible_supply_quantity']=='0.000000')
  recall=run('recall_assessment',dict(scope,recall_id='REC-001'))['rows'];rw=next(r for r in recall if r['location_id']=='WH-001')
  check(lang+':recall-denominator',rw['controllable_quantity']=='152.000000' and rw['controlled_quantity']=='20.000000' and rw['coverage_ratio']=='0.131579')
  snap={ (r['lot_id'],r['location_id']):r for r in tables['inventory_snapshots'] if r['product_id']=='PRD-001'}
  check(lang+':snapshot-reconcile',all(snap[k]['available']==r['available'] for k,r in by.items()))
  # Explicit anomaly facts, with exact first-observation scope.
  for n,code in [(42,'DUPLICATE_EVENT_IGNORED'),(43,'CONFLICTING_EVENT'),(45,'TRANSFER_COVERAGE_MISSING'),(46,'NEGATIVE_STOCK')]:
   res=run(s=dict(scope,product_ids=[f'PRD-{n:03}']));check(lang+':fixture:'+code,any(i['code']==code for i in res['issues']))
  late=run(s=dict(scope,product_ids=['PRD-041'],knowledge_date='2027-03-02'))['rows'];before=run(s=dict(scope,product_ids=['PRD-041']))['rows']
  a=next(r for r in late if r['lot_id']=='LOT-041-C' and r['location_id']=='STORE-016');b=next(r for r in before if r['lot_id']=='LOT-041-C' and r['location_id']=='STORE-016')
  check(lang+':late-known-cutoff',Decimal(b['on_hand'])-Decimal(a['on_hand'])==7)
  for n in (43,45,46):
   rows=run(s=dict(scope,product_ids=[f'PRD-{n:03}']))['rows'];check(lang+':unknown-not-zero:'+str(n),any(r['available'] is None for r in rows))
  # Overreservation cannot manufacture stock; own capacity restored once.
  mut=copy.deepcopy(tables)
  for r in mut['reservations']:
   if r['lot_id']=='LOT-001-C':r['quantity']='999'
  ar=run('fulfillment_plan',t=mut)['rows'];check(lang+':overreservation-conservation',sum(Decimal(r['allocated_quantity']) for r in ar)<=141)
  # Pending inspection blocks inventory and allocations.
  mut=copy.deepcopy(tables);new=copy.deepcopy(next(r for r in mut['inspections'] if r['lot_id']=='LOT-001-C'));new['inspection_id']='QC-CONFLICT';new['result_code']='failed';mut['inspections'].append(new)
  check(lang+':inspection-conflict',any(i['code']=='CONFLICTING_INSPECTION' for i in run(t=mut)['issues']))
  # Backlog is retained instead of silently disappearing.
  mut=copy.deepcopy(tables);next(r for r in mut['orders'] if r['order_id']=='ORD-001-A')['due_date']='2027-02-27'
  check(lang+':overdue-open-order',any(r['order_id']=='ORD-001-A' for r in run('fulfillment_plan',t=mut)['rows']))
  results[lang]={'rows':count,'all_minimum_50':True}
 # Stable facts match bilingual networks; localized strings are intentionally different.
 en,_=load('en-us');zh,_=load('zh-cn')
 localized={'name','category','unit','role','location_type','event_type','view_kind','result','reason','status','link_type'}
 for t in TABLES:
  fields=set(TABLES[t][1].split())-localized
  check('bilingual:'+t,all(all(a[f]==b[f] for f in fields) for a,b in zip(en[t],zh[t])) and len(en[t])==len(zh[t]))
 report={'kind':'development-invariants-not-formal-agent-acceptance','checks_passed':len(checks),'checks':checks,'languages':results,'known_anomalies':{'LOT-041-C':'late sale visible03-02','LOT-042-C':'duplicate semantic event ignored','LOT-043-C':'conflicting event','LOT-044-C':'erroneous sale reversed','LOT-045-C':'missing dispatch','LOT-046-C':'negative stock','REC-048':'cross-product descendant'}}
 p=Path(__file__).with_name('development-verification.json');p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'checks_passed':len(checks),'report':str(p)},indent=2))
if __name__=='__main__':main()
