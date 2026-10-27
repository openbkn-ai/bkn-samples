from installer.contract import read_version
"""Shared runtime ownership and content-only offline delivery regressions."""
import io
import json
import tarfile
import subprocess
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock, patch

from installer import shared_database as db
from installer.deploy_database import DeployError
from installer.offline_bundle import OfflinePackages
from installer.remote_bundle import CAPABILITIES, extract_package, load_release
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

    def test_shared_package_enforces_online_archive_limit(self):
        from tools.publication import build_candidate
        from installer.remote_bundle import MAX_ARCHIVE
        self.assertEqual(build_candidate.MAX_ARCHIVE, MAX_ARCHIVE)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary).resolve()
            sample = ROOT / 'samples/order-basics'
            reference = build(sample, '0.1.3', output / 'reference', shared_database=True)
            size = (reference / 'package.tar.gz').stat().st_size
            with patch.object(build_candidate, 'MAX_ARCHIVE', size):
                accepted = build(sample, '0.1.3', output / 'boundary', shared_database=True)
                self.assertEqual((accepted / 'package.tar.gz').stat().st_size, size)
            with patch.object(build_candidate, 'MAX_ARCHIVE', size - 1):
                with self.assertRaisesRegex(ValueError, 'delivery size limit'):
                    build(sample, '0.1.3', output / 'oversize', shared_database=True)
            self.assertFalse((output / 'oversize' / sample.name / '0.1.3').exists())

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
            self.assertEqual(archive['sizeBytes'], package.stat().st_size)
            import tarfile
            with tarfile.open(package) as source:
                descriptor = json.load(source.extractfile('offline-release.json'))
            self.assertEqual(manifest['spec']['requires'], descriptor['requires'])
            self.assertTrue(archive['locations'][0].endswith('/package.tar.gz'))
            runtime = RemoteInstallation(ROOT, output / 'state', read_version(ROOT), 'arm64', CAPABILITIES,
                                         'registry.example/executor@sha256:' + 'a' * 64)
            packages = OfflinePackages(ROOT, output / 'state', runtime)
            imported = packages.import_package(package, 'admin')
            self.assertEqual(imported['version'], version)
            self.assertIsNone(packages.find(imported['sample'])['dataImageRef'])

    def test_package_with_experience_set_requires_the_capability(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary).resolve()
            with_set = build(ROOT / 'samples/supply_ontology_hand', '0.1.13', output / 'with', shared_database=True)
            without = build(ROOT / 'samples/order-basics', '0.1.3', output / 'without', shared_database=True)
            requires = {}
            for name, candidate in (('with', with_set), ('without', without)):
                with tarfile.open(candidate / 'package.tar.gz') as source:
                    requires[name] = json.load(source.extractfile('offline-release.json'))['requires']
            self.assertIn('sample.experience-set', requires['with']['capabilities'])
            self.assertNotIn('sample.experience-set', requires['without']['capabilities'])
            self.assertIn('sample.experience-set', CAPABILITIES)

    def test_release_requirements_follow_new_package_not_old_baseline(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sample = root / 'sample'
            baseline = sample / 'releases/0.1.2/sample.json'
            baseline.parent.mkdir(parents=True)
            previous = json.loads((ROOT / 'samples/order-basics/releases/0.1.2/sample.json').read_text())
            baseline.write_text(json.dumps(previous))
            candidate = root / 'candidate'
            candidate.mkdir()
            required = dict(previous['spec']['requires'], platformVersion='>=0.2.1 <0.3.0',
                            architectures=['arm64', 'amd64'], capabilities=[
                                'vega.catalog', 'knowledge-network.import.kn-json',
                                'execution.function', 'execution.skill', 'database.shared'])
            payload = json.dumps({'requires': required}).encode()
            package = candidate / 'package.tar.gz'
            with tarfile.open(package, 'w:gz') as archive:
                member = tarfile.TarInfo('offline-release.json')
                member.size = len(payload)
                archive.addfile(member, io.BytesIO(payload))
            (candidate / 'build.json').write_text(json.dumps({
                'package': {'digest': 'sha256:' + 'a' * 64, 'size': package.stat().st_size},
                'releaseNotes': []}))
            with patch('tools.publication.prepare_shared_release.build', return_value=candidate):
                result = prepare(sample, '0.1.3', root / 'output')
            manifest = json.loads(Path(result['manifest']).read_text())
            self.assertEqual(manifest['spec']['requires'], required)
            entry = dict(sampleId='order-basics', version='0.1.3', releaseStatus='published', requires=required)
            for missing in ('execution.function', 'execution.skill'):
                reader = Mock(side_effect=AssertionError('must reject before reading metadata'))
                with self.subTest(missing=missing), self.assertRaisesRegex(ValueError, 'required capability is unavailable'):
                    load_release(entry, ROOT / 'protocol/draft/schemas/sample.schema.json',
                                 '0.2.1', 'arm64', CAPABILITIES - {missing}, reader=reader)
                reader.assert_not_called()

    def test_content_only_package_imports_without_image_or_registry(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary).resolve()
            sample_dir = ROOT / 'samples/supply_ontology_hand'
            version = max((p.parent.name for p in sample_dir.glob('releases/*/release-notes.*.md')),
                          key=lambda value: tuple(map(int, value.split('.'))))
            candidate = build(sample_dir, version, output / 'build', shared_database=True)
            runtime = RemoteInstallation(ROOT, output / 'state', read_version(ROOT), 'arm64', CAPABILITIES,
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
