import sys
import json
import unittest
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[2] / 'samples/supply_ontology_hand/tools'
sys.path.insert(0, str(TOOLS))
import register_native_function_toolbox as FUNCTIONS
import register_skills as SKILLS
from function_catalog import FUNCTION_CATALOG, KIT_PLAN_ACTIONS, KIT_SCHEDULE, SCHEDULE_RULES


class SupplyMountTest(unittest.TestCase):
    def test_calculations_are_mounted_and_only_the_plan_changes_are_actions(self):
        calls = []

        def call(args):
            calls.append(args)
            if args[:2] == ['toolbox', 'list']:
                return {'data': [{'box_name': 'Supply', 'box_id': 'box-1', 'status': 'published'}]}
            if args[:2] == ['tool', 'list']:
                return {'tools': [dict(name=spec['name'], tool_id=operation, status='enabled')
                                  for operation, spec in [*FUNCTION_CATALOG.items(), ('kit_schedule', KIT_SCHEDULE),
                                                          *SCHEDULE_RULES.items()]]}
            return {}

        with patch.object(FUNCTIONS, '_call', call):
            result = FUNCTIONS.run(box_name='Supply', apply=True, kn_id='supply_ontology_hand')
        attach = next(args for args in calls if args[:3] == ['bkn', 'capability', 'attach'])
        # Calculations only read: mounted on the network, run with execute_tool.
        self.assertEqual(attach, ['bkn', 'capability', 'attach', 'supply_ontology_hand', '--box', 'box-1',
                                  '--tool', ','.join([*FUNCTION_CATALOG, *SCHEDULE_RULES])])
        self.assertEqual(result['mounted_tools'], [*FUNCTION_CATALOG, *SCHEDULE_RULES])
        create = next(args for args in calls if args[:1] == ['call'] and '/action-types' in args[1])
        self.assertIn('import_mode=overwrite', create[1])
        actions = json.loads(create[create.index('-d') + 1])['entries']
        # Only what changes objects is an action: the three plan actions.
        self.assertEqual([a['id'] for a in actions], [f'supply_ontology_hand_kitplan_{key}' for key in KIT_PLAN_ACTIONS])
        self.assertEqual(result['action_ids'], [a['id'] for a in actions])
        for action in actions:
            self.assertEqual(action['operation_config'], {'type': 'object'})
            self.assertEqual(action['object_type_id'], 'supply_ontology_hand_kitplan')
            self.assertEqual(action['action_source'], {'type': 'tool', 'box_id': 'box-1', 'tool_id': 'kit_schedule'})

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
