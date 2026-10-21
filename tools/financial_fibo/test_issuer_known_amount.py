"""Hand-calculated invariants over public invented SYN facts, never answer banks.

Two equities: ten shares at USD5 = USD50; second ten shares at USD3 =
USD30 when its quote is supplied. No model, MCP, network or database calls.
"""
import copy
import importlib.util
import json
import sys
import unittest
from decimal import Decimal as D
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / 'fixtures'
LANGUAGES = ('en-us', 'zh-cn')


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def setup_language(lang):
    base = ROOT / 'samples' / ('financial-fibo-' + lang)
    return (module(base / 'tools/post_trade.py', 'issuer_core_' + lang.replace('-', '_')),
            json.loads((base / 'model-contract.json').read_text()))


def source(name='A_known_issuer_other_missing_quote'):
    return json.loads((FIXTURES / ('synthetic-issuer-local-' + name + '-source.json')).read_text())


SCOPE = json.loads((FIXTURES / 'synthetic-issuer-local-scope.json').read_text())


def canonical(result, contract):
    """Compare financial semantics while allowing translated display statuses."""
    result = copy.deepcopy(result)
    for row in result['rows']:
        row.pop('status', None)
        if 'unit' in row:
            row['unit'] = {v: k for k, v in contract['localized_values'].items()}.get(row['unit'], row['unit'])
    return result


class IssuerKnownAmount(unittest.TestCase):
    def calculate(self, data):
        outputs = []
        before = copy.deepcopy(data)
        for lang in LANGUAGES:
            core, contract = setup_language(lang)
            result = core.execute('limit_assessment_asof', data, contract, SCOPE)
            self.assertEqual(data, before, 'source facts must stay immutable: ' + lang)
            outputs.append(canonical(result, contract))
        self.assertEqual(*outputs, 'bilingual business semantics must agree')
        return outputs[0], {r['entity_id']: r for r in outputs[0]['rows'] if r['measure'] == 'issuer_ratio'}

    def assert_unknown_ratios(self, rows):
        self.assertTrue(rows)
        for row in rows.values():
            self.assertIsNone(row['observed_value'])
            self.assertEqual(row['status_code'], 'unknown')

    def test_known_fifty_survives_unrelated_unknown_quote(self):
        _, rows = self.calculate(source())
        self.assertEqual(D(rows['SYN-I1']['exposure_amount']), D(50))
        self.assertIsNone(rows['SYN-I2']['exposure_amount'])
        self.assertTrue(all(r['denominator_amount'] is None for r in rows.values()))
        self.assert_unknown_ratios(rows)

    def test_partial_issuer_cannot_report_only_its_known_component(self):
        data = source()
        # Both positions now belong to I1: known USD50 is only a lower bound,
        # not the full issuer exposure while the second position is unpriced.
        data['financial_instruments'][1]['issuer_id'] = 'SYN-I1'
        _, rows = self.calculate(data)
        self.assertIsNone(rows['SYN-I1']['exposure_amount'])
        self.assert_unknown_ratios(rows)

    def test_complete_eighty_book_has_five_eighths_and_three_eighths(self):
        data = source()
        quote = dict(data['market_prices'][0], price_id='SYN-NEW-QUOTE', instrument_id='SYN-S2', price='3')
        data['market_prices'].append(quote)
        _, rows = self.calculate(data)
        for issuer, amount, ratio in [('SYN-I1', 50, '.625'), ('SYN-I2', 30, '.375')]:
            self.assertEqual(D(rows[issuer]['exposure_amount']), D(amount))
            self.assertEqual(D(rows[issuer]['denominator_amount']), D(80))
            self.assertEqual(D(rows[issuer]['observed_value']), D(ratio))

    def test_proven_zero_book_has_known_zero_amounts_but_undefined_ratio(self):
        result, rows = self.calculate(source('B_proven_zero_book'))
        for row in rows.values():
            self.assertEqual(D(row['exposure_amount']), D(0))
            self.assertEqual(D(row['denominator_amount']), D(0))
        self.assert_unknown_ratios(rows)
        self.assertIn('INVALID_DENOMINATOR', {i['code'] for i in result['issues']})

    def test_zero_issuer_is_known_even_when_other_issuer_is_unpriced(self):
        data = source()
        data['opening_positions'][0]['quantity'] = '0'
        _, rows = self.calculate(data)
        self.assertEqual(D(rows['SYN-I1']['exposure_amount']), D(0))
        self.assertIsNone(rows['SYN-I2']['exposure_amount'])
        self.assert_unknown_ratios(rows)

    def test_missing_opening_only_poison_its_identified_issuer_amount(self):
        result, rows = self.calculate(source('C_missing_opening_for_eligible_trade'))
        self.assertEqual(D(rows['SYN-I1']['exposure_amount']), D(50))
        self.assertIsNone(rows['SYN-I2']['exposure_amount'])
        self.assertTrue(all(r['denominator_amount'] is None for r in rows.values()))
        self.assert_unknown_ratios(rows)
        self.assertIn('MISSING_OPENING_POSITION', {i['code'] for i in result['issues']})

    def test_unassignable_missing_opening_blocks_all_issuer_amounts(self):
        data = source('C_missing_opening_for_eligible_trade')
        next(i for i in data['financial_instruments'] if i['instrument_id'] == 'SYN-S2')['issuer_id'] = ''
        _, rows = self.calculate(data)
        self.assertTrue(all(r['exposure_amount'] is None and r['denominator_amount'] is None for r in rows.values()))
        self.assert_unknown_ratios(rows)

    def test_missing_opening_blocks_even_an_issuer_with_a_known_existing_position(self):
        data = source('C_missing_opening_for_eligible_trade')
        data['financial_instruments'][1]['issuer_id'] = 'SYN-I1'
        _, rows = self.calculate(data)
        self.assertIsNone(rows['SYN-I1']['exposure_amount'])
        self.assert_unknown_ratios(rows)

    def test_broken_security_master_rejects_instead_of_manufacturing_zero(self):
        data = source('C_missing_opening_for_eligible_trade')
        data['financial_instruments'] = [i for i in data['financial_instruments'] if i['instrument_id'] != 'SYN-S2']
        before = copy.deepcopy(data)
        for lang in LANGUAGES:
            core, contract = setup_language(lang)
            with self.subTest(lang=lang), self.assertRaises((KeyError, ValueError)):
                core.execute('limit_assessment_asof', data, contract, SCOPE)
            self.assertEqual(data, before)

    def test_empty_valuation_coverage_cannot_prove_zero_book(self):
        data = source()
        data['opening_positions'] = []
        _, rows = self.calculate(data)
        self.assertTrue(all(r['exposure_amount'] is None and r['denominator_amount'] is None for r in rows.values()))
        self.assert_unknown_ratios(rows)


if __name__ == '__main__':
    unittest.main(verbosity=2)
