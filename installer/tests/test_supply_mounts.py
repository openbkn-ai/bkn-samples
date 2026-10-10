import sys
import unittest
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[2] / 'samples/supply_ontology_hand/tools'
sys.path.insert(0, str(TOOLS))
import register_native_function_toolbox as FUNCTIONS
import register_skills as SKILLS
from function_catalog import FUNCTION_CATALOG


class SupplyMountTest(unittest.TestCase):
    def test_functions_mount_only_declared_tool_ids(self):
        calls = []

        def call(args):
            calls.append(args)
            if args[:2] == ['toolbox', 'list']:
                return {'data': [{'box_name': 'Supply', 'box_id': 'box-1', 'status': 'published'}]}
            if args[:2] == ['tool', 'list']:
                return {'tools': [dict(name=spec['name'], tool_id=operation, status='enabled')
                                  for operation, spec in FUNCTION_CATALOG.items()]}
            return {}

        with patch.object(FUNCTIONS, '_call', call):
            FUNCTIONS.run(box_name='Supply', apply=True, kn_id='network')
        attach = next(args for args in calls if args[:3] == ['bkn', 'capability', 'attach'])
        self.assertEqual(attach, ['bkn', 'capability', 'attach', 'network', '--box', 'box-1',
                                  '--tool', ','.join(FUNCTION_CATALOG)])
        self.assertNotIn('--all-tools', attach)

    def test_skills_mount_only_registered_ids_after_publication(self):
        calls = []

        def call(args):
            calls.append(args)
            if args[:2] == ['skill', 'list']:
                return {'data': []}
            if args[:2] == ['skill', 'register']:
                return {'skill_id': Path(args[2]).name}
            return {}

        with patch.object(SKILLS, 'run_cli', call):
            result = SKILLS.run(apply=True, kn_id='network')
        self.assertIn(['skill', 'list', '--all'], calls)
        self.assertEqual(calls[-1], ['bkn', 'capability', 'attach', 'network', '--skill',
                                    ','.join(item['skill_id'] for item in result['skills'])])
        self.assertEqual(len(result['skills']), len(SKILLS.local_skills()))


if __name__ == '__main__':
    unittest.main()
