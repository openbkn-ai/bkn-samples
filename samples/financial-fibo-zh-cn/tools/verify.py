#!/usr/bin/env python3
"""Independent financial invariants. No generator or expected-answer imports."""
import csv, hashlib, json, re, sys
from pathlib import Path
from decimal import Decimal as D, ROUND_HALF_UP
from datetime import date, timedelta
from collections import defaultdict, Counter

ROOT=Path(__file__).resolve().parents[1]

def require(ok,message):
 if not ok:raise AssertionError(message)
def quant(x,places=2):return D(x).quantize(D(10)**-places,rounding=ROUND_HALF_UP)
def equal(a,b,label,places=2):require(quant(a,places)==quant(b,places),f'{label}: observed {a}, recomputed {b}')
def decision(observed,threshold):
 if observed in ('',None):return 'unknown'
 return 'breach' if D(observed)>D(threshold) else 'within'
def load(root=ROOT,check_lock=True):
 contract=json.loads((root/'model-contract.json').read_text(encoding='utf-8'))
 lock=json.loads((root/'dataset.lock').read_text(encoding='utf-8'));T={}
 require(set(lock['files'])=={p.name for p in (root/'data').glob('*.csv')},'CSV inventory differs from lock')
 for t,c in contract['object_types'].items():
  p=root/'data'/(t+'.csv')
  if check_lock:require('sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()==lock['files'][p.name],'data hash '+t)
  with p.open(encoding='utf-8',newline='') as f:
   reader=csv.DictReader(f);require(reader.fieldnames==list(c['fields']),'column contract '+t);T[t]=list(reader)
  require(len(T[t])>=50,'insufficient business records '+t)
  require(len(T[t])==lock['record_counts'][t],'record count '+t)
 return T,contract

def verify_data(T,C,zh=False):
 M=lambda x:C['localized_values'].get(x,x) if zh else x
 by={t:{r[C['object_types'][t]['primary_key']]:r for r in rows} for t,rows in T.items()}
 allowed={
  'entity_role':{'issuer','broker','manager'},'asset_class':{'equity','bond'},'unit':{'share','face_unit'},'price_basis':{'per_share','dirty_per_100'},
  'side':{'buy','sell'},'order_status':{'accepted','planned'},'trade_status':{'executed','planned'},'view_kind':{'actual','planned'},
  'event_status':{'settled','pending','partial','failed'},'failure_reason':{'none','insufficient_securities','cash_mismatch','awaiting_confirmation','awaiting_balance','forecast_only'},
  'valuation_status':{'complete','blocked'},'reason':{'none','missing','price_unapproved','stale'},'approval':{'approved','unapproved'},
  'exposure_status':{'complete','blocked'},'measure':{'issuer_ratio','receivable_amount'},'assessment_status':{'within','breach','unknown'},
  'valuation_method':{'equity_mark','bond_dirty'},'mandate':{'long_only'},
 }
 for table,rows in T.items():
  for row in rows:
   for f,values in allowed.items():
    if f in row:require(row[f] in {M(v) for v in values},'invalid controlled value '+table+'.'+f)
 for t,rows in T.items():
  require(len(rows)==len(by[t]),'duplicate primary key '+t)
  for r in rows:
   require(r[C['object_types'][t]['primary_key']]!='','empty primary key '+t)
   for f,typ in C['object_types'][t]['fields'].items():
    if r[f]=='':continue
    if typ=='decimal':require(D(r[f]).is_finite(),'nonfinite '+t+'.'+f)
    if typ=='date':require(date.fromisoformat(r[f]).isoformat()==r[f],'not ISO date '+t+'.'+f)
    if typ=='integer':require(str(int(r[f]))==r[f],'not integer '+t+'.'+f)
    if typ=='boolean':require(r[f] in ('true','false'),'not boolean '+t+'.'+f)
 for rel in C['relations']:
  for r in T[rel['source']]:
   fk=r[rel['source_property']]
   require((not fk and rel['nullable']) or fk in by[rel['target']],f'broken relation {rel["id"]}: {fk}')
 # Uniform temporal control over every fact carrying a knowledge date, not just valuations.
 for table,rows in T.items():
  for row in rows:
   if 'known_date' not in row:continue
   planned=row.get('view_kind')==M('planned') or row.get('trade_status')==M('planned')
   fact_date=row.get('as_of_date',row.get('event_date',row.get('trade_date',row.get('order_date'))))
   require(fact_date is not None,'missing fact date '+table)
   require(row['known_date']<=C['current_as_of'],'future knowledge '+table)
   if planned:require(fact_date>C['current_as_of'],'planned fact in actual interval '+table)
   else:
    require(row['known_date']<=fact_date<=C['current_as_of'],'actual future knowledge '+table)
    if table in ('trade_orders','securities_transactions','settlement_events'):
     require(row['known_date']==fact_date,'actual atomic outcome known before occurrence '+table)
   if 'published_date' in row:
    require(row['published_date']<=fact_date,'future publication '+table)
    if not planned:require(row['published_date']<=row['known_date'],'unpublished data '+table)
 for row in T['market_prices']:
  require(row['pricing_source']==M('demo_pricing'),'unknown pricing source')
  require(date.fromisoformat(row['price_date']).weekday()<5,'weekend market quote')
  require(row['price_date']<=row['published_date'],'quote publication precedes quote')
 for row in T['fx_rates']:
  require(date.fromisoformat(row['published_date']).weekday()<5,'weekend FX fixing')
 # Role-sensitive associations cannot be satisfied by the wrong entity merely sharing a key.
 for r in T['financial_instruments']:
  require(by['legal_entities'][r['issuer_id']]['entity_role']==M('issuer'),'instrument issuer role')
  require(r['asset_class'] in (M('equity'),M('bond')),'unsupported asset class')
  equal(r['price_multiplier'],'.01' if r['asset_class']==M('bond') else '1','instrument price multiplier',6)
  require(r['unit']==M('face_unit' if r['asset_class']==M('bond') else 'share'),'instrument unit mismatch')
  require(r['price_basis']==M('dirty_per_100' if r['asset_class']==M('bond') else 'per_share'),'instrument quote basis mismatch')
 for r in T['portfolios']:require(by['legal_entities'][r['manager_id']]['entity_role']==M('manager'),'manager role')
 for r in T['trade_orders']:require(by['legal_entities'][r['counterparty_id']]['entity_role']==M('broker'),'counterparty role')
 require(Counter(r['branch'] for r in T['portfolios'])==Counter({M(k):v*(C['portfolios']//50) for k,v in {'normal':18,'pending_settlement':10,'failed_settlement':6,'price_exception':6,'issuer_breach':5,'counterparty_breach':3,'future_limit':2}.items()}),'business branches')
 require(all(r['is_synthetic']=='true' and r['synthetic_code'].startswith('DEMO-') for t in ('security_identifiers','legal_entity_identifiers') for r in T[t]),'synthetic identifier policy')
 events=defaultdict(list);trades_by_open=defaultdict(list)
 for e in T['settlement_events']:events[e['instruction_id']].append(e)
 for key in events:events[key].sort(key=lambda e:(e['event_date'],int(e['event_sequence'])))
 instr_by_trade=defaultdict(list)
 for s in T['settlement_instructions']:instr_by_trade[s['trade_id']].append(s)
 for t in T['securities_transactions']:
  o=by['trade_orders'][t['order_id']];i=by['financial_instruments'][o['instrument_id']]
  trades_by_open[(o['account_id'],o['instrument_id'])].append(t)
  require(t['trade_date']>=o['order_date'],'trade precedes order')
  require(o['known_date']<=t['known_date'],'trade consumes future order')
  require(date.fromisoformat(t['trade_date']).weekday()<5,'weekend execution')
  require(t['currency']==i['currency'],'trade currency mismatch')
  require(D(t['trade_quantity'])>0 and D(t['trade_quantity'])<=D(o['order_quantity']),'invalid fill')
  equal(t['gross_amount'],D(t['trade_quantity'])*D(t['execution_price'])*D(i['price_multiplier']),'trade gross '+t['trade_id'])
  require(len(instr_by_trade[t['trade_id']])==1,'one instruction per sample trade')
  for s in instr_by_trade[t['trade_id']]:
   equal(s['required_quantity'],t['trade_quantity'],'instruction amount')
   require(s['due_date']>=t['trade_date'],'settlement due before trade')
   require(s['currency']==t['currency'],'settlement currency mismatch')
   due=date.fromisoformat(t['trade_date']);remaining=2
   while remaining:
    due+=timedelta(days=1)
    if due.weekday()<5:remaining-=1
   require(s['due_date']==due.isoformat(),'fictional T+2 due date')
   require(events[s['instruction_id']],'missing explicit settlement state')
   total=D(0);sequence=set()
   for e in events[s['instruction_id']]:
    require(int(e['event_sequence'])>0 and e['event_sequence'] not in sequence,'duplicate event sequence');sequence.add(e['event_sequence'])
    total+=D(e['settled_quantity']);require(e['event_date']>=t['trade_date'],'settlement before trade')
    require(D(e['settled_quantity'])>=0,'negative settlement')
    require(date.fromisoformat(e['event_date']).weekday()<5,'weekend settlement event')
    require(t['known_date']<=e['known_date'],'event consumes future trade')
    if t['trade_status']==M('planned'):require(e['view_kind']==M('planned'),'actual event consumes plan')
    status=e['event_status']
    if status in (M('failed'),M('partial')):require(e['event_date']>=s['due_date'],'outcome precedes due date')
    if status in (M('failed'),M('pending')):require(D(e['settled_quantity'])==0,'failed/pending event transferred quantity')
    if status==M('partial'):require(0<D(e['settled_quantity'])<D(s['required_quantity']),'invalid partial settlement')
    if status==M('settled'):equal(total,s['required_quantity'],'settled completeness')
   require(total<=D(s['required_quantity']),'over-settlement')
  require((t['trade_status']==M('planned'))==(o['view_kind']==M('planned')),'trade plan mismatch')
  require((t['trade_date']>C['current_as_of'])==(t['trade_status']==M('planned')),'trade future knowledge leak')
 # Reconstruct all positions with exact Decimal average-cost accounting and dated settlement events.
 for p in T['positions']:
  o=by['opening_positions'][p['opening_id']];i=by['financial_instruments'][o['instrument_id']];mult=D(i['price_multiplier'])
  require(p['currency']==o['currency']==i['currency'],'position/opening currency mismatch')
  q=D(o['quantity']);sq=q;cost=q*D(o['cost_unit_price'])*mult;realized_month=D(0)
  applicable=[]
  for t in trades_by_open[(o['account_id'],o['instrument_id'])]:
   z=by['trade_orders'][t['order_id']]
   if t['trade_date']>p['as_of_date'] or t['known_date']>p['known_date']:continue
   if p['view_kind']==M('actual') and t['trade_status']==M('planned'):continue
   applicable.append(t)
  for t in sorted(applicable,key=lambda r:(r['trade_date'],r['trade_id'])):
   z=by['trade_orders'][t['order_id']];amount=D(t['trade_quantity']);sgn=1 if z['side']==M('buy') else -1
   if sgn==1:cost+=amount*D(t['execution_price'])*mult;realized=D(0)
   else:
    require(amount<=q,'oversell beyond long-only mandate');average=cost/q
    realized=amount*(D(t['execution_price'])*mult-average);cost-=amount*average
   q+=sgn*amount
   if t['trade_date'][:7]==p['as_of_date'][:7]:realized_month+=realized
   for s in instr_by_trade[t['trade_id']]:
    for e in events[s['instruction_id']]:
     if e['event_date']<=p['as_of_date'] and e['known_date']<=p['known_date'] and (p['view_kind']==M('planned') or e['view_kind']==M('actual')):sq+=sgn*D(e['settled_quantity'])
  equal(p['trade_basis_quantity'],q,'trade position '+p['position_id'],6)
  equal(p['settled_basis_quantity'],sq,'settled position '+p['position_id'],6)
  equal(p['unsettled_delta'],q-sq,'position delta '+p['position_id'],6)
  equal(p['cost_amount'],cost,'weighted average remaining cost '+p['position_id'])
  equal(p['realized_pnl'],realized_month,'monthly realized P&L '+p['position_id'])
  require(q>=0 and sq>=0,'negative long-only position')
 # Validate every price, FX and date relationship, including missing prices and blocked values.
 for v in T['valuation_snapshots']:
  p=by['positions'][v['position_id']];o=by['opening_positions'][p['opening_id']];i=by['financial_instruments'][o['instrument_id']];f=by['fx_rates'][v['fx_id']]
  require(v['as_of_date']==p['as_of_date']==f['as_of_date'],'valuation and FX dates')
  require(i['currency']==f['from_currency'] and f['to_currency']==v['currency']=='USD','FX pair')
  require(D(f['rate'])>0,'nonpositive FX')
  if f['from_currency']=='USD':equal(f['rate'],1,'self FX',6)
  price=by['market_prices'].get(v['price_id'])
  if price:
   require(price['instrument_id']==i['instrument_id'] and price['currency']==i['currency'],'wrong instrument price')
   require(price['as_of_date']==v['as_of_date'],'price snapshot mismatch')
   require(price['published_date']<=v['as_of_date'] and price['price_date']<=v['as_of_date'],'future price')
   require(D(price['price'])>0,'nonpositive price')
   reason='price_unapproved' if price['approval']!=M('approved') else 'stale' if (date.fromisoformat(v['as_of_date'])-date.fromisoformat(price['price_date'])).days>3 else 'none'
  else:
   require(not any(x['instrument_id']==i['instrument_id'] and x['as_of_date']==v['as_of_date'] for x in T['market_prices']),'missing price despite available quote')
   reason='missing'
  require(v['reason']==M(reason),'valuation reason '+v['valuation_id'])
  require(v['valuation_method']==M('bond_dirty' if i['asset_class']==M('bond') else 'equity_mark'),'valuation method')
  if reason!='none':
   require(v['valuation_status']==M('blocked'),'invalid valuation not blocked')
   require(all(v[x]=='' for x in ('market_value_local','market_value_base','unrealized_pnl_base')),'unknown price replaced by value')
  else:
   require(v['valuation_status']==M('complete'),'valid valuation blocked')
   local=quant(D(p['trade_basis_quantity'])*D(price['price'])*D(i['price_multiplier']))
   mv=quant(local*D(f['rate']));cb=quant(D(p['cost_amount'])*D(f['rate']))
   equal(v['market_value_local'],local,'local value '+v['valuation_id'])
   equal(v['market_value_base'],mv,'base value '+v['valuation_id'])
   # Cost is rounded in the position ledger before currency conversion.
   equal(v['cost_value_base'],cb,'translated cost '+v['valuation_id'])
   equal(v['unrealized_pnl_base'],mv-cb,'unrealized P&L '+v['valuation_id'])
  for row in (v,p,f):
   require((row['as_of_date']>C['current_as_of'])==(row['view_kind']==M('planned')),'view/date mismatch')
   require(row['known_date']<=('2027-02-28' if row['view_kind']==M('planned') else row['as_of_date']),'future knowledge')
  if price:require(price['view_kind']==v['view_kind'] and price['known_date']<=v['known_date'],'future/actual price mix')
 # Complete issuer denominator requires all four position valuations, not just priced positions.
 value_by_portfolio=defaultdict(list)
 for v in T['valuation_snapshots']:
  p=by['positions'][v['position_id']];op=by['opening_positions'][p['opening_id']];a=by['accounts'][op['account_id']]
  value_by_portfolio[(a['portfolio_id'],v['as_of_date'])].append(v)
 contributions=defaultdict(list)
 for c in T['exposure_contributions']:
  contributions[c['exposure_id']].append(c);v=by['valuation_snapshots'][c['valuation_id']]
  require(c['contribution_amount']==v['market_value_base'],'wrong contribution amount')
  require(c['currency']==v['currency']=='USD','contribution currency')
 for e in T['issuer_exposures']:
  vs=value_by_portfolio[(e['portfolio_id'],e['as_of_date'])]
  require(len(vs)==C['positions_per_portfolio'],'distinct portfolio positions')
  complete=all(v['valuation_status']==M('complete') for v in vs)
  require((e['exposure_status']==M('complete'))==complete,'denominator availability')
  require(all(v['known_date']<=e['known_date'] for v in vs),'issuer exposure future contributor')
  require(e['currency']=='USD','issuer exposure currency')
  expected_members={v['valuation_id'] for v in vs if by['financial_instruments'][by['opening_positions'][by['positions'][v['position_id']]['opening_id']]['instrument_id']]['issuer_id']==e['issuer_id']}
  require({c['valuation_id'] for c in contributions[e['exposure_id']]}==expected_members,'issuer contribution membership')
  if complete:
   total=sum((D(v['market_value_base']) for v in vs),D(0));amt=sum((D(c['contribution_amount']) for c in contributions[e['exposure_id']]),D(0))
   equal(e['exposure_amount'],amt,'issuer numerator');equal(e['denominator_amount'],total,'issuer denominator')
   equal(e['ratio'],amt/total,'issuer ratio',6)
  else:require(e['exposure_amount']==e['denominator_amount']==e['ratio']=='','incomplete portfolio masquerades as complete')
 # Open receivables are non-netted sells, not gross two-sided trading volumes, not regulatory CCR.
 receivable_trades=defaultdict(list);fx_by_pair={(f['from_currency'],f['as_of_date']):f for f in T['fx_rates']}
 for t in T['securities_transactions']:
  o=by['trade_orders'][t['order_id']];a=by['accounts'][o['account_id']]
  receivable_trades[(a['portfolio_id'],o['counterparty_id'])].append(t)
 for e in T['counterparty_exposures']:
  require(e['currency']=='USD','receivable currency')
  total=D(0)
  for t in receivable_trades[(e['portfolio_id'],e['counterparty_id'])]:
   o=by['trade_orders'][t['order_id']];a=by['accounts'][o['account_id']]
   if a['portfolio_id']!=e['portfolio_id'] or o['counterparty_id']!=e['counterparty_id'] or o['side']!=M('sell') or t['trade_date']>e['as_of_date'] or t['known_date']>e['known_date']:continue
   if e['view_kind']==M('actual') and t['trade_status']==M('planned'):continue
   done=sum((D(ev['settled_quantity']) for s in instr_by_trade[t['trade_id']] for ev in events[s['instruction_id']] if ev['event_date']<=e['as_of_date'] and ev['known_date']<=e['known_date'] and (e['view_kind']==M('planned') or ev['view_kind']==M('actual'))),D(0))
   i=by['financial_instruments'][o['instrument_id']]
   rates=[fx_by_pair[(i['currency'],e['as_of_date'])]]
   require(len(rates)==1,'receivable FX missing or ambiguous')
   total+=(D(t['trade_quantity'])-done)*D(t['execution_price'])*D(i['price_multiplier'])*D(rates[0]['rate'])
  equal(e['unsettled_receivable'],total,'counterparty receivable '+e['exposure_id'])
 # One applicable version per limit measure/entity/date; no hindsight.
 assessments=defaultdict(list)
 for a in T['limit_assessments']:
  l=by['mandate_limits'][a['limit_id']];assessments[(l['portfolio_id'],l['entity_id'],l['measure'],a['as_of_date'])].append(a)
  require(l['effective_from_date']<=a['as_of_date']<=l['effective_to_date'],'wrong limit validity')
  require(l['decision_date']<=a['known_date'] and l['approval']==M('approved'),'unapproved/unknown limit')
  require(l['currency']==('' if l['measure']==M('issuer_ratio') else 'USD'),'limit currency/measure')
  require(D(l['threshold'])>=0,'negative threshold')
  if l['measure']==M('issuer_ratio'):require(D(l['threshold'])<=1,'ratio threshold outside 0-1')
  if l['measure']==M('issuer_ratio'):
   require(a['issuer_exposure_id'] and not a['counterparty_exposure_id'],'issuer assessment evidence')
   e=by['issuer_exposures'][a['issuer_exposure_id']];observed=e['ratio'];entity=e['issuer_id']
  else:
   require(a['counterparty_exposure_id'] and not a['issuer_exposure_id'],'counterparty assessment evidence')
   e=by['counterparty_exposures'][a['counterparty_exposure_id']];observed=e['unsettled_receivable'];entity=e['counterparty_id']
  require(e['portfolio_id']==l['portfolio_id'] and entity==l['entity_id'],'limit scope mismatch')
  require(a['as_of_date']==e['as_of_date'] and a['view_kind']==e['view_kind'],'limit view mismatch')
  require(e['known_date']<=a['known_date'],'assessment future contributor')
  require(a['observed_value']==observed,'assessment observation')
  status=decision(observed,l['threshold'])
  require(a['assessment_status']==M(status),'assessment status')
  if observed=='':require(a['excess_value']=='','unknown excess')
  else:equal(a['excess_value'],max(D(0),D(observed)-D(l['threshold'])),'limit excess',6)
 require(all(len(v)==1 for v in assessments.values()),'overlapping limit assessments')
 for p in T['portfolios']:
  for dt in sorted({v['as_of_date'] for v in T['positions']}):
   require(sum(1 for l in T['mandate_limits'] if l['portfolio_id']==p['portfolio_id'] and l['effective_from_date']<=dt<=l['effective_to_date'])==C['limits_per_snapshot'],'limit coverage')
   require(sum(1 for l in T['limit_assessments'] if l['as_of_date']==dt and by['mandate_limits'][l['limit_id']]['portfolio_id']==p['portfolio_id'])==C['limits_per_snapshot'],'assessment coverage')
 return {'tables':len(T),'records':sum(map(len,T.values())),'relations':len(C['relations']),'positions_recomputed':len(T['positions']),'valuations_recomputed':len(T['valuation_snapshots']),'assessments_recomputed':len(T['limit_assessments'])}

def verify_model(root,T,C):
 files=list((root/'kn').rglob('*.bkn'));ids=[]
 for p in files:
  text=p.read_text(encoding='utf-8');m=re.search(r'^id: (.+)$',text,re.M);n=re.search(r'^name: (.+)$',text,re.M)
  require(m and n,'missing BKN identity '+str(p));ids.append(m[1]);require(len(m[1])<=40 and len(n[1])<=40,'identifier/name length')
  require(re.fullmatch('[a-z][a-z0-9_]*',m[1]),'BKN id syntax')
  if p.name!='network.bkn':require(p.stem==m[1],'filename/id mismatch')
 require(len(ids)==len(set(ids)),'duplicate BKN ID')
 require({p.stem for p in (root/'kn/object_types').glob('*.bkn')}==set(T),'object/table coverage')
 require({p.stem for p in (root/'kn/relation_types').glob('*.bkn')}=={r['id'] for r in C['relations']},'relation coverage')
 for t,c in C['object_types'].items():
  text=(root/'kn/object_types'/(t+'.bkn')).read_text(encoding='utf-8')
  require('Primary Keys: '+c['primary_key'] in text and 'Display Key: '+c['display_key'] in text,'BKN keys')
  fields={}
  for line in text.splitlines():
   parts=[x.strip() for x in line.strip('|').split('|')]
   if len(parts)==5 and parts[0] in c['fields']:fields[parts[0]]=parts
  require(set(fields)==set(c['fields']),'BKN properties')
  for f,typ in c['fields'].items():require(fields[f][2]==typ and fields[f][4]==f,'BKN mapped field/type')
 for r in C['relations']:
  text=(root/'kn/relation_types'/(r['id']+'.bkn')).read_text(encoding='utf-8')
  require(f'| {r["source"]} | {r["target"]} | direct |' in text,'BKN endpoints')
  require(f'| {r["source_property"]} | {r["target_property"]} |' in text,'BKN relation mapping')
 source=json.loads((root/'fibo-reference/source-lock.json').read_text(encoding='utf-8'))
 require(source['revision']==C['source_revision'],'FIBO revision')
 for name,digest in source['files'].items():require('sha256:'+hashlib.sha256((root/'fibo-reference/sources'/name).read_bytes()).hexdigest()==digest,'FIBO source digest')
 require((root/'fibo-reference/LICENSE-FIBO.txt').is_file(),'FIBO license missing')

if __name__=='__main__':
 T,C=load();verify_model(ROOT,T,C);r=verify_data(T,C,'zh-cn' in ROOT.name)
 print(json.dumps({'ok':True,**r},ensure_ascii=False))
