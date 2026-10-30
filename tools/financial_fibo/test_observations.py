"""The published functions take one dated scope; the loader recomputes it from in-memory SYN facts."""
import ast
import copy
import unittest

from test_issuer_known_amount import LANGUAGES, ROOT, SCOPE, module, setup_language, source

OPERATIONS = ('settlement_asof', 'valuation_asof', 'limit_assessment_asof')


def loader(lang):
    return module(ROOT / 'samples' / ('financial-fibo-' + lang) / 'tools/managed_execution.py',
                  'observations_loader_' + lang.replace('-', '_'))


class MemoryQuery:
    def __init__(self, tables, contract):
        self.tables, self.contract = tables, contract

    def __call__(self, kn, table, **kw):
        cond = kw['condition']
        values = cond['value'] if cond['operation'] == 'in' else [cond['value']]
        pk = self.contract['object_types'][table]['primary_key']
        rows = sorted((r for r in self.tables[table] if r[cond['field']] in values), key=lambda r: r[pk])
        return {'datas': copy.deepcopy(rows[kw['offset']:kw['offset'] + kw['limit']]), 'total_count': len(rows)}


class SingleScope(unittest.TestCase):
    def test_public_native_signature_has_four_required_arguments(self):
        for lang in LANGUAGES:
            path = ROOT / 'samples' / ('financial-fibo-' + lang) / 'tools/register_capabilities.py'
            tree = ast.parse(path.read_text())
            factory = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'tool_code')
            entry = next(n.value.value for n in factory.body if isinstance(n, ast.Assign)
                         and any(isinstance(t, ast.Name) and t.id == 'entry' for t in n.targets))
            function = next(n for n in ast.parse(entry).body if isinstance(n, ast.FunctionDef) and n.name == 'financial_function')
            self.assertEqual([a.arg for a in function.args.args], ['portfolio_ids', 'as_of_date', 'knowledge_date', 'view_kind'])
            self.assertEqual(function.args.defaults, [])

    def test_loaded_request_equals_direct_recomputation_all_operations_both_languages(self):
        for lang in LANGUAGES:
            core, contract = setup_language(lang)
            managed = loader(lang)
            tables = source('C_missing_opening_for_eligible_trade')
            for operation in OPERATIONS:
                with self.subTest(lang=lang, operation=operation):
                    result = managed.run_request(MemoryQuery(tables, contract), 'synthetic-kn', contract, operation, SCOPE, core.execute)
                    loaded = managed.load_sources(MemoryQuery(tables, contract), 'synthetic-kn', contract, SCOPE, operation)
                    direct = core.execute(operation, loaded, contract, SCOPE)
                    self.assertEqual({k: v for k, v in result.items() if k != 'data_source'}, direct)
                    self.assertEqual(result['data_source']['knowledge_network_id'], 'synthetic-kn')


if __name__ == '__main__':
    unittest.main()
