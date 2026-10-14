"""Recover accepted legacy attempts without reopening withdrawn new installs."""
import json
import tempfile
import threading
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from installer.contract import build_manifest_index, read_version
from installer.remote_catalog import merge_remote
from installer.remote_installation import RemoteInstallation
from installer.state_store import write_json
from installer.studio_api import ApiError, _read_state, list_samples
from installer.studio_http import main

ROOT = Path(__file__).resolve().parents[2]
IMAGE = 'ghcr.io/openbkn-ai/bkn-samples@sha256:' + 'a' * 64


class RecoveryTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.state = Path(directory.name)
        self.index = build_manifest_index(ROOT, 'a' * 40)
        self.item = next(i for i in self.index['samples'] if i['name'] == 'supply-chain')
        self.record = {'id': 'old-failed', 'sample': 'supply-chain', 'version': '0.2.0',
                       'status': 'failed', 'manifestSha256': self.item['manifestSha256'],
                       'dataImageRef': IMAGE, 'stages': {'database': 'succeeded', 'verify': 'failed'}}
        self.entries = json.loads((ROOT / 'catalog.json').read_text())['spec']['entries']
        self.stack = self.enterContext(ExitStack())
        env = {'BKN_SAMPLES_ROOT': str(ROOT), 'BKN_SAMPLE_STATE_DIR': str(self.state),
               'BKN_SAMPLE_PLATFORM_VERSION': '0.2.0', 'BKN_SAMPLE_EXECUTOR_IMAGE_REF': '',
               'BKN_SAMPLE_DATA_IMAGE_REF': IMAGE}
        self.stack.enter_context(patch.dict('os.environ', env))
        self.stack.enter_context(patch('installer.studio_api.load_indexes',
            return_value=(read_version(ROOT), self.index, self.index)))
        apps = []
        self.stack.enter_context(patch('installer.studio_http.serve', side_effect=lambda app, *args: apps.append(app)))
        from installer.deploy_database import _sample
        self.sample_lookup = self.stack.enter_context(patch('installer.deploy_database._sample', wraps=_sample))
        self.retry_runtime = self.stack.enter_context(patch('installer.runtime.retry_sample'))
        self.stack.enter_context(patch('installer.catalog_source.OfficialCatalog.entries', return_value=self.entries))
        main()
        self.app = apps[0]

    def test_legacy_failure_resumes_original_receipt_and_database_identity(self):
        write_json(self.state / 'supply-chain.json', self.record)
        calls, deployed = [], []
        finished = threading.Event()
        def run(**kwargs):
            calls.append(kwargs['version'])
            kwargs['deploy']('supply-chain')
            current = _read_state(self.state, 'supply-chain')
            current['status'] = 'installed'
            write_json(self.state / 'supply-chain.json', current)
            finished.set()
        self.retry_runtime.side_effect = run
        with patch('installer.runtime.deploy_database', side_effect=lambda *args, **kwargs: deployed.append(kwargs)):
            accepted = self.app.retry('supply-chain', 'old-failed', 'admin', 'Bearer test')
            self.assertEqual(accepted['version'], '0.2.0')
            self.assertTrue(finished.wait(2))
        self.assertEqual(calls, ['0.2.0'])
        self.assertEqual(deployed[0]['sample_release_version'], '0.2.0')
        self.assertEqual(deployed[0]['data_image_ref'], IMAGE)
        self.assertTrue(deployed[0]['require_ownership'])
        self.assertEqual(_read_state(self.state, 'supply-chain')['version'], '0.2.0')
        history = list((self.state / 'history' / 'supply-chain').glob('*.json'))
        # Recovery does not rewrite the saved failed attempt.
        self.assertTrue(history)
        self.assertTrue(any(json.loads(p.read_text()) == self.record for p in history))

    def test_changed_or_unproven_artifacts_remain_rejected_before_state_changes(self):
        for changes in ({'version': '0.3.0'}, {'manifestSha256': ''},
                        {'manifestSha256': 'b' * 64}, {'dataImageRef': IMAGE.replace('a' * 64, 'b' * 64)}):
            with self.subTest(changes=changes):
                record = {**self.record, **changes}
                write_json(self.state / 'supply-chain.json', record)
                with self.assertRaises(ApiError) as rejected:
                    self.app.retry('supply-chain', 'old-failed', 'admin', 'Bearer test')
                self.assertEqual(rejected.exception.code, 'version_changed')
                self.assertEqual(_read_state(self.state, 'supply-chain'), record)

    def test_explicit_sample_version_is_not_treated_as_old_service_bug(self):
        write_json(self.state / 'supply-chain.json', self.record)
        from installer.deploy_database import _sample
        directory, document = _sample(ROOT, 'supply-chain')
        document['metadata']['version'] = '0.1.0'
        self.sample_lookup.return_value = (directory, document)
        with self.assertRaises(ApiError) as rejected:
            self.app.retry('supply-chain', 'old-failed', 'admin', 'Bearer test')
        self.assertEqual(rejected.exception.code, 'version_changed')
        self.assertEqual(_read_state(self.state, 'supply-chain'), self.record)

    def test_withdrawn_fallback_is_disabled_and_both_new_install_routes_reject(self):
        result = list_samples(pinned_version=read_version(ROOT), image_index=self.index,
                             repo_index=self.index, state_dir=self.state, actor_role='admin')
        runtime = RemoteInstallation(ROOT, self.state, '0.2.0', 'arm64', [], '')
        merge_remote(result, self.entries, self.state, 'admin', runtime)
        card = next(c for c in result['samples'] if c['name'] == 'world-cup')
        self.assertEqual(card['version'], '0.1.0')
        self.assertFalse(card['installable'])
        self.assertEqual(card['code'], 'release_withdrawn')
        view = next(v for v in card['versions'] if v['version'] == '0.1.0')
        self.assertEqual(view['reason'], 'release_withdrawn')
        digest = next(i for i in self.index['samples'] if i['name'] == 'world-cup')['manifestSha256']
        for create in (lambda: self.app.create('world-cup', 'admin', 'Bearer test'),
                       lambda: self.app.create_selected('world-cup', 'admin', 'Bearer test', '0.1.0', digest)):
            with self.assertRaises(ApiError) as rejected:
                create()
            self.assertEqual(rejected.exception.code, 'release_withdrawn')
            self.assertFalse((self.state / 'world-cup.json').exists())
