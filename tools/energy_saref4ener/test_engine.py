"""Small hand-built boundary cases, independent of sample answer banks."""
import copy
import json
from pathlib import Path
import unittest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import execute

CONTRACT = json.loads(Path(__file__).with_name('contract.json').read_text())
SCOPE = {'event_ids': ['e1'], 'as_of_date': '2027-02-28', 'knowledge_date': '2027-02-28'}


def fixture():
    tables = {key: [] for key in CONTRACT['object_types']}
    tables['sites'] = [{'site_id': 's1', 'response_cap_kw': '10'}]
    tables['devices'] = [{'device_id': 'd1', 'site_id': 's1', 'max_reduction_kw': '10', 'min_service_kw': '2', 'status_code': 'active'}]
    tables['meters'] = [{'meter_id': 'm1', 'device_id': 'd1', 'unit_code': 'kWh'}]
    for i in (1, 2):
        tables['response_events'].append({'event_id': f'e{i}', 'response_date': '2027-02-01', 'block_code': 'peak_a', 'duration_hours': '2', 'target_kw': '8', 'priority': str(i), 'reward_cny_kwh': '1.005', 'minimum_ratio': '0.5', 'status_code': 'active', 'announced_date': '2027-01-01', 'known_date': '2027-01-01'})
        tables['flexibility_offers'].append({'offer_id': f'o{i}', 'event_id': f'e{i}', 'device_id': 'd1', 'offered_kw': '10', 'cost_cny_kwh': '0.5025', 'status_code': 'active', 'valid_from': '2027-01-01', 'valid_to': '2027-03-31', 'revision': '1', 'known_date': '2027-01-01'})
    tables['load_forecasts'] = [{'forecast_id': 'f1', 'device_id': 'd1', 'response_date': '2027-02-01', 'block_code': 'peak_a', 'forecast_kw': '12', 'quality_code': 'valid', 'revision': '1', 'known_date': '2027-01-01'}]
    tables['baselines'] = [{'baseline_id': 'b1', 'device_id': 'd1', 'response_date': '2027-02-01', 'block_code': 'peak_a', 'baseline_kw': '12', 'quality_code': 'approved', 'revision': '1', 'known_date': '2027-01-01'}]
    tables['meter_readings'] = [{'reading_id': 'r1', 'meter_id': 'm1', 'response_date': '2027-02-01', 'block_code': 'peak_a', 'actual_kwh': '14', 'duration_hours': '2', 'quality_code': 'valid', 'revision': '1', 'known_date': '2027-02-02'}]
    return tables


def allocations(tables):
    for i in (1, 2):
        tables['dispatch_allocations'].append({'allocation_id': f'a{i}', 'event_id': f'e{i}', 'device_id': 'd1', 'committed_kw': '5', 'status_code': 'committed', 'known_date': '2027-01-01'})
        tables['execution_logs'].append({'execution_id': f'x{i}', 'allocation_id': f'a{i}', 'response_date': '2027-02-01', 'status_code': 'completed', 'revision': '1', 'known_date': '2027-02-02'})


