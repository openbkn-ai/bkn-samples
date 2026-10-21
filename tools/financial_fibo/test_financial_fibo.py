#!/usr/bin/env python3
"""Independent negative controls and bilingual equivalence. Does not regenerate answers."""
import copy, csv, importlib.util, json, re, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
EN=ROOT/'samples/financial-fibo-en-us';ZH=ROOT/'samples/financial-fibo-zh-cn'
sys.path.insert(0,str(EN/'tools'))
from verify import load,verify_data,decision
sys.path.insert(0,str(EN/'bkn-eval'))
from run import evaluate,database,same

class HookEntrypoints(unittest.TestCase):
 def test_installer_hook_entrypoints_keep_executable_git_modes(self):
  import subprocess
  for sample in (EN,ZH):
   manifest=json.loads((sample/'sample.yaml').read_text())
   for name,relative in manifest['spec']['hooks'].items():
    path=sample/relative
    with self.subTest(sample=sample.name,hook=name):
     self.assertTrue(path.stat().st_mode & 0o111,relative+' must be directly executable')
     # The standard archive builder preserves Git index modes, not chmod alone.
     entry=subprocess.check_output(['git','ls-files','--stage','--',str(path.relative_to(ROOT))],cwd=ROOT,text=True)
     self.assertTrue(entry.startswith('100755 '),relative+' must retain executable mode in Git and release archives')

