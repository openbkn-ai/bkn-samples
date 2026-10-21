"""Independent synthetic ledger counterexamples; no hidden evaluation-bank access."""
import copy,json,unittest
from pathlib import Path
from decimal import Decimal as D
from test_capabilities import CORE,load

FIXTURES=Path(__file__).with_name('fixtures')
ENUM_FIELDS={'entity_role','asset_class','unit','price_basis','mandate','branch','side','order_status','trade_status','event_status','view_kind','approval','failure_reason','measure'}
def fixture(name,lang):
 f=json.loads((FIXTURES/('synthetic-'+name+'.json')).read_text());_,c=load(lang);t=f['source']
 if lang=='zh-cn':
  for rows in t.values():
   for row in rows:
    for k,v in list(row.items()):
     if k in ENUM_FIELDS:row[k]=c['localized_values'].get(v,v)
 return f,t,c

def price_for_usd(f):
 return {'price_id':'SYN-USD-QUOTE','instrument_id':'SYN-I','as_of_date':f['scope']['as_of_date'],'price_date':f['scope']['as_of_date'],'published_date':f['scope']['knowledge_date'],'known_date':f['scope']['knowledge_date'],'price':'20','currency':'USD','approval':'approved','pricing_source':'synthetic','view_kind':'actual'}

