"""Regress the SDK representation defect exposed by the real 8081 first pass."""
import copy
import csv
import json
import unittest
from decimal import Decimal
from pathlib import Path
from retail_core import execute, event_payload

ROOT = Path(__file__).resolve().parents[2]


class RuntimeAdapterTest(unittest.TestCase):
    def fixture(self, lang):
        sample = ROOT / 'samples' / ('retail-gs1-' + lang)
        contract = json.loads((sample / 'model-contract.json').read_text())
        tables = {}
        for path in (sample / 'data').glob('*.csv'):
            with path.open() as source:
                tables[path.stem] = list(csv.DictReader(source))
        for row in tables['movements']:
            row.update(_instance_id='movements-' + row['movement_id'],
                       _instance_identity={'movement_id': row['movement_id']},
                       _display=row['movement_id'])
            for field in ('source_location_id', 'destination_location_id', 'order_id', 'transfer_id', 'reversal_of'):
                row[field] = row[field] or None
            for field in ('event_date', 'recorded_date'):
                row[field] += 'T00:00:00+08:00'
        return tables, contract

    def run_inventory(self, tables, contract, product):
        return execute('inventory_asof', tables, contract,
                       dict(product_ids=[product], as_of_date='2027-02-28', knowledge_date='2027-02-28'))

    def test_duplicate_is_ignored_despite_distinct_sdk_record_metadata(self):
        for lang in ('en-us', 'zh-cn'):
            with self.subTest(lang=lang):
                tables, contract = self.fixture(lang)
                result = self.run_inventory(tables, contract, 'PRD-042')
                row = next(r for r in result['rows'] if (r['lot_id'], r['location_id']) == ('LOT-042-C', 'STORE-017'))
                self.assertEqual((row['on_hand'], row['sold'], row['returned'], row['available']),
                                 ('28.000000', '12.000000', '3.000000', '23.000000'))
                self.assertTrue(any(i['code'] == 'DUPLICATE_EVENT_IGNORED' and i['ref_id'] == 'EV-00875' for i in result['issues']))
                self.assertFalse(any(i['code'] == 'CONFLICTING_EVENT' and i['ref_id'] == 'EV-00875' for i in result['issues']))

    def test_changed_business_quantity_is_still_a_conflict(self):
        tables, contract = self.fixture('en-us')
        duplicate = next(r for r in tables['movements'] if r['movement_id'] == 'MOV-00877')
        duplicate['quantity'] = '13'
        result = self.run_inventory(tables, contract, 'PRD-042')
        row = next(r for r in result['rows'] if (r['lot_id'], r['location_id']) == ('LOT-042-C', 'STORE-017'))
        self.assertIsNone(row['on_hand'])
        self.assertTrue(any(i['code'] == 'CONFLICTING_EVENT' and i['ref_id'] == 'EV-00875' for i in result['issues']))

    def test_equivalent_payload_types_and_days_do_not_create_conflicts(self):
        tables, _ = self.fixture('en-us')
        row = copy.deepcopy(next(r for r in tables['movements'] if r['movement_id'] == 'MOV-00875'))
        other = dict(row, movement_id='other', _display='other', event_date='2027-02-24',
                     event_sequence='40.000000', quantity=str(Decimal(row['quantity']).quantize(Decimal('.000001'))), destination_location_id='')
        self.assertEqual(event_payload(row), event_payload(other))


if __name__ == '__main__':
    unittest.main()