class Boundaries(unittest.TestCase):
    def run_op(self, operation, tables, scope=None):
        return execute(operation, tables, CONTRACT, scope or SCOPE)

    def test_scope_validated_before_table_access(self):
        class Poison(dict):
            def get(self, *args):
                raise AssertionError('source accessed')
        for value in ([], ['e1']*2, ['e1']*21):
            with self.assertRaises(ValueError):
                self.run_op('dispatch_plan', Poison(), {**SCOPE, 'event_ids': value})
        with self.assertRaises(ValueError):
            self.run_op('dispatch_plan', Poison(), {**SCOPE, 'as_of_date': '2027-2-28'})

    def test_blocked_needs_no_forecast(self):
        t = fixture()
        t['load_forecasts'] = []
        t['device_constraints'] = [{'constraint_id': 'c1', 'device_id': 'd1', 'block_code': 'peak_a', 'effective_from': '2027-01-01', 'effective_to': '2027-03-01', 'constraint_type_code': 'block'}]
        result = self.run_op('flexibility_assessment', t)
        self.assertEqual(result['rows'][0]['eligible_kw'], '0.000000')
        self.assertEqual(result['completeness'], 'complete')
        t['device_constraints'] = []
        self.assertIsNone(self.run_op('flexibility_assessment', t)['rows'][0]['eligible_kw'])

    def test_unknown_first_site_keeps_later_site_evidence_and_issues(self):
        t = fixture()
        for i in (2, 3):
            t['sites'].append({'site_id': f's{i}', 'response_cap_kw': '10' if i == 2 else ''})
            t['devices'].append({**t['devices'][0], 'device_id': f'd{i}', 'site_id': f's{i}'})
            t['flexibility_offers'].append({**t['flexibility_offers'][0], 'offer_id': f'o-extra-{i}', 'device_id': f'd{i}'})
            t['load_forecasts'].append({**t['load_forecasts'][0], 'forecast_id': f'f{i}', 'device_id': f'd{i}'})
            t['baselines'].append({**t['baselines'][0], 'baseline_id': f'b{i}', 'device_id': f'd{i}'})
        # The first site has unknown device capacity; the last has an unknown site cap.
        t['load_forecasts'] = [r for r in t['load_forecasts'] if r['device_id'] != 'd1']
        result = self.run_op('flexibility_assessment', t)
        self.assertIsNone(result['rows'][0]['eligible_kw'])
        self.assertIsNone(result['rows'][0]['shortfall_kw'])
        self.assertEqual(result['rows'][0]['status_code'], 'unknown')
        self.assertEqual(result['completeness'], 'partial')
        self.assertEqual(result['evidence']['sites'], ['s1', 's2', 's3'])
        unknown_sites = {source for issue in result['issues'] if issue['code'] == 'unknown_site_capacity' for source in issue['source_ids']}
        self.assertEqual(unknown_sites, {'s1', 's3'})
        self.assertEqual(next(row for row in result['device_rows'] if row['device_id'] == 'd2')['eligible_kw'], '10.000000')

    def test_cutoff_and_latest_conflict_and_retry(self):
        t = fixture()
        late = {**t['load_forecasts'][0], 'forecast_id': 'f2', 'revision': '2', 'forecast_kw': '3', 'known_date': '2027-03-01'}
        t['load_forecasts'].append(late)
        self.assertEqual(self.run_op('flexibility_assessment', t)['rows'][0]['eligible_kw'], '10.000000')
        late['known_date'] = '2027-02-01'
        retry = {**late, 'forecast_id': 'f3'}
        t['load_forecasts'].append(retry)
        self.assertEqual(self.run_op('flexibility_assessment', t)['rows'][0]['eligible_kw'], '1.000000')
        retry['forecast_kw'] = '4'
        self.assertIsNone(self.run_op('flexibility_assessment', t)['rows'][0]['eligible_kw'])

    def test_subset_does_not_reuse_competing_capacity(self):
        t = fixture()
        result = self.run_op('dispatch_plan', t, {**SCOPE, 'event_ids': ['e2']})
        self.assertEqual(result['rows'][0]['new_kw'], '2.000000')
        allocations(t)
        result = self.run_op('dispatch_plan', t)
        self.assertEqual(result['rows'][0]['committed_kw'], '5.000000')
        self.assertEqual(result['rows'][0]['new_kw'], '0.000000')
        t['dispatch_allocations'][1]['committed_kw'] = '6'
        self.assertIsNone(self.run_op('dispatch_plan', t)['rows'][0]['total_kw'])

    def test_shared_measurement_and_inclusive_threshold_rounding(self):
        t = fixture()
        allocations(t)
        result = self.run_op('settlement_assessment', t)
        row = result['rows'][0]
        self.assertEqual(row['verified_kwh'], '5.000000')
        self.assertEqual(row['delivery_ratio'], '0.500000')
        self.assertEqual(row['revenue_cny'], '5.03')
        self.assertEqual(row['cost_cny'], '2.51')
        self.assertEqual(row['net_cny'], '2.52')
        self.assertIsNone(row['recorded_revenue_cny'])
        self.assertIn('a2', result['evidence']['dispatch_allocations'])
        t['execution_logs'][1]['status_code'] = 'failed'
        self.assertEqual(self.run_op('settlement_assessment', t)['rows'][0]['verified_kwh'], '10.000000')

    def test_missing_receipt_unknown_failed_zero_and_future_not_due(self):
        t = fixture()
        allocations(t)
        t['execution_logs'] = []
        self.assertIsNone(self.run_op('settlement_assessment', t)['rows'][0]['verified_kwh'])
        t['execution_logs'] = [{'execution_id': 'x1', 'allocation_id': 'a1', 'response_date': '2027-02-01', 'status_code': 'declined', 'revision': '1'}]
        self.assertEqual(self.run_op('settlement_assessment', t)['rows'][0]['verified_kwh'], '0.000000')
        t['response_events'][0]['response_date'] = '2027-03-01'
        self.assertEqual(self.run_op('settlement_assessment', t)['rows'][0]['status_code'], 'not_due')

    def test_excluded_offer_retains_known_site_without_requiring_forecast(self):
        for change in ({'status_code': 'withdrawn'}, {'valid_to': '2027-01-31'}):
            with self.subTest(change=change):
                t = fixture()
                t['flexibility_offers'][0].update(change)
                t['load_forecasts'] = []
                result = self.run_op('flexibility_assessment', t)
                self.assertEqual(result['device_rows'][0]['site_id'], 's1')
                self.assertEqual(result['device_rows'][0]['eligible_kw'], '0.000000')
                self.assertEqual(result['rows'][0]['eligible_kw'], '0.000000')
                self.assertEqual(result['completeness'], 'complete')

    def test_unknown_shared_plan_retains_known_commitment_fact(self):
        t = fixture()
        allocations(t)
        t['load_forecasts'] = []
        result = self.run_op('dispatch_plan', t)
        row = result['rows'][0]
        self.assertEqual(row['status_code'], 'unknown')
        self.assertEqual(row['committed_kw'], '5.000000')
        self.assertIsNone(row['new_kw'])
        self.assertIsNone(row['total_kw'])
        self.assertIsNone(row['estimated_cost_cny'])
        self.assertEqual(result['allocation_rows'][0]['allocated_kw'], '5.000000')
        self.assertEqual(result['allocation_rows'][0]['kind'], 'existing')

    def test_settlement_independent_of_forecast_and_price_unknown_is_local(self):
        t = fixture()
        allocations(t)
        t['load_forecasts'] = []
        t['devices'][0]['status_code'] = 'inactive'
        row = self.run_op('settlement_assessment', t)['rows'][0]
        self.assertEqual(row['verified_kwh'], '5.000000')
        self.assertEqual(row['revenue_cny'], '5.03')
        self.assertEqual(row['cost_cny'], '2.51')
        t['flexibility_offers'] = []
        row = self.run_op('settlement_assessment', t)['rows'][0]
        self.assertEqual(row['verified_kwh'], '5.000000')
        self.assertEqual(row['revenue_cny'], '5.03')
        self.assertIsNone(row['cost_cny'])
        self.assertIsNone(row['net_cny'])

    def test_zero_commitment_is_known_with_explicit_shortage(self):
        result = self.run_op('settlement_assessment', fixture())
        row = result['rows'][0]
        self.assertEqual(row['verified_kwh'], '0.000000')
        self.assertIsNone(row['delivery_ratio'])
        self.assertEqual(row['revenue_cny'], '0.00')
        self.assertEqual(row['cost_cny'], '0.00')
        self.assertTrue(any(i['code'] == 'target_shortage' for i in result['issues']))

    def test_bad_latest_reading_does_not_fall_back(self):
        t = fixture()
        allocations(t)
        t['meter_readings'].append({**t['meter_readings'][0], 'reading_id': 'r2', 'revision': '2', 'quality_code': 'invalid'})
        result = self.run_op('settlement_assessment', t)
        self.assertIsNone(result['rows'][0]['verified_kwh'])
        self.assertNotIn('r1', result['evidence']['meter_readings'])


if __name__ == '__main__':
    unittest.main()
