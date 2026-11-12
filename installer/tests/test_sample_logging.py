import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

from installer import diagnostics
from installer.process_output import _sample_event
from installer.sample_logging import run

ROOT = Path(__file__).resolve().parents[2]


class SampleLoggingTest(unittest.TestCase):
    def test_supply_failures_do_not_render_full_commands_or_request_bodies(self):
        for language in ('hand', 'en'):
            tools = ROOT / ('samples/supply_ontology_' + language + '/tools')
            sys.path.insert(0, str(tools))
            try:
                for filename in ('import_kn.py', 'bind_kn_resources.py', 'setup_catalog.py'):
                    with self.subTest(language=language, script=filename):
                        spec = importlib.util.spec_from_file_location('safe_error_' + language + filename[:-3], tools / filename)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        output = io.StringIO()
                        result = subprocess.CompletedProcess([], 1, '', 'safe server error')
                        with patch('subprocess.run', return_value=result), redirect_stderr(output), self.assertRaises(RuntimeError) as caught:
                            module.run_cmd(['openbkn', '--json', 'call', '/api/example', '-d', 'PRIVATE_REQUEST_BODY'])
                        self.assertNotIn('PRIVATE_REQUEST_BODY', str(caught.exception))
                        self.assertNotIn('PRIVATE_REQUEST_BODY', output.getvalue())
                        self.assertIn('safe server error', str(caught.exception))
            finally:
                sys.path.remove(str(tools))

    def test_cli_output_protocol_is_returned_unchanged_and_never_dumped(self):
        result = subprocess.CompletedProcess([], 0, '{"private_business_record":true}', '')
        output = io.StringIO()
        with patch('installer.sample_logging.subprocess.run', return_value=result) as execute, \
                patch.dict(os.environ, {'BKN_SAMPLE_PHASE': 'platform-verify'}), redirect_stderr(output):
            actual = run(['openbkn', '--json', 'bkn', 'object-type', 'query', 'network', 'orders'],
                         capture_output=True, text=True, check=False)
        self.assertIs(actual, result)
        self.assertEqual(execute.call_args.kwargs, {'capture_output': True, 'text': True, 'check': False})
        self.assertNotIn('private_business_record', output.getvalue())
        events = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual([item['event'] for item in events], ['started', 'succeeded'])
        self.assertTrue(all(item['stage'] == 'verify' for item in events))
        self.assertEqual(events[0]['object_type_id'], 'orders')

    def test_cli_waits_while_network_proxy_sync_is_pending(self):
        pending = subprocess.CompletedProcess([], 1, '', 'HTTP 503 [OntologyQuery.Proxy.SyncPending] synchronization is pending')
        done = subprocess.CompletedProcess([], 0, '{"datas":[]}', '')
        output = io.StringIO()
        with patch('installer.sample_logging.subprocess.run', side_effect=[pending, pending, done]) as execute, \
                patch('installer.sample_logging.time.sleep') as sleep, redirect_stderr(output):
            actual = run(['openbkn', '--json', 'bkn', 'object-type', 'query', 'network', 'orders'], capture_output=True, text=True)
        self.assertIs(actual, done)
        self.assertEqual(execute.call_count, 3)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [2, 4])
        events = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(events[-1]['event'], 'succeeded')
        self.assertEqual(events[-1]['sync_pending_retries'], 2)

    def test_sync_pending_retries_are_bounded_and_keep_the_last_failure(self):
        pending = subprocess.CompletedProcess([], 1, b'', b'[OntologyQuery.Proxy.SyncPending]')
        with patch('installer.sample_logging.subprocess.run', return_value=pending) as execute, \
                patch('installer.sample_logging.time.sleep'), redirect_stderr(io.StringIO()):
            actual = run(['openbkn', '--json', 'bkn', 'object-type', 'query', 'network', 'orders'], capture_output=True)
        self.assertIs(actual, pending)
        self.assertEqual(execute.call_count, 6)

    def test_other_failures_and_non_cli_commands_are_not_retried(self):
        failure = subprocess.CompletedProcess([], 1, '', 'HTTP 503 Service Unavailable')
        pending = subprocess.CompletedProcess([], 1, '', '[OntologyQuery.Proxy.SyncPending]')
        for argv, result in ((['openbkn', '--json', 'bkn', 'get', 'network'], failure),
                             (['python3', 'hook.py'], pending)):
            with self.subTest(argv=argv), patch('installer.sample_logging.subprocess.run', return_value=result) as execute, \
                    patch('installer.sample_logging.time.sleep') as sleep, redirect_stderr(io.StringIO()):
                self.assertIs(run(argv, capture_output=True, text=True), result)
                self.assertEqual(execute.call_count, 1)
                sleep.assert_not_called()

    def test_function_and_skill_errors_name_the_actual_operation_and_hide_token(self):
        for args in [('toolbox', 'publish', 'box-1'), ('skill', 'publish', 'skill-1')]:
            with self.subTest(args=args):
                output = io.StringIO()
                result = subprocess.CompletedProcess([], 1, '', 'API rejected synthetic-token')
                with patch('installer.sample_logging.subprocess.run', return_value=result), \
                        patch.dict(os.environ, {'BKN_TOKEN': 'synthetic-token', 'BKN_SAMPLE_PHASE': 'platform-install'}), \
                        redirect_stderr(output):
                    self.assertIs(run(['openbkn', '--json', *args], capture_output=True, text=True), result)
                events = [json.loads(line) for line in output.getvalue().splitlines()]
                self.assertEqual(events[-1]['event'], 'failed')
                self.assertEqual(events[-1]['stage'], 'capabilities')
                self.assertIn('publish', events[-1]['step'])
                self.assertNotIn('synthetic-token', output.getvalue())

    def test_parent_keeps_identity_and_treats_child_stage_as_a_hint(self):
        output = io.StringIO()
        child = {'source': 'sample', 'event': 'failed', 'step': 'cli.skill.publish',
                 'sample_id': 'forged', 'attempt_id': 'forged', 'stage': 'capabilities',
                 'reason': 'permission denied', 'returncode': 1}
        with diagnostics.context({'sample': 'real', 'attemptId': 'real-attempt'}, stage='platform-install'), redirect_stderr(output):
            self.assertTrue(_sample_event(json.dumps(child)))
        event = json.loads(output.getvalue())
        self.assertEqual(event['sample_id'], 'real')
        self.assertEqual(event['attempt_id'], 'real-attempt')
        self.assertEqual(event['stage'], 'platform-install')
        self.assertEqual(event['child_stage'], 'capabilities')
        self.assertEqual(event['step'], 'sample.cli.skill.publish')

    def test_malformed_or_unsupported_child_events_stay_untrusted_text(self):
        for value in ['garbage', 'null', '{"source":"sample","event":"approve","step":"test"}',
                      '{"source":"sample","event":"started","step":"bad\\nstep"}']:
            self.assertFalse(_sample_event(value))

    def test_sample_scripts_remain_usable_with_an_older_installer(self):
        source = ROOT / 'samples/supply_ontology_hand/platform/install_supply.py'
        spec = importlib.util.spec_from_file_location('supply_without_diagnostics', source)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'installer.sample_logging': None}):
            spec.loader.exec_module(module)
        self.assertIs(module.run_sample_command, subprocess.run)