class IndependentKnownFields(unittest.TestCase):
 def test_usd_cost_identity_without_quote_or_fixing(self):
  for lang in ('en-us','zh-cn'):
   f,t,c=fixture('usd-identity',lang);result=CORE.execute('valuation_asof',t,c,f['scope']);r=result['rows'][0]
   for k,v in f['expected_fields'].items():self.assertEqual(r[k],v,(lang,k))
   self.assertEqual(r['fx_basis'],'currency_identity');self.assertIsNone(r['fx_id']);self.assertNotIn('fx_rates',result['evidence'])
   self.assertEqual(r['reason_code'],'MISSING_OR_AMBIGUOUS_PRICE')
 def test_usd_market_value_and_exposure_without_external_fixing(self):
  for lang in ('en-us','zh-cn'):
   f,t,c=fixture('usd-identity',lang);f['scope']['knowledge_date']=f['scope']['as_of_date'];t['market_prices']=[price_for_usd(f)]
   r=CORE.execute('valuation_asof',t,c,f['scope'])['rows'][0]
   self.assertEqual((r['market_value_local'],r['market_value_base'],r['cost_value_base']),('40.00','40.00','20.00'))
   e=CORE.execute('limit_assessment_asof',t,c,f['scope'])['rows'][0];self.assertEqual(e['observed_value'],'1.000000')
 def test_supplied_invalid_identity_quote_is_not_silently_ignored(self):
  for lang in ('en-us','zh-cn'):
   f,t,c=fixture('usd-identity',lang);f['scope']['knowledge_date']=f['scope']['as_of_date'];t['market_prices']=[price_for_usd(f)]
   t['fx_rates']=[{'fx_id':'SYN-BAD-USD','as_of_date':f['scope']['as_of_date'],'from_currency':'USD','to_currency':'USD','rate':'2','known_date':f['scope']['knowledge_date'],'published_date':f['scope']['knowledge_date'],'view_kind':'actual'}]
   result=CORE.execute('valuation_asof',t,c,f['scope']);r=result['rows'][0]
   self.assertEqual((r['market_value_local'],r['market_value_base'],r['cost_value_base']),('40.00','40.00','20.00'));self.assertEqual(result['completeness'],'partial');self.assertTrue(any(i['code']=='INVALID_FX' for i in result['issues']));self.assertIsNone(r['fx_id']);self.assertEqual(r['fx_basis'],'currency_identity')
   self.assertIn('SYN-BAD-USD',result['evidence']['fx_rates'])
 def test_unordered_cost_preserves_conserved_quantities_and_market_value(self):
  for lang in ('en-us','zh-cn'):
   f,t,c=fixture('unordered-cost-known-quantity',lang);result=CORE.execute('valuation_asof',t,c,f['scope']);r=result['rows'][0]
   for k,v in f['expected_fields'].items():self.assertEqual(r[k],v,(lang,k))
   self.assertEqual(r['reason_code'],'AMBIGUOUS_TRADE_ORDER');self.assertIn('SYN-QUOTE',result['evidence']['market_prices']);self.assertIn('SYN-FX',result['evidence']['fx_rates'])
   issuer=next(x for x in CORE.execute('limit_assessment_asof',t,c,f['scope'])['rows'] if x['measure']=='issuer_ratio')
   self.assertEqual(issuer['observed_value'],'1.000000');self.assertEqual(issuer['denominator_amount'],'242.00')
 def test_missing_foreign_fx_retains_known_local_market_value(self):
  f,t,c=fixture('unordered-cost-known-quantity','en-us');t['fx_rates']=[];r=CORE.execute('valuation_asof',t,c,f['scope'])['rows'][0]
  self.assertEqual((r['trade_basis_quantity'],r['market_value_local']),('11','220.00'));self.assertIsNone(r['market_value_base']);self.assertIn('MISSING_OR_AMBIGUOUS_FX',r['reason_codes'])
 def test_unknown_settlement_does_not_erase_trade_quantity(self):
  f,t,c=fixture('unordered-cost-known-quantity','en-us');t['settlement_events'][0]['settled_quantity']='3';r=CORE.execute('valuation_asof',t,c,f['scope'])['rows'][0]
  self.assertEqual((r['trade_basis_quantity'],r['market_value_base']),('11','242.00'));self.assertIsNone(r['settled_basis_quantity']);self.assertIsNone(r['unsettled_delta'])
 def test_definite_long_only_oversell_stays_invalid(self):
  f,t,c=fixture('unordered-cost-known-quantity','en-us');t['securities_transactions'][1]['trade_quantity']='20';t['settlement_instructions'][1]['required_quantity']='20'
  r=CORE.execute('valuation_asof',t,c,f['scope'])['rows'][0];self.assertIsNone(r['trade_basis_quantity']);self.assertIsNone(r['market_value_base']);self.assertIn('LONG_ONLY_OVERSELL',r['reason_codes'])
 def test_unknown_cost_does_not_prove_recorded_cost_stale(self):
  f,t,c=fixture('unordered-cost-known-quantity','en-us');t['positions']=[{'position_id':'SYN-POS','opening_id':'SYN-OP','as_of_date':f['scope']['as_of_date'],'known_date':f['scope']['knowledge_date'],'view_kind':'actual','trade_basis_quantity':'11','settled_basis_quantity':'10','unsettled_delta':'1','cost_amount':'114','realized_pnl':'5'}]
  result=CORE.execute('valuation_asof',t,c,f['scope']);self.assertFalse(any(i['code']=='STALE_RECORDED_POSITION' for i in result['issues']))
  self.assertIn('SYN-POS',result['evidence']['positions'])

 def test_proved_zero_position_and_cost_need_no_price_or_fx(self):
  for lang in ('en-us','zh-cn'):
   f,t,c=fixture('unordered-cost-known-quantity',lang)
   for table in ('trade_orders','securities_transactions','settlement_instructions','settlement_events'):t[table]=[t[table][1]]
   t['trade_orders'][0]['order_quantity']='10';t['securities_transactions'][0]['trade_quantity']='10';t['settlement_instructions'][0]['required_quantity']='10';t['settlement_events'][0]['settled_quantity']='10';t['market_prices']=[];t['fx_rates']=[]
   result=CORE.execute('valuation_asof',t,c,f['scope']);r=result['rows'][0]
   for field in ('trade_basis_quantity','settled_basis_quantity','unsettled_delta','cost_amount','market_value_local','market_value_base','cost_value_base','unrealized_pnl_base'):self.assertEqual(D(r[field]),0,(lang,field))
   self.assertEqual(r['fx_basis'],'zero_amount');self.assertIsNone(r['price_id']);self.assertIsNone(r['fx_id'])
   self.assertTrue({'MISSING_OR_AMBIGUOUS_PRICE','MISSING_OR_AMBIGUOUS_FX'} <= {i['code'] for i in result['issues']})
   cp=next(x for x in CORE.execute('limit_assessment_asof',t,c,f['scope'])['rows'] if x['measure']=='receivable_amount');self.assertEqual(cp['observed_value'],'0.00')
 def test_zero_local_cost_remains_zero_usd_with_unknown_foreign_fx(self):
  f,t,c=fixture('usd-identity','en-us');f['scope']['knowledge_date']=f['scope']['as_of_date'];t['financial_instruments'][0]['currency']='EUR';t['opening_positions'][0].update(currency='EUR',cost_unit_price='0');t['market_prices']=[{**price_for_usd(f),'currency':'EUR'}]
  r=CORE.execute('valuation_asof',t,c,f['scope'])['rows'][0];self.assertEqual(r['cost_value_base'],'0.00');self.assertEqual(r['market_value_local'],'40.00');self.assertIsNone(r['market_value_base'])
 def test_zero_sell_obligation_does_not_require_foreign_fx(self):
  for lang in ('en-us','zh-cn'):
   f,t,c=fixture('unordered-cost-known-quantity',lang);t['fx_rates']=[]
   result=CORE.execute('limit_assessment_asof',t,c,f['scope']);cp=next(x for x in result['rows'] if x['measure']=='receivable_amount')
   self.assertEqual(cp['observed_value'],'0.00');self.assertEqual(cp['contributions'][0]['fx_basis'],'zero_amount');self.assertIsNone(cp['contributions'][0]['fx_id'])
 def test_missing_instruction_is_not_proved_zero(self):
  f,t,c=fixture('unordered-cost-known-quantity','en-us');t['fx_rates']=[];t['settlement_instructions']=t['settlement_instructions'][:1]
  result=CORE.execute('limit_assessment_asof',t,c,f['scope']);cp=next(x for x in result['rows'] if x['measure']=='receivable_amount');self.assertIsNone(cp['observed_value'])
 def test_conflicting_usd_records_do_not_change_mathematical_identity(self):
  f,t,c=fixture('usd-identity','en-us');f['scope']['knowledge_date']=f['scope']['as_of_date'];t['market_prices']=[price_for_usd(f)]
  base={'as_of_date':f['scope']['as_of_date'],'from_currency':'USD','to_currency':'USD','rate':'1','known_date':f['scope']['knowledge_date'],'published_date':f['scope']['knowledge_date'],'view_kind':'actual'}
  t['fx_rates']=[{**base,'fx_id':'SYN-USD-A'},{**base,'fx_id':'SYN-USD-B'}]
  result=CORE.execute('valuation_asof',t,c,f['scope']);r=result['rows'][0];self.assertEqual((r['market_value_base'],r['cost_value_base']),('40.00','20.00'));self.assertIsNone(r['fx_id']);self.assertTrue(any(i['code']=='MISSING_OR_AMBIGUOUS_FX' for i in result['issues']));self.assertEqual(set(result['evidence']['fx_rates']),{'SYN-USD-A','SYN-USD-B'})

if __name__=='__main__':unittest.main(verbosity=2)
