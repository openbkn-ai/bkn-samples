"""Checks for portability and lossless restoration, independent of a live platform."""
import datetime
import decimal
import importlib.util
import json
import os
import re
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


DB = module('ecommerce_database', 'db/database.py')
PLATFORM = module('ecommerce_platform', 'platform/network.py')


class SampleTests(unittest.TestCase):
    def test_lossless_typed_values(self):
        values = [None, '', 0, False, decimal.Decimal('123.4500'), datetime.datetime(2026, 11, 20, 0, 0),
                  datetime.date(2026, 11, 20), datetime.timedelta(seconds=3601), b'\x00\xff']
        decoded = [DB.decode(v) for v in json.loads(json.dumps(values, default=DB.encode))]
        self.assertEqual(values, decoded)
        self.assertEqual(str(decoded[4]), '123.4500')

    def test_receipt_retains_bindings_between_hook_invocations(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'BKN_SAMPLE_RECEIPT': str(Path(temp) / 'receipt.json')}):
            state = PLATFORM.State(); state.remember('toolboxes', 'ecommerce_box_a', 'new-box')
            state.phase('tools')
            restored = PLATFORM.State()
            self.assertEqual(restored.value['map']['ecommerce_box_a'], 'new-box')
            self.assertIn('tools', restored.value['phases'])
            self.assertEqual(restored.owned['toolboxes'], ['new-box'])

    def test_render_cross_tool_references_without_source_mutation(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'BKN_SAMPLE_RECEIPT': str(Path(temp) / 'receipt.json')}):
            state = PLATFORM.State(); state.value['map'] = {'ecommerce_tool_a': 'fresh-id'}
            source = {'code': "TOOLS={'x':'ecommerce_tool_a'}", 'list': ['ecommerce_tool_a']}
            result = state.render(source)
            self.assertEqual(result['list'], ['fresh-id'])
            self.assertIn('fresh-id', result['code'])
            self.assertIn('ecommerce_tool_a', source['code'])

    def test_all_function_sources_compile_and_are_scoped_to_sample(self):
        functions = PLATFORM.load(ROOT / 'tools/assets/functions.json')
        self.assertEqual(len(functions), 49)
        self.assertEqual(sum(d['metadata_type'] == 'function' for d in functions), 39)
        for d in functions:
            f = d.get('function_input', {})
            if f.get('script_type') == 'python':
                compile(f['code'], d['name'], 'exec')
            elif f.get('script_type') == 'cypher':
                self.assertEqual(f['kn_id'], PLATFORM.KN)
            self.assertNotIn('ecommerce_ops_bkn_zh_standard_20261119', f.get('code', ''))

    def test_metrics_have_complete_version_dependencies(self):
        records = [PLATFORM.load(p) for p in (ROOT / 'kn/object_metrics').glob('*.json')]
        definitions = [r['definition'] for r in records]
        keys = {(d['id'], d['version']) for d in definitions}
        self.assertEqual(len({d['id'] for d in definitions}), 67)
        def visit(v):
            if isinstance(v, dict):
                if 'metric_id' in v and 'version' in v:
                    self.assertIn((v['metric_id'], v['version']), keys)
                for child in v.values(): visit(child)
            elif isinstance(v, list):
                for child in v: visit(child)
        for d in definitions: visit(d)

    def test_event_managed_definitions_are_not_imported_twice(self):
        events = PLATFORM.load(ROOT / 'tools/assets/events.json')
        self.assertEqual(len(events), 7)
        for event in events:
            self.assertFalse((ROOT / 'kn/object_types' / (event['code'] + '.bkn')).exists())
            self.assertFalse((ROOT / 'kn/relation_types' / (event['code'] + '_subject.bkn')).exists())
        policies = {e['code']: e['rule'] for e in events}
        self.assertEqual(policies['payment_failure_unrecovered']['thresholds']['quiet_wait_minutes'], 15)
        self.assertEqual(policies['logistics_tracking_stalled']['thresholds']['stagnation_hours'], 48)
        self.assertEqual(policies['return_received_processing_wait']['thresholds']['processing_wait_hours'], 24)

    def test_resource_fields_exist_in_frozen_real_tables(self):
        schema, digest = DB.fixture()
        self.assertTrue(digest)
        for oid, binding in PLATFORM.load(ROOT / 'tools/assets/bindings.json').items():
            columns = {c['Field'] for c in schema['tables'][binding['table']]['columns']}
            mapped = {v['name'] if isinstance(v, dict) else v for v in binding['fields'].values()}
            self.assertTrue(mapped <= columns, oid)

    def test_only_declared_skills_are_packaged(self):
        skills = PLATFORM.load(ROOT / 'tools/assets/skills.json')
        self.assertEqual(len(skills), 3)
        self.assertEqual({p.name for p in (ROOT / 'skills').iterdir()}, {s['name'] for s in skills})
        for s in skills:
            self.assertIn('name: ' + s['name'], (ROOT / s['directory'] / 'SKILL.md').read_text(encoding='utf-8'))

    def test_toolbox_names_follow_platform_contract(self):
        for box in PLATFORM.load(ROOT / 'tools/assets/toolboxes.json'):
            self.assertRegex(box['name'], r'^[A-Za-z0-9_]+$')
            self.assertLessEqual(len(box['name']), 50)
        bootstrap = PLATFORM.load(ROOT / 'tools/assets/bootstrap.json')
        self.assertEqual(bootstrap['branch'], 'main')

    def test_impact_contracts_do_not_duplicate_legacy_affect_projection(self):
        for file in (ROOT / 'kn/action_types').glob('*.bkn'):
            text = file.read_text(encoding='utf-8')
            self.assertFalse('### Impact Contracts' in text and '### Affect Object' in text, file.name)

    def test_parameter_defaults_preserve_effective_binding(self):
        original = [{'name': 'status', 'type': 'string', 'source': 'body', 'value_from': 'input'}]
        imported = [{**original[0], 'operation': '', 'value': '', 'if_system_gen': False, 'comment': ''}]
        self.assertEqual(PLATFORM.parameter_semantics(original), PLATFORM.parameter_semantics(imported))
        imported[0]['source'] = 'path'
        self.assertNotEqual(PLATFORM.parameter_semantics(original), PLATFORM.parameter_semantics(imported))

    def test_event_install_adds_only_missing_members_with_entries_envelope(self):
        groups = PLATFORM.load(ROOT / 'tools/assets/groups.json')
        events = PLATFORM.load(ROOT / 'tools/assets/events.json')
        current = [{'id': g['id'], 'object_type_ids': [i for i in g.get('object_type_ids') or [] if i not in {e['code'] for e in events}]} for g in groups]
        calls = []
        def request(method, path, body=None):
            if method == 'GET':
                return {'entries': events} if path.endswith('/event-types') else {'concept_groups': current}
            calls.append((method, path, body)); return {}
        class FakeState:
            render = staticmethod(lambda value: value)
            phase = staticmethod(lambda name: None)
        with patch.object(PLATFORM, 'api', side_effect=request):
            PLATFORM.install_events(FakeState())
        memberships = [body for method, path, body in calls if path.endswith('strict_mode=true')]
        self.assertEqual(len(memberships), 1)
        self.assertEqual({i['id'] for i in memberships[0]['entries']}, {e['code'] for e in events})

    def test_http_success_with_unknown_event_check_is_rejected(self):
        native = next(e for e in PLATFORM.load(ROOT / 'tools/assets/events.json') if e.get('rule_tool'))
        original_load = PLATFORM.load
        def selected_load(path):
            return [native] if Path(path).name == 'events.json' else original_load(path)
        with patch.object(PLATFORM, 'load', side_effect=selected_load), patch.object(PLATFORM, 'api', return_value={'check': {'status': 'unknown'}}):
            with self.assertRaisesRegex(ValueError, 'native event check incomplete'):
                PLATFORM.scan_events(None)


if __name__ == '__main__':
    unittest.main()
