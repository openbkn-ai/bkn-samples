"""Independent snapshot reconciliation and adversarial controls for live-function core."""
import copy,csv,importlib.util,json,sys,unittest
from decimal import Decimal as D
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
def module(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
CORE=module(ROOT/'samples/financial-fibo-en-us/tools/post_trade.py','post_trade')
LOADER=module(ROOT/'samples/financial-fibo-en-us/tools/managed_execution.py','managed')
def load(lang):
 p=ROOT/'samples'/('financial-fibo-'+lang);c=json.loads((p/'model-contract.json').read_text());tables={}
 for t in c['object_types']:
  with (p/'data'/(t+'.csv')).open() as f:tables[t]=list(csv.DictReader(f))
 return tables,c
SCOPE=dict(portfolio_ids=['PF-001'],as_of_date='2027-02-28',knowledge_date='2027-02-28',view_kind='actual')
class Reconstruction(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.t,cls.c=load('en-us')
 def test_all_dated_positions_valuations_assessments_both_languages(self):
  counts={}
  for lang in ('en-us','zh-cn'):
   t,c=load(lang);positions={r['position_id']:r for r in t['positions']};opening={r['opening_id']:r for r in t['opening_positions']};accounts={r['account_id']:r for r in t['accounts']}
   vals={(positions[r['position_id']]['opening_id'],r['as_of_date']):r for r in t['valuation_snapshots']}
   ps={(r['opening_id'],r['as_of_date']):r for r in t['positions']};ass={}
   limits={r['limit_id']:r for r in t['mandate_limits']}
   for a in t['limit_assessments']:
    l=limits[a['limit_id']];measure={v:k for k,v in c['localized_values'].items()}.get(l['measure'],l['measure']);ass[(l['portfolio_id'],l['entity_id'],measure,a['as_of_date'])]=a
   n=0
   for dt in sorted({p['as_of_date'] for p in t['positions']}):
    scope=dict(portfolio_ids=[p['portfolio_id'] for p in t['portfolios']],as_of_date=dt,knowledge_date=min(dt,'2027-02-28'),view_kind='planned' if dt>'2027-02-28' else 'actual')
    engine=CORE.Decisions(t,c,scope)
    for r in engine.result('valuation_asof')['rows']:
     p=ps[(r['opening_id'],dt)];v=vals[(r['opening_id'],dt)]
     for key in ('trade_basis_quantity','settled_basis_quantity','unsettled_delta','cost_amount'):self.assertEqual(D(r[key]),D(p[key]),(lang,dt,r['opening_id'],key))
     self.assertEqual(D(r['realized_pnl_month']),D(p['realized_pnl']))
     for key in ('market_value_local','market_value_base','cost_value_base','unrealized_pnl_base'):
      expected=None if v[key]=='' else D(v[key]);actual=None if r[key] is None else D(r[key]);self.assertEqual(actual,expected,(lang,dt,r['opening_id'],key))
     n+=1
    for r in engine.result('limit_assessment_asof')['rows']:
     a=ass[(r['portfolio_id'],r['entity_id'],r['measure'],dt)]
     self.assertEqual(r['limit_id'],a['limit_id']);self.assertEqual(r['status_code'],engine.norm(a['assessment_status']))
     self.assertEqual(None if r['observed_value'] is None else D(r['observed_value']),None if not a['observed_value'] else D(a['observed_value']))
     self.assertEqual(r['recorded_difference'],None if r['observed_value'] is None else ('0.000000' if r['measure']=='issuer_ratio' else '0.00'))
   counts[lang]=n
  self.assertEqual(counts,{'en-us':8000,'zh-cn':8000})
 def run_changed(self,change,op='limit_assessment_asof',scope=None):
  t=copy.deepcopy(self.t);change(t);return CORE.execute(op,t,self.c,scope or SCOPE)
 def test_atomic_price_change_invalidates_cache(self):
  def change(t):next(r for r in t['market_prices'] if r['price_id']=='PX-001-4')['price']='40'
  r=self.run_changed(change);self.assertTrue(any(x['code']=='STALE_RECORDED_EXPOSURE' for x in r['issues']))
  row=next(x for x in r['rows'] if x['entity_id']=='ISS-001');self.assertNotEqual(D(row['recorded_difference']),0)
 def test_missing_price_blocks_whole_denominator(self):
  r=self.run_changed(lambda t:t.__setitem__('market_prices',[x for x in t['market_prices'] if x['price_id']!='PX-001-4']))
  self.assertTrue(all(x['observed_value'] is None for x in r['rows'] if x['measure']=='issuer_ratio'))
 def test_overlapping_limits_unknown(self):
  def change(t):r=copy.deepcopy(next(x for x in t['mandate_limits'] if x['limit_id']=='LIM-001-I1'));r['limit_id']='OTHER';t['mandate_limits'].append(r)
  r=self.run_changed(change);row=next(x for x in r['rows'] if x['entity_id']=='ISS-001');self.assertEqual((row['selection_status'],row['status_code']),('ambiguous','unknown'))
 def test_threshold_equality_and_one_quantum(self):
  observed=next(r for r in CORE.execute('limit_assessment_asof',self.t,self.c,SCOPE)['rows'] if r['entity_id']=='ISS-001')['observed_value']
  for diff,status in [(D(0),'within'),(D('.000001'),'breach')]:
   def change(t):next(x for x in t['mandate_limits'] if x['limit_id']=='LIM-001-I1')['threshold']=str(D(observed)-diff)
   row=next(x for x in self.run_changed(change)['rows'] if x['entity_id']=='ISS-001');self.assertEqual(row['status_code'],status)
 def test_missing_instruction_unknown_not_zero(self):
  def change(t):t['settlement_instructions']=[s for s in t['settlement_instructions'] if s['instruction_id']!='SI-001-1-3']
  r=self.run_changed(change);self.assertTrue(any(x['code']=='MISSING_INSTRUCTION' for x in r['issues']));self.assertIsNone(next(x for x in r['rows'] if x['measure']=='receivable_amount')['observed_value'])
 def test_oversettlement_rejected(self):
  def change(t):next(e for e in t['settlement_events'] if e['event_id']=='SE-001-1-1')['settled_quantity']='99999'
  r=self.run_changed(change,'settlement_asof');self.assertEqual(next(x for x in r['rows'] if x['instruction_id']=='SI-001-1-1')['status_code'],'unknown')
 def test_same_day_mixed_trade_order_is_ambiguous(self):
  def change(t):next(e for e in t['securities_transactions'] if e['trade_id']=='TR-001-1-3')['trade_date']='2026-11-09'
  r=self.run_changed(change,'valuation_asof');self.assertTrue(any(x['code']=='AMBIGUOUS_TRADE_ORDER' for x in r['issues']))
 def test_known_cutoff_does_not_leak(self):
  scope={**SCOPE,'knowledge_date':'2026-11-01'};r=CORE.execute('settlement_asof',self.t,self.c,scope);self.assertEqual(r['rows'],[])
 def test_zero_fx_blocks(self):
  def change(t):next(e for e in t['fx_rates'] if e['fx_id']=='FX-CNY-2027-02-28')['rate']='0'
  r=self.run_changed(change,'valuation_asof');self.assertTrue(any(x['code']=='INVALID_FX' for x in r['issues']))
 def test_loader_pagination_and_truncation(self):
  allrows=[{'id':str(n)} for n in range(10001)]
  def good(*a,**kw):return dict(datas=allrows[kw['offset']:kw['offset']+kw['limit']],total_count=10001)
  self.assertEqual(len(LOADER.fetch_rows(good,'kn','t','id','scope',['x'])),10001)
  def bad(*a,**kw):return dict(datas=allrows[:2],total_count=10001)
  with self.assertRaisesRegex(ValueError,'TRUNCATED'):LOADER.fetch_rows(bad,'kn','t','id','scope',['x'])
 def test_bulk_id_filter_avoids_expanding_hundreds_of_predicates(self):
  def query(*a,**kw):
   c=kw['condition'];leaves=c.get('sub_conditions',[c]);self.assertLessEqual(len(leaves),100)
   values=c['value'] if c['operation']=='in' else [x['value'] for x in leaves]
   rows=[{'id':x} for x in values];return {'datas':rows,'total_count':len(rows)}
  self.assertEqual(len(LOADER.fetch_rows(query,'kn','t','id','key',[str(x) for x in range(10001)])),10001)
 def test_duplicate_keys_rejected(self):
  with self.assertRaisesRegex(ValueError,'DUPLICATE'):self.run_changed(lambda t:t['market_prices'].append(dict(t['market_prices'][0])))

 def test_every_dated_bilingual_settlement_state(self):
   outputs={}
   for lang in ('en-us','zh-cn'):
    t,c=load(lang);results={}
    for dt in sorted({p['as_of_date'] for p in t['positions']}):
     scope=dict(portfolio_ids=[p['portfolio_id'] for p in t['portfolios']],as_of_date=dt,knowledge_date=min(dt,'2027-02-28'),view_kind='planned' if dt>'2027-02-28' else 'actual')
     result=CORE.execute('settlement_asof',t,c,scope)
     results[dt]={r['instruction_id']:(r['status_code'],r['settled_quantity'],r['remaining_quantity'],r['overdue']) for r in result['rows']}
    outputs[lang]=results
   self.assertEqual(sum(map(len,outputs['en-us'].values())),24000)
   self.assertEqual(outputs['en-us'],outputs['zh-cn'])
 def test_recomputed_cache_diagnostics_are_explicit_and_not_inputs(self):
   for lang in ('en-us','zh-cn'):
    t,c=load(lang)
    original=CORE.execute('valuation_asof',t,c,SCOPE)
    self.assertFalse(any(i['code'].startswith('STALE_RECORDED') for i in original['issues']))
    changed=copy.deepcopy(t)
    next(r for r in changed['market_prices'] if r['price_id']=='PX-001-4')['price']='40'
    result=CORE.execute('valuation_asof',changed,c,SCOPE)
    diagnostic=next(i for i in result['issues'] if i['code']=='STALE_RECORDED_VALUATION')
    self.assertIn('market_value_base',diagnostic['differences'])
    self.assertIn(diagnostic['valuation_id'],result['evidence']['valuation_snapshots'])
    cached_only=copy.deepcopy(t)
    next(r for r in cached_only['positions'] if r['position_id']=='POS-001-1-4')['cost_amount']='1'
    next(r for r in cached_only['valuation_snapshots'] if r['valuation_id']=='VAL-001-1-4')['market_value_base']='1'
    result=CORE.execute('valuation_asof',cached_only,c,SCOPE)
    self.assertEqual(result['rows'],original['rows'])
    self.assertTrue({'STALE_RECORDED_POSITION','STALE_RECORDED_VALUATION'} <= {i['code'] for i in result['issues']})
 def test_missing_price_does_not_erase_known_cost(self):
   t,c=load('en-us');t['market_prices']=[p for p in t['market_prices'] if p['price_id']!='PX-001-4']
   r=next(r for r in CORE.execute('valuation_asof',t,c,SCOPE)['rows'] if r['instrument_id']=='INS-001')
   self.assertEqual(r['status_code'],'blocked');self.assertIsNone(r['market_value_base'])
   self.assertIsNotNone(r['cost_value_base']);self.assertIsNotNone(r['trade_basis_quantity'])
 def test_ambiguous_quote_keeps_all_candidate_evidence(self):
   t,c=load('en-us');p=copy.deepcopy(next(r for r in t['market_prices'] if r['price_id']=='PX-001-4'));p['price_id']='DUPLICATE-QUOTE';t['market_prices'].append(p)
   result=CORE.execute('valuation_asof',t,c,SCOPE)
   self.assertTrue({'PX-001-4','DUPLICATE-QUOTE'} <= set(result['evidence']['market_prices']))
   self.assertTrue(any(i['code']=='MISSING_OR_AMBIGUOUS_PRICE' for i in result['issues']))
 def test_date_only_and_midnight_transport(self):
   self.assertEqual(CORE.day('2027-02-28T00:00:00.000Z'),'2027-02-28')
   self.assertEqual(CORE.day('2027-02-28'),'2027-02-28')
   for value in ('2027-02-28T01:00:00Z','2027-02-28trailing','2027-02-30'):
    with self.assertRaises(ValueError):CORE.day(value)
 def test_two_hundred_portfolios_complete_in_bounded_reads(self):
   for lang in ('en-us','zh-cn'):
    t,c=load(lang);calls=[]
    def query(kn,table,**kw):
     calls.append(table);cond=kw['condition'];value=cond['value'];values=set(value if cond['operation']=='in' else [value]);rows=sorted((r for r in t[table] if r[cond['field']] in values),key=lambda r:r[c['object_types'][table]['primary_key']]);return {'datas':rows[kw['offset']:kw['offset']+kw['limit']],'total_count':len(rows)}
    scope={**SCOPE,'portfolio_ids':[r['portfolio_id'] for r in t['portfolios']]}
    for operation in ('settlement_asof','valuation_asof','limit_assessment_asof'):
     calls.clear();actual=LOADER.load_sources(query,'kn',c,scope,operation)
     self.assertLessEqual(len(calls),50)
     print(lang,operation,'all200 portfolios,',len(calls),'complete source reads',flush=True)
     a,b=CORE.execute(operation,actual,c,scope),CORE.execute(operation,t,c,scope)
     for key in ('rows','issues','evidence','completeness'):self.assertEqual(a[key],b[key],(lang,operation,key))
 def test_page_truncation_still_fails(self):
   def query(*a,**k):return {'datas':[{'id':'a'}],'total_count':20000}
   with self.assertRaisesRegex(ValueError,'TRUNCATED'):LOADER.fetch_rows(query,'kn','t','id','key',['x'])
 def test_duplicate_batch_key_still_fails(self):
   def query(*a,**k):return {'datas':[{'id':'always_same'}],'total_count':1}
   with self.assertRaisesRegex(ValueError,'DUPLICATE_BATCH'):LOADER.fetch_rows(query,'kn','t','id','key',[str(n) for n in range(1001)])
if __name__=='__main__':unittest.main(verbosity=2)
