"""Pure request-local observation tests using invented public SYN facts.

Source query is an in-memory filtering callback. Small patched output quotas
exercise UTF8 accounting and fail-closed behavior; not a platform native quota validation.
"""
import ast
import copy
import json
import unittest
from unittest.mock import patch

from test_issuer_known_amount import LANGUAGES, ROOT, SCOPE, canonical, module, setup_language, source

OPERATIONS = ('settlement_asof', 'valuation_asof', 'limit_assessment_asof')
ADDITIONAL = [dict(as_of_date='2045-01-31', knowledge_date='2045-01-14', view_kind='actual'),
              dict(as_of_date='2045-01-31', knowledge_date='2045-01-31', view_kind='planned')]


def loader(lang):
    return module(ROOT / 'samples' / ('financial-fibo-' + lang) / 'tools/managed_execution.py',
                  'observations_loader_' + lang.replace('-', '_'))


class MemoryQuery:
    def __init__(self, tables, contract):
        self.tables, self.contract, self.calls = tables, contract, []

    def __call__(self, kn, table, **kw):
        self.calls.append((kn, table, copy.deepcopy(kw)))
        cond = kw['condition']
        values = cond['value'] if cond['operation'] == 'in' else [cond['value']]
        pk = self.contract['object_types'][table]['primary_key']
        rows = sorted((r for r in self.tables[table] if r[cond['field']] in values), key=lambda r: r[pk])
        return {'datas': copy.deepcopy(rows[kw['offset']:kw['offset'] + kw['limit']]), 'total_count': len(rows)}


def observed_source():
    data = source('C_missing_opening_for_eligible_trade')
    # Planned mark is USD7 rather than actual USD5: known first issuer = USD70.
    data['market_prices'].append(dict(data['market_prices'][0], price_id='SYN-PLANNED', price='7', view_kind='planned'))
    return data


