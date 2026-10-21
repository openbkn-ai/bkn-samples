"""Public typed contracts reject ambiguous ownership, enum drift and type bypasses."""
import json
import unittest
from collections import Counter
from pathlib import Path
from jsonschema import Draft202012Validator
from build_response_contracts import capability_contract, response_contract

ROOT = Path(__file__).resolve().parents[2]

class PublicResponseContracts(unittest.TestCase):
 def load(self, lang, name):
  return json.loads((ROOT / 'samples' / ('financial-fibo-' + lang) / 'bkn-eval' / name).read_text())

 def test_all_public_reference_shapes_and_split(self):
  for lang in ('en-us', 'zh-cn'):
   questions = self.load(lang, 'questions.json')
   contracts = self.load(lang, 'response-contracts.json')
   gold = self.load(lang, 'expected-results.json')
   self.assertEqual(len(questions), 100)
   self.assertEqual(Counter(q['level'] for q in questions), {'easy_basic': 30, 'intermediate': 40, 'hard_complex': 30})
   self.assertEqual(set(contracts), set(gold))
   for qid, entry in gold.items():
    schema = contracts[qid]
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    validator.validate({'rows': entry['rows']})
    fields = schema['anyOf'][0]['properties']['rows']['items']['required']
    validator.validate({'columns': fields, 'data': [[r[f] for f in fields] for r in entry['rows']]})

 def test_boolean_serializations_do_not_generalize_to_amounts(self):
  sample = ROOT / 'samples/financial-fibo-en-us'
  schema = response_contract(['is_synthetic', 'overdue', 'amount'], [{'is_synthetic':'true', 'overdue':1, 'amount':1.5}], sample, False)
  v = Draft202012Validator(schema)
  for truth in (True, False, 0, 1, 'true', 'false', None):
   v.validate({'rows':[{'is_synthetic':truth, 'overdue':truth, 'amount':'1.50'}]})
  for invalid in ('yes', 'TRUE', '1', 2):
   self.assertFalse(v.is_valid({'rows':[{'is_synthetic':invalid, 'overdue':True, 'amount':1}]}))
  for invalid in (True, False, 'true', 'false'):
   self.assertFalse(v.is_valid({'rows':[{'is_synthetic':True, 'overdue':False, 'amount':invalid}]}))

 def test_complete_native_vocabulary_even_with_empty_gold(self):
  sample = ROOT / 'samples/financial-fibo-zh-cn'
  schema = capability_contract(['side', 'status_code', 'event_ids'], [], sample, True, 'C01')
  v = Draft202012Validator(schema)
  for side in ('buy', 'sell'):
   for status in ('settled', 'pending', 'partial', 'failed', 'unknown'):
    v.validate({'rows':[{'side':side, 'status_code':status, 'event_ids':[]}]})
  self.assertFalse(v.is_valid({'rows':[{'side':'卖出', 'status_code':'partial', 'event_ids':[]}]}))
  self.assertFalse(v.is_valid({'rows':[{'side':'sell', 'status_code':'部分结算', 'event_ids':[]}]}))
  self.assertFalse(v.is_valid({'rows':[{'side':'sell', 'status_code':'partial', 'event_ids':'[]'}]}))

 def test_raw_bkn_language_enums_and_compact_enforcement(self):
  for lang, permitted, rejected in [('en-us', 'sell', '卖出'), ('zh-cn', '卖出', 'sell')]:
   sample = ROOT / 'samples' / ('financial-fibo-' + lang)
   schema = response_contract(['side'], [{'side':permitted}], sample, lang=='zh-cn', ['trade_orders'])
   v = Draft202012Validator(schema)
   v.validate({'columns':['side'], 'data':[[permitted]]})
   self.assertFalse(v.is_valid({'columns':['side'], 'data':[[rejected]]}))
   self.assertFalse(v.is_valid({'columns':['invented'], 'data':[[permitted]]}))
   self.assertFalse(v.is_valid({'columns':['side'], 'data':[[permitted, 'extra']]}))

 def test_identity_owners_source_reason_and_precision(self):
  contracts = self.load('en-us', 'response-contracts.json')
  def props(qid):return contracts[qid]['anyOf'][0]['properties']['rows']['items']['properties']
  self.assertEqual(set(props('FIN-004')), {'instrument_id','synthetic_code','scheme','instrument_name','issuer_id','issuer_name'})
  self.assertIn('manager_name', props('FIN-006'))
  self.assertNotIn('name', props('FIN-006'))
  self.assertIn('valuation_reason', props('FIN-044'))
  self.assertEqual(props('FIN-028')['due_state']['enum'], ['overdue', 'not_due', None])
  for field in ('trade_contribution', 'reconstructed_receivable'):
   self.assertEqual(props('FIN-088')[field]['x-scale'], 2)
   self.assertEqual(props('FIN-088')[field]['x-aggregation'], 'sum_unrounded_then_round')

 def test_capability_question_contracts_when_generated(self):
  for lang in ('en-us', 'zh-cn'):
   qs = self.load(lang, 'capability-questions.json')
   gold = self.load(lang, 'capability-expected.json')
   self.assertEqual(len(qs), 30)
   for q in qs:
    schema = q['response_contract']
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate({'rows':gold[q['id']]['rows']})
    self.assertEqual(schema['anyOf'][0]['properties']['rows']['items']['required'], q['requested_fields'])

if __name__ == '__main__':
 unittest.main(verbosity=2)
