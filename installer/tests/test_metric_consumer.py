import copy
import io
import json
import unittest
from decimal import Decimal
from pathlib import Path
from tools.metric_consumer import metric_result, query_all, participants_all
from installer.tests.test_metric_requests import SCHEMA
from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ('supply_ontology_hand', 'supply_ontology_en', 'financial-fibo-zh-cn',
           'financial-fibo-en-us', 'retail-gs1-zh-cn', 'retail-gs1-en-us')
ARGS = {'kn_id': 'network', 'metric_id': 'metric', 'version': 1, 'query': {'page_size': 1}}


def result(status='ok', cursor=None):
    return {'kn_id': 'network', 'metric_id': 'metric', 'version': 1, 'status': status,
            'model': {'unit': {'code': 'USD'}}, 'entries': [{'status': 'ok', 'value': 9007199254740993,
            'display_value': '9007199254740993.01'}], 'total_count': 2 if cursor else 1,
            **({'next_cursor': cursor} if cursor else {})}


class MetricConsumerTest(unittest.TestCase):
    def test_every_pack_contains_identical_consumer_and_valid_query_examples(self):
        for sample in SAMPLES:
            root = ROOT / 'samples' / sample
            self.assertEqual((root / 'tools/metric_consumer.py').read_bytes(), (ROOT / 'tools/metric_consumer.py').read_bytes())
            examples = json.loads((root / 'tools/assets/metrics-consumption-examples.json').read_text())
            for case in examples['cases']:
                Draft7Validator(SCHEMA).validate({**ARGS, 'query': case['query']})

    def test_exact_display_and_unit_preserved_and_unknown_is_not_zero(self):
        payload = result()
        normalized = metric_result(payload, metric_id='metric', version=1)
        self.assertEqual(normalized['rows'][0]['display_value'], '9007199254740993.01')
        self.assertEqual(normalized['model'], payload['model'])
        payload.update(status='no_data', entries=[], total_count=0)
        self.assertTrue(metric_result(payload, metric_id='metric', version=1)['complete'])
        self.assertEqual(payload['entries'], [])

    def test_partial_warnings_unavailable_and_pages_are_not_complete_success(self):
        for status in ('partial', 'unavailable'):
            self.assertFalse(metric_result(result(status), metric_id='metric', version=1)['complete'])
        for update in ({'warnings': ['truncated']}, {'next_cursor': 'opaque', 'total_count': 2}):
            payload = result();payload.update(update)
            self.assertFalse(metric_result(payload, metric_id='metric', version=1)['complete'])
        with self.assertRaises(ValueError):
            metric_result(result(), metric_id='other', version=1)

    def test_paging_preserves_scope_and_checks_complete_count(self):
        requests = []
        def call(tool, arguments):
            requests.append(copy.deepcopy(arguments))
            payload = result(cursor='opaque-server-cursor') if len(requests) == 1 else result()
            payload['total_count'] = 2
            return payload
        report = query_all(call, ARGS)
        self.assertTrue(report['complete'])
        self.assertEqual(report['rows'][1]['source_query'], {'page_size': 1, 'cursor': 'opaque-server-cursor'})
        self.assertEqual(requests[1]['query'], {'page_size': 1, 'cursor': 'opaque-server-cursor'})
        self.assertNotIn('cursor', ARGS['query'])
        with self.assertRaises(ValueError):
            query_all(lambda *_: result(cursor='repeated'), ARGS)
        payload = result();payload['total_count'] = 5
        with self.assertRaises(ValueError):
            query_all(lambda *_: payload, ARGS)

    def test_participants_keep_opaque_bucket_and_original_query(self):
        requests = []
        entry = {'bucket_key': 'server-bucket', 'available_actions': ['participants'], 'source_query': {'page_size': 1, 'cursor': 'server-page'}}
        def call(tool, arguments):
            self.assertEqual(tool, 'drill_through_metric');requests.append(copy.deepcopy(arguments))
            return {'kn_id': 'network', 'metric_id': 'metric', 'version': 1, 'status': 'partial',
                    'participants': [{'instance_identity': {'id': 'one'}, 'role': 'owner'}],
                    'warnings': ['limit'], 'bucket_value': '12', 'evaluated_at': 123}
        self.assertFalse(participants_all(call, ARGS, entry)['complete'])
        self.assertEqual(requests[0]['query'], entry['source_query'])
        self.assertEqual(requests[0]['bucket_key'], entry['bucket_key'])
        with self.assertRaises(ValueError):
            participants_all(call, ARGS, {})

class MetricExampleOracleTest(unittest.TestCase):
    def test_examples_match_locked_csv_without_running_runtime_functions(self):
        import csv
        fields = {'issuer_ratio_recorded': 'ratio', 'sell_receivable_recorded_usd': 'unsettled_receivable',
                  'recorded_available_quantity': 'available', 'recorded_recall_coverage': 'coverage_ratio'}
        for sample in SAMPLES:
            root = ROOT / 'samples' / sample
            document = json.loads((root / 'tools/assets/metrics-consumption-examples.json').read_text())
            if sample.startswith('supply'):
                totals = {}
                for row in csv.DictReader(io.StringIO((root / 'data/erp_real_time_inventory.csv').read_text())):
                    totals[row['warehouse']] = totals.get(row['warehouse'], Decimal(0)) + Decimal(row['available_inventory_qty'] or '0')
                self.assertEqual(Decimal(document['cases'][0]['expected_values'][0]), sum(totals.values()))
                top = sorted(totals.items(), key=lambda item: (-item[1], item[0]))[:5]
                self.assertEqual([(r['warehouse'], Decimal(r['display_value'])) for r in document['cases'][1]['expected_rows']], top)
                self.assertEqual(document['cases'][1]['expected_total_count'], len(totals))
            else:
                for case in document['cases']:
                    identity = case['query']['instance_identities'][0]
                    rows = list(csv.DictReader(io.StringIO((root / 'data' / (case['owner_object_type_id'] + '.csv')).read_text())))
                    matches = [r for r in rows if all(r[k] == v for k, v in identity.items())]
                    self.assertEqual(len(matches), 1)
                    row = matches[0]
                    self.assertEqual(Decimal(case['expected_value']), Decimal(row[fields[case['metric_code']]]))
                    self.assertTrue(all(row[k] == v for k, v in case['snapshot_evidence'].items()))


if __name__ == '__main__':
    unittest.main()
