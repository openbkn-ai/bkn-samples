import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from unittest.mock import Mock, patch

from installer import diagnostics
from installer.control_plane import create_installation, retry_installation, ownership_tags
from installer.hook_process import run_hook
from installer.remote_bundle import download_package
from installer.runtime import process_run
from installer.state_store import write_json
from installer.studio_api import _read_state, _write_installing, ApiError
from installer.task_runner import InstallationRunner
from installer.uninstall import prepare_uninstall, execute_uninstall
from installer.tests.test_control_plane import OpenBKN, hooks, DATABASE, NETWORK


def read_events(output):
    return [json.loads(line) for line in output.getvalue().splitlines()]


class DiagnosticFlowTest(unittest.TestCase):
    def test_failed_verification_then_retry_preserves_root_cause_and_skips_completed_hook(self):
        with tempfile.TemporaryDirectory() as tmp, redirect_stderr(io.StringIO()) as output:
            state = Path(tmp)
            runner = InstallationRunner(state, ['supply-chain'])
            client, seen = OpenBKN(), []
            def hook(stage, payload):
                seen.append(stage)
                if stage == 'platform-verify' and seen.count(stage) == 1:
                    return {'ok': False, 'message': 'ObjectQuery.BadMapping: material_code is missing'}
                return hooks(stage, payload)
            common = dict(sample='supply-chain', version='0.1.18', actor_role='admin', database=DATABASE,
                          state_dir=state, openbkn=client, hook_runner=hook,
                          expected_tables=12, knowledge_network=NETWORK, components={'metrics': False})
            runner.submit('supply-chain', lambda: _write_installing(state, 'supply-chain', '0.1.18'),
                          lambda: create_installation(**common))
            self.assertTrue(runner.locks['supply-chain'].acquire(timeout=2))
            runner.locks['supply-chain'].release()
            first = _read_state(state, 'supply-chain')
            self.assertEqual(first['status'], 'failed')
            runner.submit('supply-chain', lambda: None, lambda: retry_installation(**common))
            self.assertTrue(runner.locks['supply-chain'].acquire(timeout=2))
            runner.locks['supply-chain'].release()
            second = _read_state(state, 'supply-chain')
        self.assertEqual(second['status'], 'installed')
        self.assertNotEqual(first['attemptId'], second['attemptId'])
        self.assertEqual(seen.count('platform-install'), 1)
        events = read_events(output)
        first_events = [e for e in events if e['attempt_id'] == first['attemptId']]
        second_events = [e for e in events if e['attempt_id'] == second['attemptId']]
        self.assertTrue(any('ObjectQuery.BadMapping' in e.get('reason', '') for e in first_events))
        self.assertTrue(any(e['event'] == 'retry.started' and e['previous_attempt_id'] == first['attemptId'] for e in second_events))
        self.assertTrue(any(e['event'] == 'skipped' and e['step'] == 'platform-install' for e in second_events))

    def test_download_timeout_and_checksum_failure_name_the_target_and_reason(self):
        package = {'locations': ['https://github.com/openbkn-ai/bkn-samples/releases/download/test/package.tar.gz'],
                   'digest': 'sha256:' + hashlib.sha256(b'expected').hexdigest()}
        for timeout in (True, False):
            with self.subTest(timeout=timeout), tempfile.TemporaryDirectory() as tmp, redirect_stderr(io.StringIO()) as output:
                response = io.BytesIO(b'wrong bytes')
                response.status = 200
                if timeout:
                    response.read = Mock(side_effect=TimeoutError('package read timed out'))
                opener = Mock()
                opener.open.return_value = response
                destination = Path(tmp) / 'package.tar.gz'
                with diagnostics.context({'sample': 'example', 'attemptId': 'attempt-download'}), \
                        patch('installer.remote_bundle.build_opener', return_value=opener), self.assertRaises((TimeoutError, ValueError)):
                    download_package(package, destination)
                self.assertFalse(destination.exists())
            events = read_events(output)
            self.assertTrue(any(e['event'] == 'failed' for e in events))
            self.assertTrue(all(e['attempt_id'] == 'attempt-download' for e in events))
            self.assertIn('package.tar.gz', output.getvalue())
            self.assertIn('timed out' if timeout else 'digest mismatch', output.getvalue())

    def test_uninstall_caught_error_is_diagnosable_and_does_not_continue_deletion(self):
        with tempfile.TemporaryDirectory() as tmp, redirect_stderr(io.StringIO()) as output:
            state = Path(tmp)
            record = {'id': 'installed', 'sample': 'example', 'version': '1.0.0', 'attemptId': 'before',
                      'status': 'installed', 'catalogId': 'catalog', 'resources': {
                          'knowledgeNetworkId': 'network', 'ownedExecution': {'toolboxes': [], 'skills': []}}}
            write_json(state / 'example.json', record)
            runner = InstallationRunner(state, ['example'])
            def api(method, path, body=None):
                raise ApiError(503, 'upstream_unavailable', 'catalog lookup failed: HTTP 503')
            runner.submit('example', lambda: prepare_uninstall(state, 'example', 'installed', 'admin'),
                          lambda: execute_uninstall(state, 'example', api, lambda *_: self.fail('No deletion allowed')))
            self.assertTrue(runner.locks['example'].acquire(timeout=2))
            runner.locks['example'].release()
            current = _read_state(state, 'example')
        self.assertEqual(current['status'], 'uninstall_failed')
        failures = [e for e in read_events(output) if e['event'] == 'failed']
        self.assertTrue(any(e.get('error_code') == 'upstream_unavailable' for e in failures))
        self.assertTrue(any('HTTP 503' in e.get('reason', '') and e['attempt_id'] == current['attemptId'] for e in failures))

    @unittest.skipUnless(sys.platform == 'linux' and os.geteuid() == 0, 'requires Linux UID-switching runtime')
    def test_real_hook_subprocess_events_reach_parent_with_trusted_attempt(self):
        with tempfile.TemporaryDirectory() as tmp, redirect_stderr(io.StringIO()) as output:
            sample = Path(tmp) / 'sample'
            sample.mkdir()
            cli = sample / 'openbkn'
            cli.write_text('#!' + sys.executable + '\nimport sys\nprint("API denied synthetic-token",file=sys.stderr)\nsys.exit(1)\n')
            cli.chmod(0o755)
            script = sample / 'install.py'
            script.write_text('#!' + sys.executable + '\nfrom installer.sample_logging import run\nfrom pathlib import Path\nimport sys\n'
                              'p=run([str(Path(__file__).with_name("openbkn")),"--json","skill","publish","skill-test"],'
                              'capture_output=True,text=True)\nsys.exit(p.returncode)\n')
            script.chmod(0o755)
            with diagnostics.context({'sample': 'real', 'attemptId': 'trusted-attempt', 'version': '1.0.0'}):
                result = run_hook(sample, script, process_run, {'BKN_TOKEN': 'synthetic-token',
                                                               'BKN_SAMPLE_PHASE': 'platform-install'})
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('synthetic-token', output.getvalue())
        failures = [e for e in read_events(output) if e.get('source') == 'sample' and e['event'] == 'failed']
        self.assertTrue(any(e['step'] == 'sample.cli.skill.publish' and e['attempt_id'] == 'trusted-attempt'
                            and e['sample_id'] == 'real' and e['child_stage'] == 'capabilities' for e in failures))
