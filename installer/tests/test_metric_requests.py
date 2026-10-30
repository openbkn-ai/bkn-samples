"""Keep runtime requests distinct from published metric capability definitions."""
import json
import unittest
from pathlib import Path
from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / 'tools/contracts/object-metrics-v1/query_metric.json').read_text())['input_schema']


class MetricRequestsTest(unittest.TestCase):
    def test_bilingual_queries_match_upstream_schema_and_model_types(self):
        for sample in ('supply_ontology_en',):
            root = ROOT / 'samples' / sample
            network = json.loads((root / 'kn' / (sample + '.json')).read_text())
            objects = network.get('object_types') or network.get('objectTypes') or network['entries'][0]['object_types']
            types = {(o['id'], p['name']): p['type'] for o in objects for p in o['data_properties']}
            definitions = json.loads((root / 'tools/assets/metrics-create.json').read_text())['entries']
            definitions = {m['name']: m for m in definitions}
            for filename in ('metrics-query-examples.json', 'metrics-analysis-examples.json'):
                for case in json.loads((root / 'tools/assets' / filename).read_text())['cases']:
                    metric = definitions[case['metric_name']]
                    allowed = metric['query_capabilities']['analysis_dimensions'] + metric['query_capabilities']['time_dimensions']
                    bodies = [case['body']] if 'body' in case else [q['body'] for q in case.get('queries', [])]
                    for body in bodies:
                        with self.subTest(sample=sample, case=case['id']):
                            Draft7Validator(SCHEMA).validate({'kn_id': sample, 'metric_id': 'resolved-id', 'version': metric['version'], 'query': body})
                            self.check_types(body, types, allowed)

    def check_types(self, value, types, allowed):
        if isinstance(value, dict):
            if value.get('source') == 'property':
                ref = value['property_ref']
                self.assertIn(ref, allowed)
                self.assertIn((ref['object_type_id'], ref['property_name']), types)
            left = value.get('left', {}).get('property_ref')
            if left and types[(left['object_type_id'], left['property_name'])] == 'date':
                for operand in value.get('right', []):
                    self.assertEqual(operand['value_type'], 'date')
                    from datetime import date
                    date.fromisoformat(operand['value'])
            for ref in value.get('group_by', []):
                self.assertIn(ref, allowed)
            for child in value.values():
                self.check_types(child, types, allowed)
        elif isinstance(value, list):
            for child in value:
                self.check_types(child, types, allowed)

    def test_upstream_schema_rejects_old_runtime_field_but_definitions_keep_it(self):
        bad = {'kn_id': 'network', 'metric_id': 'metric', 'version': 1, 'query': {'analysis_dimensions': []}}
        self.assertTrue(list(Draft7Validator(SCHEMA).iter_errors(bad)))
        for sample in ('supply_ontology_en',):
            metrics = json.loads((ROOT / 'samples' / sample / 'tools/assets/metrics-create.json').read_text())['entries']
            self.assertTrue(all('analysis_dimensions' in m['query_capabilities'] for m in metrics))


if __name__ == '__main__':
    unittest.main()