class FinancialSemantics(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.T,cls.C=load(EN)
 def mutation(self,table,key,column,value,pattern):
  data=copy.deepcopy(self.T);pk=self.C['object_types'][table]['primary_key']
  row=next(r for r in data[table] if r[pk]==key);row[column]=value
  with self.assertRaisesRegex(AssertionError,pattern):verify_data(data,self.C)
 def test_missing_relationship_endpoint(self):self.mutation('trade_orders','ORD-001-1-4','instrument_id','INS-NOT-REAL','broken relation')
 def test_issuer_role(self):self.mutation('financial_instruments','INS-001','issuer_id','CP-001','issuer role')
 def test_bond_factor(self):self.mutation('financial_instruments','INS-002','price_multiplier','1','price multiplier')
 def test_wrong_gross(self):self.mutation('securities_transactions','TR-001-1-4','gross_amount','1','trade gross')
 def test_failed_transfer(self):self.mutation('settlement_events','SE-029-2-4','settled_quantity','1','failed/pending')
 def test_partial_marked_complete(self):self.mutation('settlement_events','SE-020-2-4','event_status','settled','settled completeness')
 def test_position_quantity(self):self.mutation('positions','POS-001-1-4','trade_basis_quantity','999999','trade position')
 def test_settled_basis(self):self.mutation('positions','POS-019-2-4','settled_basis_quantity','0','settled position')
 def test_cost_basis(self):self.mutation('positions','POS-001-2-4','cost_amount','0','remaining cost')
 def test_realized_pnl(self):self.mutation('positions','POS-001-2-4','realized_pnl','99999','realized P&L')
 def test_missing_price_filled_with_zero(self):self.mutation('valuation_snapshots','VAL-037-1-4','market_value_base','0','unknown price replaced')
 def test_future_price(self):self.mutation('market_prices','PX-001-4','published_date','2027-03-01','future publication')
 def test_price_approval(self):self.mutation('market_prices','PX-001-4','approval','unapproved','valuation reason')
 def test_fx_rate(self):self.mutation('fx_rates','FX-CNY-2027-02-28','rate','1','base value')
 def test_fx_currency(self):self.mutation('fx_rates','FX-CNY-2027-02-28','from_currency','EUR','FX pair')
 def test_value(self):self.mutation('valuation_snapshots','VAL-001-1-4','market_value_base','0','base value')
 def test_pnl(self):self.mutation('valuation_snapshots','VAL-001-1-4','unrealized_pnl_base','0','unrealized P&L')
 def test_issuer_denominator(self):self.mutation('issuer_exposures','IE-001-1-4','denominator_amount','1','issuer denominator')
 def test_issuer_ratio(self):self.mutation('issuer_exposures','IE-041-1-4','ratio','0','issuer ratio')
 def test_receivable(self):self.mutation('counterparty_exposures','CE-046-4','unsettled_receivable','0','counterparty receivable')
 def test_limit_decision(self):self.mutation('limit_assessments','LA-LIM-046-C-4','assessment_status','within','assessment status')
 def test_future_limit_misapplied(self):self.mutation('mandate_limits','LIM-049-I1','effective_from_date','2027-03-15','wrong limit validity')
 def test_hindsight(self):self.mutation('positions','POS-001-1-5','known_date','2027-02-20','trade position|future contributor')
 def test_duplicate_business_key(self):
  t=copy.deepcopy(self.T);t['positions'][1]['position_id']=t['positions'][0]['position_id']
  with self.assertRaisesRegex(AssertionError,'duplicate primary key'):verify_data(t,self.C)
 def test_settlement_cannot_be_known_before_occurrence(self):self.mutation('settlement_events','SE-001-1-4','known_date','2027-02-08','known before occurrence')
 def test_trade_cannot_be_known_before_execution(self):self.mutation('securities_transactions','TR-001-1-4','known_date','2027-02-01','known before occurrence')
 def test_future_order_knowledge(self):self.mutation('trade_orders','ORD-001-1-4','known_date','2099-01-01','future knowledge')
 def test_fx_not_yet_published(self):self.mutation('fx_rates','FX-CNY-2027-02-28','published_date','2099-01-01','future publication')
 def test_wrong_position_currency(self):self.mutation('positions','POS-001-1-4','currency','EUR','currency mismatch')
 def test_future_receivable_knowledge(self):self.mutation('counterparty_exposures','CE-001-4','known_date','2099-01-01','future knowledge')
 def test_actual_snapshot_rejects_planned_event(self):self.mutation('settlement_events','SE-001-1-4','view_kind','planned','planned fact in actual interval')
 def test_quote_unit(self):self.mutation('financial_instruments','INS-002','unit','share','unit mismatch')
 def test_quote_basis(self):self.mutation('financial_instruments','INS-002','price_basis','per_share','quote basis mismatch')
 def test_unknown_price_provider(self):self.mutation('market_prices','PX-001-4','pricing_source','missing_provider','unknown pricing source')
 def test_future_assessment_knowledge(self):self.mutation('limit_assessments','LA-LIM-049-I1-NEXT-5','known_date','2099-01-01','future knowledge')
 def test_future_issuer_knowledge(self):self.mutation('issuer_exposures','IE-001-1-5','known_date','2099-01-01','future knowledge')
 def test_weekend_execution(self):
  t=copy.deepcopy(self.T);row=next(x for x in t['securities_transactions'] if x['trade_id']=='TR-001-1-4')
  row['trade_date']=row['known_date']='2027-02-21'
  with self.assertRaisesRegex(AssertionError,'weekend execution'):verify_data(t,self.C)
 def test_weekend_quote(self):self.mutation('market_prices','PX-001-4','price_date','2027-02-28','weekend market quote')
 def test_same_fixing_weekend_carry(self):
  from collections import defaultdict
  seen=defaultdict(set)
  for f in self.T['fx_rates']:seen[(f['from_currency'],f['published_date'])].add(f['rate'])
  self.assertTrue(all(len(v)==1 for v in seen.values()))
 def test_strict_threshold_boundary(self):
  for threshold,step in [('500.00','0.01'),('0.300000','0.000001')]:
   from decimal import Decimal as D
   self.assertEqual(decision(threshold,threshold),'within')
   self.assertEqual(decision(str(D(threshold)-D(step)),threshold),'within')
   self.assertEqual(decision(str(D(threshold)+D(step)),threshold),'breach')
   self.assertEqual(decision('',threshold),'unknown')
 def test_actual_price_paths_have_gains_and_losses(self):
  for field,table in [('realized_pnl','positions'),('unrealized_pnl_base','valuation_snapshots')]:
   vals=[float(r[field]) for r in self.T[table] if r[field] and r['view_kind']=='actual']
   self.assertLess(min(vals),0);self.assertGreater(max(vals),0)
 def test_duplicate_incremental_transfer_rejected(self):
  t=copy.deepcopy(self.T);row=copy.deepcopy(next(r for r in t['settlement_events'] if r['event_id']=='SE-001-1-4'))
  row['event_id']='DUPLICATE-TRANSFER';row['event_sequence']='3';t['settlement_events'].append(row)
  with self.assertRaisesRegex(AssertionError,'settled completeness|over-settlement'):verify_data(t,self.C)
 def test_current_rollup_excludes_future_recovery(self):
  db=database(self.T,self.C)
  r=dict(db.execute("SELECT * FROM settlement_state WHERE instruction_id='SI-020-2-4'").fetchone())
  self.assertEqual(r['event_status'],'partial')
  raw=[x for x in self.T['settlement_events'] if x['instruction_id']=='SI-020-2-4']
  self.assertTrue(any(x['view_kind']=='planned' and x['event_status']=='settled' for x in raw))
  self.assertEqual(r['settled_quantity'],float(next(x['settled_quantity'] for x in raw if x['event_id']=='SE-020-2-4')))
  db.close()
 def test_projected_normal_settlement_and_recovery(self):
  row=next(x for x in self.T['counterparty_exposures'] if x['exposure_id']=='CE-001-5')
  self.assertEqual(float(row['unsettled_receivable']),0)
  partial=next(x for x in self.T['positions'] if x['position_id']=='POS-019-2-5')
  self.assertEqual(float(partial['unsettled_delta']),0)
 def test_monthly_trade_count_not_event_count(self):
  from collections import Counter
  db=database(self.T,self.C)
  q=json.loads((EN/'bkn-eval/questions.json').read_text())[19]
  result=[dict(r) for r in db.execute(q['evidence_sql'])];actual=sum(x['trades'] for x in result)
  self.assertEqual(actual,len(self.T['securities_transactions']))
  self.assertGreater(len(self.T['settlement_events']),actual)
  db.close()
 def test_issuer_audit_counts_null_role(self):
  t=copy.deepcopy(self.T);t['legal_entities']=[r for r in t['legal_entities'] if r['entity_id']!='ISS-001']
  db=database(t,self.C);q=json.loads((EN/'bkn-eval/questions.json').read_text())[8]
  row=dict(db.execute(q['evidence_sql']).fetchone());self.assertEqual(row['identity_exceptions'],2);db.close()
 def test_realized_loss_independent_anchor(self):
  from decimal import Decimal as D, ROUND_HALF_UP
  # Opening: 3426*21 CNY; earlier buys: 5219 CNY / 255 shares; sale: 85 at 19.40 CNY.
  expected=(D(85)*(D('19.40')-(D(3426)*21+D(5219))/(D(3426)+255))).quantize(D('.01'),rounding=ROUND_HALF_UP)
  self.assertEqual(str(expected),'-132.86')
  a=json.loads((EN/'bkn-eval/expected-results.json').read_text());self.assertEqual(str(a['FIN-070']['rows'][0]['reconstructed_realized_pnl']),str(expected))
 def test_repeated_acknowledgement_does_not_double_trade(self):
  t=copy.deepcopy(self.T);ack=copy.deepcopy(next(x for x in t['settlement_events'] if x['event_id']=='ACK-001-1-4'))
  ack['event_id']='REDUNDANT-ACK';ack['event_sequence']='2';t['settlement_events'].append(ack)
  next(x for x in t['settlement_events'] if x['event_id']=='SE-001-1-4')['event_sequence']='3'
  verify_data(t,self.C)
  db=database(t,self.C);q=json.loads((EN/'bkn-eval/questions.json').read_text())[19]
  self.assertEqual(sum(r['trades'] for r in db.execute(q['evidence_sql'])),8000);db.close()
 def test_explanations_are_business_answers(self):
  for sample in (EN,ZH):
   q=json.loads((sample/'bkn-eval/questions.json').read_text());a=json.loads((sample/'bkn-eval/expected-results.json').read_text())
   self.assertTrue(all(a[x['id']]['explanation']!=x['question'] for x in q))
   self.assertTrue(all(len(a[x['id']]['explanation'])>40 for x in q))
 def test_frozen_business_controls(self):
  a=json.loads((EN/'bkn-eval/expected-results.json').read_text())
  self.assertEqual(a['FIN-089']['rows'][0]['breached_limits'],12)
  self.assertGreater(a['FIN-089']['rows'][0]['excess_usd'],0)
  self.assertEqual(a['FIN-099']['rows'],[{'as_of_date':'2027-02-28','view_kind':'actual','assessment_status':'within','assessments':32},{'as_of_date':'2027-03-31','view_kind':'planned','assessment_status':'breach','assessments':32}])
  self.assertTrue(all(x['invalid_limit_uses']==0 for x in a['FIN-100']['rows']))
 def test_sql_is_read_only(self):
  db=database(self.T,self.C)
  with self.assertRaises(Exception):db.execute('DELETE FROM positions')
  db.close()
 def test_null_is_not_zero(self):self.assertFalse(same([{'amount':None}],[{'amount':0}],0.000001))
 def test_bilingual_equivalence(self):
  other,c=load(ZH);mapping=c['localized_values']
  semantic_names={'name','country','sector'}
  for table,rows in self.T.items():
   pk=self.C['object_types'][table]['primary_key'];target={r[pk]:r for r in other[table]}
   self.assertEqual({r[pk] for r in rows},set(target))
   for row in rows:
    z=target[row[pk]]
    for f,v in row.items():
     if f in semantic_names:
      self.assertRegex(z[f],r'[\u4e00-\u9fff]')
     else:self.assertEqual(z[f],mapping.get(v,v),(table,row[pk],f))
  q1=json.loads((EN/'bkn-eval/questions.json').read_text());q2=json.loads((ZH/'bkn-eval/questions.json').read_text())
  self.assertEqual([q['id'] for q in q1],[q['id'] for q in q2])
  for a,b in zip(q1,q2):
   self.assertEqual(a['scenario_id'],b['scenario_id']);self.assertEqual(a['level'],b['level']);self.assertEqual(a['required_relations'],b['required_relations'])
   sql=a['evidence_sql']
   for x,y in mapping.items():sql=sql.replace("'"+x+"'","'"+y+"'")
   self.assertEqual(sql,b['evidence_sql'])
   self.assertRegex(b['question'],r'[\u4e00-\u9fff]')
 def test_full_english_bank(self):self.assertEqual(evaluate(EN)['questions_passed'],100)
 def test_full_chinese_bank(self):self.assertEqual(evaluate(ZH)['questions_passed'],100)


class ReferenceRepairControls(unittest.TestCase):
 def test_half_cent_financial_rounding(self):
  import sqlite3
  from decimal_sql import register
  db=sqlite3.connect(':memory:');register(db)
  for a,b,expected in [('10275.00','1.073',11025.08),('-10275.00','1.073',-11025.08),('1.005','1',1.01),('-1.005','1',-1.01)]:
   self.assertEqual(db.execute('SELECT DROUND(DMUL(?,?),2)',(a,b)).fetchone()[0],expected)
  self.assertIsNone(db.execute('SELECT DROUND(DMUL(NULL,1),2)').fetchone()[0]);db.close()
 def test_grouped_translation_rounds_after_sum(self):
  import sqlite3
  from decimal_sql import register
  db=sqlite3.connect(':memory:');register(db)
  db.execute('CREATE TABLE x(a TEXT,b TEXT)');db.executemany('INSERT INTO x VALUES (?,?)',[('1.005','1'),('1.005','1')])
  self.assertEqual(db.execute('SELECT DROUND(DSUM_PRODUCT(a,b),2) FROM x').fetchone()[0],2.01);db.close()
 def test_recorded_money_basis_and_local_monthly_scope(self):
  from decimal import Decimal,ROUND_HALF_UP
  # Booking each contract and translating a booked contract are distinct rounding stages.
  booked=sum(Decimal('1.005').quantize(Decimal('.01'),rounding=ROUND_HALF_UP) for _ in range(2))
  raw_sum=sum(Decimal('1.005') for _ in range(2)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
  self.assertEqual(booked,Decimal('2.02'));self.assertEqual(raw_sum,Decimal('2.01'))
  for root in (EN,ZH):
   qs={q['id']:q for q in json.loads((root/'bkn-eval/questions.json').read_text())}
   self.assertIn('gross_amount',qs['FIN-019']['question'])
   for qid in ['FIN-040','FIN-060']:
    self.assertTrue('history' in qs[qid]['question'] or '历史' in qs[qid]['question'])
   self.assertTrue('local currency' in qs['FIN-020']['question'] or '同一本币' in qs['FIN-020']['question'])
   self.assertTrue('cohort' in qs['FIN-020']['question'] or '队列' in qs['FIN-020']['question'])
 def test_breach_lists_and_named_future_limit_are_complete(self):
  for root in (EN,ZH):
   qs={q['id']:q for q in json.loads((root/'bkn-eval/questions.json').read_text())};gold=json.loads((root/'bkn-eval/expected-results.json').read_text())
   status='超限' if root==ZH else 'breach'
   self.assertTrue(all(r['assessment_status']==status for r in gold['FIN-076']['rows']))
   self.assertEqual(len(gold['FIN-089']['rows']),12)
   self.assertEqual(len({r['limit_id'] for r in gold['FIN-089']['rows']}),12)
   self.assertTrue(all(r['breached_limits']==12 for r in gold['FIN-089']['rows']))
   self.assertIn('LIM-049-I1',qs['FIN-091']['question'])
 def test_expanded_cardinalities_and_explicit_cohorts(self):
  for root in (EN,ZH):
   qs={q['id']:q for q in json.loads((root/'bkn-eval/questions.json').read_text())};gold=json.loads((root/'bkn-eval/expected-results.json').read_text())
   self.assertNotIn('four actual',qs['FIN-015']['question']);self.assertNotIn('四笔',qs['FIN-015']['question']);self.assertEqual(len(gold['FIN-015']['rows']),8)
   self.assertTrue('February' in qs['FIN-027']['question'] or '二月' in qs['FIN-027']['question'])
   self.assertIn('POS-001-2-4',qs['FIN-036']['question']);self.assertIn('POS-029-2-4',qs['FIN-036']['question'])
   self.assertTrue(all(r['issuers']==4 for r in gold['FIN-079']['rows']));self.assertNotIn('two issuer',qs['FIN-079']['question']);self.assertNotIn('两项发行方',qs['FIN-079']['question'])
   self.assertNotIn('two future',qs['FIN-099']['question']);self.assertNotIn('两个未来',qs['FIN-099']['question'])
   self.assertEqual(gold['FIN-055']['rows'][0]['reconstructed_base'],11025.08)
 def test_receivable_limit_scope_excludes_issuer_concentration(self):
  for root in (EN,ZH):
   qs={q['id']:q for q in json.loads((root/'bkn-eval/questions.json').read_text())};gold=json.loads((root/'bkn-eval/expected-results.json').read_text())
   self.assertIn('未结算应收金额限额' if root==ZH else 'receivable limits',qs['FIN-090']['question'])
   self.assertEqual(sum(r['breached_limits'] for r in gold['FIN-090']['rows']),12)
   import csv
   rows=list(csv.DictReader((root/'data/limit_assessments.csv').open()))
   breach='超限' if root==ZH else 'breach';actual='实际' if root==ZH else 'actual'
   current=[r for r in rows if r['as_of_date']=='2027-02-28' and r['view_kind']==actual and r['assessment_status']==breach]
   self.assertEqual(len(current),32)
   self.assertEqual(sum(bool(r['counterparty_exposure_id']) for r in current),12)
 def test_live_model_contract_has_rules_and_localized_states(self):
  for root in (EN,ZH):
   text=(root/'kn/network.bkn').read_text();self.assertIn('known_date',text);self.assertIn('Decimal',text)
   text=(root/'kn/object_types/trade_orders.bkn').read_text();self.assertIn('实际' if root==ZH else 'actual',text)

if __name__=='__main__':unittest.main(verbosity=2)
