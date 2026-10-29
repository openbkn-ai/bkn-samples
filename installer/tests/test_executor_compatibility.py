import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from installer.executor_compatibility import ExecutorCompatibility, ExecutorCompatibilityError, cli_capabilities
from installer.remote_installation import RemoteInstallation
from installer.remote_catalog import merge_remote
from installer.state_store import write_json
from installer.studio_api import ApiError

ROOT = Path(__file__).resolve().parents[2]
ENTRY = copy.deepcopy(next(e for e in json.loads((ROOT / 'catalog.json').read_text())['spec']['entries']
             if e['manifest']['digest'] == 'sha256:147cfecf87311bcdd0cb09bb88490c630e20aac7dbab8fc0441958258b46d281'))
# Exercise SDK compatibility independently of the live release retirement policy.
ENTRY['releaseStatus'] = 'published'
ENTRY.pop('withdrawalReason', None)


class ExecutorCompatibilityTest(unittest.TestCase):
    def runtime(self, state):
        return RemoteInstallation(ROOT, state, '0.2.1', 'arm64', ENTRY['requires']['capabilities'],
                                  'example.test/executor@sha256:' + 'a' * 64)

    def test_default_sdk_blocks_card_and_prepare_before_state_or_resources(self):
        with tempfile.TemporaryDirectory() as d, patch('installer.executor_compatibility.cli_capabilities', return_value=False) as probe:
            state = Path(d)
            runtime = self.runtime(state)
            card = merge_remote({'samples': []}, [ENTRY], state, 'admin', runtime)['samples'][0]
            self.assertFalse(card['installable'])
            self.assertIn('legacy', card['compatibilityMessage'])
            self.assertIn('legacy', card['message'])
            for _ in range(2):
                with self.assertRaises(ApiError) as error:
                    runtime.prepare(ENTRY)
                self.assertEqual(error.exception.status, 409)
                self.assertIn('legacy', error.exception.message)
            self.assertEqual(list(state.iterdir()), [])
            probe.assert_called_once()

    def test_digest_identity_not_name_and_platform_range_not_narrowed(self):
        renamed = copy.deepcopy(ENTRY)
        renamed['sampleId'] = 'different-name'
        with patch('installer.executor_compatibility.cli_capabilities', return_value=True) as probe:
            compatibility = ExecutorCompatibility()
            compatibility.require(renamed)
            compatibility.require(ENTRY)
            self.assertEqual(probe.call_count, 10)
        renamed['manifest']['digest'] = 'sha256:' + 'b' * 64
        with patch('installer.executor_compatibility.cli_capabilities') as probe:
            ExecutorCompatibility().require(renamed)
            probe.assert_not_called()

    def test_failed_probe_is_cached_and_fails_closed(self):
        with patch('installer.executor_compatibility.cli_capabilities', return_value=False) as probe:
            guard = ExecutorCompatibility()
            for _ in range(3):
                with self.assertRaises(ExecutorCompatibilityError):
                    guard.require(ENTRY)
            probe.assert_called_once()

    def test_retry_of_old_receipt_without_new_metadata_is_blocked_unchanged(self):
        with tempfile.TemporaryDirectory() as d, patch('installer.executor_compatibility.cli_capabilities', return_value=False):
            state = Path(d); runtime = self.runtime(state)
            receipt = {'id': 'old-install', 'sample': ENTRY['sampleId'], 'version': ENTRY['version'],
                       'status': 'failed', 'stages': {}, 'remoteRelease': {'entry': ENTRY,
                       'executorDigest': runtime.executor_digest, 'executorImage': runtime.executor_image}}
            file = state / (ENTRY['sampleId'] + '.json'); write_json(file, receipt)
            before = file.read_bytes()
            with self.assertRaises(ApiError): runtime.prepare_retry(ENTRY['sampleId'], 'old-install')
            self.assertEqual(file.read_bytes(), before)

    def test_installed_receipt_retains_uninstall_and_resource_identity(self):
        with tempfile.TemporaryDirectory() as d, patch('installer.executor_compatibility.cli_capabilities', return_value=False):
            state = Path(d); runtime = self.runtime(state)
            receipt = {'id':'existing', 'sample':ENTRY['sampleId'], 'version':ENTRY['version'], 'status':'installed',
                       'stages':{}, 'resources':{'knowledgeNetworkId':'owned-kn','ownedExecution':{'toolboxes':[],'skills':[]}}, 'remoteRelease':{'entry':ENTRY}}
            file=state/(ENTRY['sampleId']+'.json');write_json(file,receipt);before=file.read_bytes()
            card=merge_remote({'samples':[]},[ENTRY],state,'admin',runtime)['samples'][0]
            self.assertEqual(card['status'],'installed')
            self.assertFalse(card['installable'])
            self.assertTrue(card['canUninstall'])
            self.assertEqual(file.read_bytes(),before)

    def test_withdrawn_legacy_release_blocks_install_but_keeps_owned_uninstall(self):
        entry = copy.deepcopy(ENTRY)
        entry['releaseStatus'] = 'withdrawn'
        entry['withdrawalReason'] = 'Replaced by a corrected archive'
        with tempfile.TemporaryDirectory() as d, patch('installer.executor_compatibility.cli_capabilities') as probe:
            state = Path(d); runtime = self.runtime(state)
            receipt = {'id': 'existing', 'sample': entry['sampleId'], 'version': entry['version'],
                       'status': 'installed', 'stages': {}, 'resources': {'knowledgeNetworkId': 'owned-kn',
                       'ownedExecution': {'toolboxes': [], 'skills': []}},
                       'remoteRelease': {'entry': entry}}
            file = state / (entry['sampleId'] + '.json'); write_json(file, receipt); before = file.read_bytes()
            card = merge_remote({'samples': []}, [entry], state, 'admin', runtime)['samples'][0]
            self.assertFalse(card['installable'])
            self.assertTrue(card['canUninstall'])
            self.assertEqual(card['status'], 'installed')
            with self.assertRaises(ApiError) as error:
                runtime.prepare(entry)
            self.assertIn('withdrawn', error.exception.message)
            self.assertEqual(file.read_bytes(), before)
            probe.assert_not_called()

    def test_probe_uses_executor_path_clean_environment_and_bounded_local_command(self):
        valid = "Usage: openbkn bkn metric [options] [command]\nCommands:\n  list <kn>\n  create <kn>\n  query <kn> <id>\n"
        for output, code, expected in [(valid,0,True),(valid.replace('Usage: ', 'USAGE\n  '),0,True),(valid,1,False),('Usage: openbkn bkn [options] [command]',0,False),('untrusted text',0,False)]:
            with self.subTest(output=output,code=code), patch('installer.executor_compatibility.shutil.which',return_value='/executor/bin/openbkn'), patch('installer.executor_compatibility.subprocess.run',return_value=Mock(stdout=output,returncode=code)) as run:
                self.assertEqual(cli_capabilities(('bkn','metric'),('list','create','query')),expected)
                args,kwargs=run.call_args
                self.assertEqual(args[0],['/executor/bin/openbkn','bkn','metric','--help'])
                self.assertEqual(kwargs['timeout'],5)
                self.assertNotIn('BKN_TOKEN',kwargs['env'])
                self.assertNotIn('BKN_BASE_URL',kwargs['env'])
                self.assertEqual(kwargs['cwd'],kwargs['env']['HOME'])

    def test_actual_cli_help_fixtures_accept_legacy_sdks_and_reject_parent_help(self):
        for name, expected in [('sdk014', True), ('sdk020', True), ('sdk021', False)]:
            content = (ROOT / 'installer/tests/fixtures/cli-help' / (name + '.txt')).read_text()
            with self.subTest(sdk=name), patch('installer.executor_compatibility.shutil.which', return_value='/executor/bin/openbkn'), patch('installer.executor_compatibility.subprocess.run', return_value=Mock(stdout=content, returncode=0)):
                self.assertEqual(cli_capabilities(('bkn', 'metric'), ('list', 'create', 'query')), expected)

    def test_invalid_manifest_identity_fails_closed(self):
        for entry in [None, [], {}, {'manifest': []}, {'manifest': {'digest': []}}]:
            with self.subTest(entry=entry), self.assertRaises(ExecutorCompatibilityError):
                ExecutorCompatibility().require(entry)

    def test_existing_uninstall_failure_keeps_specific_error_code_and_message(self):
        with tempfile.TemporaryDirectory() as d, patch('installer.executor_compatibility.cli_capabilities', return_value=False):
            state = Path(d); runtime = self.runtime(state)
            receipt = {'id': 'existing', 'sample': ENTRY['sampleId'], 'version': ENTRY['version'],
                       'status': 'uninstall_failed', 'operation': 'uninstall', 'stages': {},
                       'error': {'code': 'uninstall_proxy_sync_timeout', 'message': 'Proxy sync timed out'}}
            write_json(state / (ENTRY['sampleId'] + '.json'), receipt)
            old = {'name': ENTRY['sampleId'], 'version': ENTRY['version'], 'status': 'uninstall_failed',
                   'code': 'uninstall_proxy_sync_timeout', 'message': 'Proxy sync timed out',
                   'installable': False, 'canUninstall': True, 'versions': [{'version': ENTRY['version']}]}
            card = merge_remote({'samples': [old]}, [ENTRY], state, 'admin', runtime)['samples'][0]
            self.assertEqual(card['code'], 'uninstall_proxy_sync_timeout')
            self.assertEqual(card['message'], 'Proxy sync timed out')
            self.assertTrue(card['canUninstall'])
            self.assertFalse(card['installable'])
            self.assertIn('legacy', card['compatibilityMessage'])

    def test_sdk_with_metrics_but_missing_capability_attach_is_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as d, patch('installer.executor_compatibility.cli_capabilities', side_effect=lambda command, operations, **kwargs: command != ('bkn', 'capability')):
            state = Path(d); runtime = self.runtime(state)
            with self.assertRaises(ApiError) as error:
                runtime.prepare(ENTRY)
            self.assertIn('bkn capability', error.exception.message)
            self.assertEqual(list(state.iterdir()), [])

    def test_unrelated_generic_compatibility_failure_keeps_existing_bundled_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            state = Path(d); runtime = self.runtime(state)
            entry = copy.deepcopy(ENTRY); entry['manifest']['digest'] = 'sha256:' + 'b' * 64
            old = {'name': entry['sampleId'], 'version': entry['version'], 'status':'not_installed',
                   'installable':True, 'message':'', 'versions':[{'version':entry['version']}]}
            with patch.object(runtime, 'require_executor', side_effect=ValueError('generic mismatch')):
                card = merge_remote({'samples':[old]}, [entry], state, 'admin', runtime)['samples'][0]
            self.assertTrue(card['installable'])
            self.assertEqual(card['message'], '')

    def test_probe_budget_is_global_across_all_command_groups(self):
        with patch('installer.executor_compatibility.time.monotonic', side_effect=[10, 10, 16]), patch('installer.executor_compatibility.cli_capabilities', return_value=True) as probe:
            with self.assertRaises(ExecutorCompatibilityError):
                ExecutorCompatibility().require(ENTRY)
            probe.assert_called_once()
            self.assertEqual(probe.call_args.kwargs['timeout'], 5)

    def test_complete_original_executor_help_matrix_and_sdk014_rejection(self):
        for name, accepted in [('original235-groups', True), ('sdk014-groups', False)]:
            groups = json.loads((ROOT / 'installer/tests/fixtures/cli-help' / (name + '.json')).read_text())
            outputs = {tuple(row['command']): row for row in groups}
            def run(args, **kwargs):
                row = outputs[tuple(args[1:-1])]
                return Mock(stdout=row['stdout'], returncode=row['exit'])
            with self.subTest(executor=name), patch('installer.executor_compatibility.shutil.which', return_value='/executor/bin/openbkn'), patch('installer.executor_compatibility.subprocess.run', side_effect=run):
                if accepted:
                    ExecutorCompatibility().require(ENTRY)
                else:
                    with self.assertRaisesRegex(ExecutorCompatibilityError, 'bkn capability'):
                        ExecutorCompatibility().require(ENTRY)