class Observations(unittest.TestCase):
    def test_public_native_signature_keeps_four_required_arguments(self):
        # Inspect public registration source without importing SDK/CLI wiring.
        for lang in LANGUAGES:
            path = ROOT / 'samples' / ('financial-fibo-' + lang) / 'tools/register_capabilities.py'
            tree = ast.parse(path.read_text())
            factory = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'tool_code')
            entry = next(n.value.value for n in factory.body if isinstance(n, ast.Assign)
                         and any(isinstance(t, ast.Name) and t.id == 'entry' for t in n.targets))
            function = next(n for n in ast.parse(entry).body if isinstance(n, ast.FunctionDef) and n.name == 'financial_function')
            self.assertEqual([a.arg for a in function.args.args],
                             ['portfolio_ids', 'as_of_date', 'knowledge_date', 'view_kind', 'additional_observations'])
            self.assertEqual(len(function.args.defaults), 1)
            self.assertIsNone(function.args.defaults[0].value)
            self.assertEqual(function.args.args[-1].annotation.id, 'list')

    def test_each_scope_equals_independent_scalar_all_operations_both_languages(self):
        bilingual = {}
        for lang in LANGUAGES:
            core, contract = setup_language(lang)
            managed = loader(lang)
            tables = observed_source()
            before = copy.deepcopy((tables, SCOPE, ADDITIONAL))
            for operation in OPERATIONS:
                with self.subTest(lang=lang, operation=operation):
                    query = MemoryQuery(tables, contract)
                    # Read-call equality measures pool loading, not just a claimed counter.
                    managed.load_sources(query, 'synthetic-kn', contract, SCOPE, operation)
                    pool_calls = copy.deepcopy(query.calls)
                    query.calls.clear()
                    batch = managed.run_request(query, 'synthetic-kn', contract, operation, SCOPE, core.execute, ADDITIONAL)
                    self.assertEqual(query.calls, pool_calls)
                    self.assertEqual(set(batch), {'schema_version', 'capability', 'mode', 'source_loads', 'observations'})
                    self.assertEqual((batch['schema_version'], batch['capability'], batch['mode'], batch['source_loads']),
                                     (1, operation, 'observations', 1))
                    self.assertEqual(len(batch['observations']), 3)
                    expected = []
                    for scope in [SCOPE] + [dict(s, portfolio_ids=SCOPE['portfolio_ids']) for s in ADDITIONAL]:
                        expected.append(managed.run_request(MemoryQuery(tables, contract), 'synthetic-kn', contract, operation, scope, core.execute))
                    self.assertEqual(batch['observations'], expected)
                    self.assertTrue(all(set(o['data_source']) == {'knowledge_network_id', 'loaded_counts'} for o in expected))
                    # Mutating one returned envelope must not contaminate another.
                    independent = copy.deepcopy(batch['observations'][1:])
                    first = batch['observations'][0]
                    first['data_source']['loaded_counts']['SYN-ONLY-FIRST'] = 1
                    first['issues'].append({'code': 'SYN-ONLY-FIRST'})
                    first['evidence']['SYN-ONLY-FIRST'] = ['test']
                    self.assertEqual(batch['observations'][1:], independent)
                    bilingual.setdefault(lang, {})[operation] = [canonical(r, contract) for r in expected]
            self.assertEqual((tables, SCOPE, ADDITIONAL), before)
        self.assertEqual(bilingual[LANGUAGES[0]], bilingual[LANGUAGES[1]])

    def test_wire_strings_and_mixed_objects_equal_full_typed_results(self):
        for lang in LANGUAGES:
            core, contract = setup_language(lang)
            managed = loader(lang)
            data = observed_source()
            wire = [json.dumps(item, ensure_ascii=False) for item in ADDITIONAL]
            mixed = [wire[0], copy.deepcopy(ADDITIONAL[1])]
            before = copy.deepcopy((data, SCOPE, ADDITIONAL, wire, mixed))
            for operation in OPERATIONS:
                expected = managed.run_request(MemoryQuery(data, contract), 'kn', contract,
                                               operation, SCOPE, core.execute, ADDITIONAL)
                for extra in (wire, mixed):
                    with self.subTest(lang=lang, operation=operation, extra=extra):
                        result = managed.run_request(MemoryQuery(data, contract), 'kn', contract,
                                                     operation, SCOPE, core.execute, extra)
                        self.assertEqual(result, expected)
                        scalar = [managed.run_request(MemoryQuery(data, contract), 'kn', contract,
                                                      operation, current, core.execute)
                                  for current in [SCOPE] + [dict(item, portfolio_ids=SCOPE['portfolio_ids'])
                                                           for item in ADDITIONAL]]
                        self.assertEqual(result['observations'], scalar)
            self.assertEqual((data, SCOPE, ADDITIONAL, wire, mixed), before)

    def test_invalid_wire_rejected_before_source_loading(self):
        duplicate = ('{"as_of_date":"2045-01-31","knowledge_date":"2045-01-14",'
                     '"view_kind":"planned","view_kind":"actual"}')
        invalid = ['', '{', '[]', 'null', 'true', '1', '"text"', '{}', duplicate,
                   json.dumps(dict(ADDITIONAL[0], unexpected='field')),
                   json.dumps(dict(ADDITIONAL[0], knowledge_date='2045-02-30')),
                   json.dumps(dict(ADDITIONAL[0], view_kind='forecast'))]
        for lang in LANGUAGES:
            managed = loader(lang)
            _, contract = setup_language(lang)
            for wire in invalid:
                with self.subTest(lang=lang, wire=wire):
                    with patch.object(managed, 'load_sources') as load:
                        with self.assertRaises(ValueError):
                            managed.run_request(None, 'kn', contract, 'valuation_asof', SCOPE,
                                                None, [wire])
                        load.assert_not_called()

    def test_duplicate_canonical_scope_across_wire_and_dict_rejected_before_loading(self):
        for lang in LANGUAGES:
            managed = loader(lang)
            _, contract = setup_language(lang)
            # Different whitespace/key order still describes the same scope.
            wire = json.dumps(dict(reversed(list(ADDITIONAL[0].items()))), indent=2)
            for extra in ([wire, ADDITIONAL[0]], [ADDITIONAL[0], wire],
                          [json.dumps({key: SCOPE[key] for key in ADDITIONAL[0]})]):
                with self.subTest(lang=lang, extra=extra):
                    with patch.object(managed, 'load_sources') as load:
                        with self.assertRaisesRegex(ValueError, '^DUPLICATE_OBSERVATION$'):
                            managed.run_request(None, 'kn', contract, 'valuation_asof', SCOPE,
                                                None, extra)
                        load.assert_not_called()

    def test_scopes_have_materially_different_financial_facts(self):
        # Batch/scalar equality alone could pass if both ignored the scope.
        for lang in LANGUAGES:
            core, contract = setup_language(lang)
            managed = loader(lang)
            data = observed_source()
            settle = managed.run_request(MemoryQuery(data, contract), 'kn', contract, 'settlement_asof', SCOPE, core.execute, ADDITIONAL)
            self.assertEqual(len(settle['observations'][0]['rows']), 1)
            self.assertEqual(settle['observations'][1]['rows'], [])
            values = managed.run_request(MemoryQuery(data, contract), 'kn', contract, 'valuation_asof', SCOPE, core.execute, ADDITIONAL)['observations']
            self.assertEqual(values[0]['rows'][0]['market_value_base'], '50.00')
            self.assertIsNone(values[1]['rows'][0]['market_value_base'])
            self.assertEqual(values[2]['rows'][0]['market_value_base'], '70.00')
            self.assertNotIn('SYN-PLANNED', values[0]['evidence'].get('market_prices', []))
            self.assertNotIn('SYN-PRICE1', values[2]['evidence'].get('market_prices', []))

    def test_next_request_reloads_changed_price(self):
        for lang in LANGUAGES:
            core, contract = setup_language(lang)
            managed = loader(lang)
            data = observed_source()
            query = MemoryQuery(data, contract)
            args = (query, 'kn', contract, 'valuation_asof', SCOPE, core.execute, ADDITIONAL)
            first = managed.run_request(*args)
            calls = len(query.calls)
            data['market_prices'][0]['price'] = '9'
            second = managed.run_request(*args)
            self.assertEqual(len(query.calls), calls * 2)
            self.assertEqual(first['observations'][0]['rows'][0]['market_value_base'], '50.00')
            self.assertEqual(second['observations'][0]['rows'][0]['market_value_base'], '90.00')

    def test_none_and_empty_preserve_scalar_envelope(self):
        for lang in LANGUAGES:
            core, contract = setup_language(lang)
            managed = loader(lang)
            tables = observed_source()
            expected_tables = managed.load_sources(MemoryQuery(tables, contract), 'kn', contract, SCOPE, 'valuation_asof')
            expected = core.execute('valuation_asof', expected_tables, contract, SCOPE)
            expected['data_source'] = {'knowledge_network_id': 'kn', 'loaded_counts': {k: len(v) for k, v in expected_tables.items() if v}}
            for extra in (None, []):
                self.assertEqual(managed.run_request(MemoryQuery(tables, contract), 'kn', contract, 'valuation_asof', SCOPE, core.execute, extra), expected)

    def test_invalid_batch_rejected_before_source_reads_or_execution(self):
        bad = [({}, ADDITIONAL), (dict(SCOPE, portfolio_ids=[]), ADDITIONAL),
               (dict(SCOPE, portfolio_ids=['x'] * 2), ADDITIONAL),
               (dict(SCOPE, portfolio_ids=[str(i) for i in range(21)]), ADDITIONAL),
               (dict(SCOPE, portfolio_ids=[None]), ADDITIONAL),
               (dict(SCOPE, portfolio_ids='SYN-P'), ADDITIONAL),
               (SCOPE, {}), (SCOPE, 'bad'),
               (SCOPE, ADDITIONAL * 6),  # 13 total scopes
               (SCOPE, [{k: SCOPE[k] for k in ADDITIONAL[0]}]),
               (SCOPE, [ADDITIONAL[0], ADDITIONAL[0]]),
               (SCOPE, [None]), (SCOPE, [[]]),
               (SCOPE, [dict(ADDITIONAL[0], unexpected='field')]),
               (SCOPE, [{'as_of_date': '2045-01-31', 'view_kind': 'actual'}])]
        for key in ('as_of_date', 'knowledge_date'):
            for value in ('2045-02-30', '20450131', '2045-1-31', '2045-01-31T00:00:00Z', None):
                bad.append((SCOPE, [dict(ADDITIONAL[0], **{key: value})]))
                bad.append((dict(SCOPE, **{key: value}), ADDITIONAL))
        for view in ('实际', 'forecast', None):
            bad.append((SCOPE, [dict(ADDITIONAL[0], view_kind=view)]))
            bad.append((dict(SCOPE, view_kind=view), ADDITIONAL))
        for lang in LANGUAGES:
            _, contract = setup_language(lang)
            managed = loader(lang)
            for scope, additional in bad:
                with self.subTest(lang=lang, scope=scope, additional=additional):
                    def forbidden(*a, **kw):
                        self.fail('invalid batch reached source query or executor')
                    with self.assertRaises((ValueError, KeyError)):
                        managed.run_request(forbidden, 'kn', contract, 'valuation_asof', scope, forbidden, additional)

    def test_exact_twelve_observations_twenty_portfolios_and_scalar_two_hundred(self):
        for lang in LANGUAGES:
            managed = loader(lang)
            _, contract = setup_language(lang)
            ids = ['SYN-P' + str(i) for i in range(20)]
            scope = dict(SCOPE, portfolio_ids=ids)
            extra = [dict(ADDITIONAL[0], knowledge_date='2045-01-%02d' % day) for day in range(1, 12)]
            calls, executions = [], []
            def query(*args, **kwargs):
                calls.append(args)
                return {'datas': [], 'total_count': 0}
            def execute(operation, tables, c, current):
                executions.append(copy.deepcopy(current))
                return {'scope': copy.deepcopy(current), 'rows': []}
            result = managed.run_request(query, 'kn', contract, 'valuation_asof', scope, execute, extra)
            self.assertEqual(len(result['observations']), 12)
            self.assertEqual(len(executions), 12)
            self.assertTrue(all(s['portfolio_ids'] == ids for s in executions))
            for omitted in (None, []):
                result = managed.run_request(query, 'kn', contract, 'valuation_asof', dict(SCOPE, portfolio_ids=[str(i) for i in range(200)]), execute, omitted)
                self.assertEqual(len(result['scope']['portfolio_ids']), 200)
                self.assertNotIn('mode', result)

    def test_partial_or_missing_payload_fails_before_execution(self):
        for lang in LANGUAGES:
            managed = loader(lang)
            _, contract = setup_language(lang)
            for payload in ({'datas': [], 'partial': True}, {'datas': [], 'partial_reasons': ['SYN']},
                            {'total_count': 1}, {'data': []}, {'datas': None}, None):
                with self.subTest(lang=lang, payload=payload):
                    def forbidden(*args):
                        self.fail('incomplete source reached executor')
                    with self.assertRaises(ValueError):
                        managed.run_request(lambda *a, **kw: copy.deepcopy(payload), 'kn', contract, 'valuation_asof', SCOPE, forbidden, ADDITIONAL)

    def test_configured_batch_quota_matches_three_mib_revision(self):
        for lang in LANGUAGES:
            managed = loader(lang)
            self.assertEqual(managed.BATCH_PORTFOLIOS, 20)
            self.assertEqual(managed.BATCH_OUTPUT_BYTES, 3 * 1024 * 1024)
            _, contract = setup_language(lang)
            query = lambda *a, **kw: {'datas': [], 'total_count': 0}
            # Each scope is modest alone, but the complete two-scope UTF8 result
            # exceeds the real local 3MiB guard. No partial envelope is returned.
            execute = lambda *a: {'rows': ['测' * (600 * 1024)]}
            with self.assertRaisesRegex(ValueError, 'BATCH_OUTPUT_EXCEEDED'):
                managed.run_request(query, 'kn', contract, 'valuation_asof', SCOPE, execute, ADDITIONAL[:1])

    def test_utf8_output_guard_rejects_instead_of_truncating(self):
        # This is a reduced quota unit check, not a platform native quota validation.
        for lang in LANGUAGES:
            managed = loader(lang)
            _, contract = setup_language(lang)
            query = lambda *a, **kw: {'datas': [], 'total_count': 0}
            execute = lambda *a: {'rows': ['测' * 200]}
            args = (query, 'kn', contract, 'valuation_asof', SCOPE, execute, ADDITIONAL[:1])
            response = managed.run_request(*args)
            encoded = json.dumps(response, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
            self.assertGreater(len(encoded), len(encoded.decode('utf-8')))
            with patch.object(managed, 'BATCH_OUTPUT_BYTES', len(encoded) - 1):
                with self.assertRaisesRegex(ValueError, 'BATCH_OUTPUT_EXCEEDED'):
                    managed.run_request(*args)
            with patch.object(managed, 'BATCH_OUTPUT_BYTES', len(encoded)):
                self.assertEqual(managed.run_request(*args), response, 'exact serialized quota boundary must fit')


if __name__ == '__main__':
    unittest.main(verbosity=2)
