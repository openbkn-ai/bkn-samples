"""Shared runtime ownership and content-only offline delivery regressions."""
import json
import subprocess
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock, patch

from installer import shared_database as db
from installer.deploy_database import DeployError
from installer.offline_bundle import OfflinePackages
from installer.remote_bundle import CAPABILITIES, extract_package
from installer.remote_installation import RemoteInstallation
from installer.state_store import write_json
from installer.studio_api import _read_state, _write_failed
from tools.publication.build_candidate import build
from tools.publication.prepare_shared_release import prepare

ROOT = Path(__file__).resolve().parents[2]


class SharedDatabaseTest(unittest.TestCase):
    def fixture(self, state):
        record = {"sample": "supply-chain", "version": "0.1.6", "status": "installing", "stages": {}}
        write_json(state / "supply-chain.json", record)
        return record

    def config(self):
        return {"host": "product-sample-database", "port": 3306, "database": "sample_registry"}

    @contextmanager
    def manager(self, receipt):
        yield self.cursor

    def test_loaders_receive_scoped_credentials_and_retry_keeps_ownership(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            self.fixture(state)
            self.cursor = Mock()
            self.cursor.fetchone.return_value = None
            run = Mock(return_value=subprocess.CompletedProcess([], 0))
            with patch.object(db, 'settings', self.config), patch.object(db, 'manager', self.manager), \
                 patch.object(db, '_owner', return_value=None), patch.object(db, '_schemas', return_value=set()):
                result = db.prepare(ROOT, 'supply-chain', '0.1.6', state, run)
            record = _read_state(state, 'supply-chain')
            receipt = record['databaseRuntime']
            self.assertEqual(result['host'], 'product-sample-database')
            self.assertEqual(len(run.call_args_list), 2)
            environment = run.call_args_list[0].args[1]
            self.assertEqual(environment['MYSQL_ADMIN_DATABASE'], 'supply_demo_hand')
            self.assertNotEqual(environment['MYSQL_USER'], 'root')
            self.assertNotIn(result['password'], json.dumps(record))
            grants = [call.args[0] for call in self.cursor.execute.call_args_list if call.args[0].startswith('GRANT')]
            self.assertEqual(len(grants), 2)
            self.assertIn('`supply\\_demo\\_hand`.*', grants[0])
            owner = ('supply-chain', '0.1.6', receipt['ownership'], receipt['user'], False)
            with patch.object(db, 'settings', self.config), patch.object(db, 'manager', self.manager), \
                 patch.object(db, '_owner', return_value=owner), patch.object(db, '_schemas', return_value={receipt['name']}):
                self.assertEqual(db.prepare(ROOT, 'supply-chain', '0.1.6', state, run), result)
            self.assertEqual(_read_state(state, 'supply-chain')['databaseRuntime'], receipt)
            _write_failed(state, 'supply-chain', '0.1.6', 'database_not_ready', 'retry')
            self.assertEqual(_read_state(state, 'supply-chain')['databaseRuntime'], receipt)

    def test_existing_or_reserved_database_is_never_adopted(self):
        for reserved in (False, True):
            with self.subTest(reserved=reserved), tempfile.TemporaryDirectory() as temporary:
                state = Path(temporary)
                self.fixture(state)
                self.cursor = Mock()
                self.cursor.fetchone.return_value = ('other_loading',) if reserved else None
                with patch.object(db, 'settings', self.config), patch.object(db, 'manager', self.manager), \
                     patch.object(db, '_owner', return_value=None), patch.object(db, '_schemas', return_value={'supply_demo_hand'}), \
                     self.assertRaises(DeployError) as error:
                    db.prepare(ROOT, 'supply-chain', '0.1.6', state, Mock())
                self.assertEqual(error.exception.code, 'ownership_conflict')
                self.assertFalse(any(call.args[0].startswith(('CREATE DATABASE', 'DROP', 'GRANT')) for call in self.cursor.execute.call_args_list))

    def test_missing_registry_owner_prevents_uninstall_deletion(self):
        self.cursor = Mock()
        receipt = dict(kind=db.KIND, name='sample_db', staging='sample_db_loading', host='db', port=3306,
                       user='sample_user', ownership='a' * 32)
        with patch.object(db, 'manager', self.manager), patch.object(db, '_owner', return_value=None), \
             patch.object(db, '_schemas', return_value={'sample_db'}), \
             self.assertRaises(DeployError):
            db.remove(dict(sample='sample', version='0.1.0', databaseRuntime=receipt))
        self.assertFalse(any(call.args[0].startswith('DROP') for call in self.cursor.execute.call_args_list))

    def test_release_uses_one_self_contained_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary).resolve()
            sample_dir = ROOT / 'samples/order-basics'
            version = '0.1.3'
            result = prepare(sample_dir, version, output / 'build')
            package = Path(result['package'])
            self.assertEqual(package.name, 'package.tar.gz')
            self.assertEqual(list((output / 'build').rglob('*.tar.gz')), [package])
            manifest = json.loads(Path(result['manifest']).read_text())
            report = json.loads((package.parent / 'build.json').read_text())
            archive = manifest['spec']['artifacts'][0]
            self.assertEqual(len(manifest['spec']['artifacts']), 1)
            self.assertEqual(archive['digest'], report['package']['digest'])
            self.assertTrue(archive['locations'][0].endswith('/package.tar.gz'))
            runtime = RemoteInstallation(ROOT, output / 'state', '0.2.0', 'arm64', CAPABILITIES,
                                         'registry.example/executor@sha256:' + 'a' * 64)
            packages = OfflinePackages(ROOT, output / 'state', runtime)
            imported = packages.import_package(package, 'admin')
            self.assertEqual(imported['version'], version)
            self.assertIsNone(packages.find(imported['sample'])['dataImageRef'])

    def test_content_only_package_imports_without_image_or_registry(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary).resolve()
            sample_dir = ROOT / 'samples/supply_ontology_hand'
            version = max((p.parent.name for p in sample_dir.glob('releases/*/release-notes.*.md')),
                          key=lambda value: tuple(map(int, value.split('.'))))
            candidate = build(sample_dir, version, output / 'build', shared_database=True)
            runtime = RemoteInstallation(ROOT, output / 'state', '0.2.0', 'arm64', CAPABILITIES,
                                         'registry.example/executor@sha256:' + 'a' * 64)
            packages = OfflinePackages(ROOT, output / 'state', runtime)
            imported = packages.import_package(candidate / 'package.tar.gz', 'admin')
            release = packages.find(imported['sample'])
            self.assertIsNone(release['dataImageRef'])
            packages.prepare(release)
            seen = []
            packages.execute(release, lambda root, version, image, retry: seen.append((version, image)))
            self.assertEqual(seen, [(version, None)])
            import tarfile
            with tarfile.open(candidate / 'package.tar.gz') as archive:
                self.assertFalse(any(member.name.startswith('runtime/') for member in archive))
