import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from installer.offline_image import file_sha, validate_layout
from installer.deploy_database import deploy_database, DeployError
from installer.offline_bundle import OfflinePackages
from installer.remote_installation import RemoteInstallation
from installer.tests.test_deploy_database import FakeKubectl
from tools.publication.build_candidate import build

ROOT = Path(__file__).resolve().parents[2]


def image_fixture(directory):
    """Small, complete OCI fixture. No mocked digest verification."""
    directory.mkdir(parents=True)
    blobs = directory / 'blobs/sha256'
    blobs.mkdir(parents=True)

    def blob(value, media):
        data = value if isinstance(value, bytes) else json.dumps(value).encode()
        digest = hashlib.sha256(data).hexdigest()
        (blobs / digest).write_bytes(data)
        return {'mediaType': media, 'size': len(data), 'digest': 'sha256:' + digest}

    layer = blob(b'embedded fixture layer', 'application/vnd.oci.image.layer.v1.tar')
    manifests = []
    for arch in ('arm64', 'amd64'):
        config = blob({'architecture': arch, 'os': 'linux'}, 'application/vnd.oci.image.config.v1+json')
        manifest = blob({'schemaVersion': 2, 'config': config, 'layers': [layer]},
                        'application/vnd.oci.image.manifest.v1+json')
        manifest['platform'] = {'architecture': arch, 'os': 'linux'}
        manifests.append(manifest)
    root = blob({'schemaVersion': 2, 'manifests': manifests}, 'application/vnd.oci.image.index.v1+json')
    ref = 'ghcr.io/openbkn-ai/bkn-samples@' + root['digest']
    root['annotations'] = {'org.opencontainers.image.ref.name': ref}
    (directory / 'index.json').write_text(json.dumps({'schemaVersion': 2, 'manifests': [root]}))
    (directory / 'oci-layout').write_text(json.dumps({'imageLayoutVersion': '1.0.0'}))
    return ref, blobs / layer['digest'][7:]


class OfflineImageTest(unittest.TestCase):
    def test_complete_layout_passes_without_network(self):
        with tempfile.TemporaryDirectory() as temporary, patch('socket.socket', side_effect=AssertionError('network forbidden')):
            layout = Path(temporary) / 'oci'
            ref, _ = image_fixture(layout)
            self.assertEqual(validate_layout(layout, ref, ['arm64', 'amd64']), {'arm64', 'amd64'})

    def test_preparation_registers_fully_qualified_names_without_pull(self):
        from installer.offline_image import main
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ref, _ = image_fixture(root / 'runtime/oci')
            (root / 'offline-release.json').write_text(json.dumps({
                'apiVersion': 'samples.openbkn.ai/offline.v2', 'dataImageRef': ref,
                'requires': {'architectures': ['arm64', 'amd64']}}))
            observed = []
            def run(args, **kwargs):
                observed.append(args)
                if 'import' in args:
                    import tarfile
                    with tarfile.open(fileobj=kwargs['stdin']) as archive:
                        self.assertIn('index.json', archive.getnames())
                return subprocess.CompletedProcess(args, 0, stdout=ref + '\n')
            with patch('installer.offline_image.__file__', str(root / 'runtime/prepare_offline.py')), \
                 patch('sys.argv', ['prepare_offline.py']), \
                 patch('installer.offline_image.subprocess.run', side_effect=run):
                main()
            self.assertIn('--base-name', observed[0])
            self.assertEqual(observed[0][observed[0].index('--base-name') + 1], ref.split('@')[0])
            self.assertNotIn('--no-unpack', observed[0])
            self.assertFalse(any('pull' in args for args in observed))

    def test_missing_or_corrupt_layer_is_rejected(self):
        for missing in (True, False):
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as temporary:
                layout = Path(temporary) / 'oci'
                ref, layer = image_fixture(layout)
                layer.unlink() if missing else layer.write_bytes(b'corrupt')
                with self.assertRaises(ValueError):
                    validate_layout(layout, ref, ['arm64'])

    def test_external_blob_url_is_rejected_without_requesting_it(self):
        with tempfile.TemporaryDirectory() as temporary, patch('socket.socket', side_effect=AssertionError('network forbidden')):
            layout = Path(temporary) / 'oci'
            ref, _ = image_fixture(layout)
            index = json.loads((layout / 'index.json').read_text())
            index['manifests'][0]['urls'] = ['https://example.invalid/image']
            (layout / 'index.json').write_text(json.dumps(index))
            with self.assertRaisesRegex(ValueError, 'external OCI'):
                validate_layout(layout, ref, [])

    def test_legacy_url_only_package_is_not_accepted_as_offline(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'offline-release.json').write_text(json.dumps({'apiVersion': 'samples.openbkn.ai/offline.v1'}))
            with self.assertRaisesRegex(ValueError, 'self-contained'):
                OfflinePackages(ROOT, root / 'state', None).inspect(root, 'sha256:' + 'a' * 64)

    def test_wrong_digest_architecture_and_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            layout = Path(temporary) / 'oci'
            ref, layer = image_fixture(layout)
            with self.assertRaises(ValueError):
                validate_layout(layout, ref[:-1] + ('0' if ref[-1] != '0' else '1'), [])
            with self.assertRaises(ValueError):
                validate_layout(layout, ref, ['riscv64'])
            layer.rename(layer.with_suffix('.original'))
            layer.symlink_to(layer.with_suffix('.original'))
            with self.assertRaises(ValueError):
                validate_layout(layout, ref, [])

    def test_offline_deploy_never_queries_registry_or_falls_back(self):
        image = 'ghcr.io/openbkn-ai/bkn-samples@sha256:' + 'a' * 64
        kubectl = FakeKubectl()
        with patch('installer.deploy_database.registry_digests', side_effect=AssertionError('registry forbidden')):
            deploy_database(ROOT, 'supply-chain', kubectl, data_image_ref=image, offline=True, attempts=1)
        workload = next(d for d in yaml.safe_load_all(kubectl.applied[0]) if d['kind'] == 'StatefulSet')
        self.assertEqual(workload['spec']['template']['spec']['containers'][0]['imagePullPolicy'], 'Never')
        self.assertFalse(kubectl.patched)

    def test_missing_local_image_fails_without_network_fallback(self):
        image = 'ghcr.io/openbkn-ai/bkn-samples@sha256:' + 'a' * 64
        kubectl = FakeKubectl(states=['image_pull_failed'])
        with patch('installer.deploy_database.registry_digests', side_effect=AssertionError('registry forbidden')):
            with self.assertRaises(DeployError) as caught:
                deploy_database(ROOT, 'supply-chain', kubectl, data_image_ref=image, offline=True, attempts=1)
        self.assertEqual(caught.exception.code, 'offline_image_missing')
        self.assertFalse(kubectl.patched)

    def test_offline_deploy_requires_fixed_image(self):
        with patch('installer.deploy_database.configured_image_ref', return_value=None), \
             patch('installer.deploy_database.registry_digests', side_effect=AssertionError('registry forbidden')):
            with self.assertRaises(DeployError) as caught:
                deploy_database(ROOT, 'supply-chain', FakeKubectl(), offline=True)
        self.assertEqual(caught.exception.code, 'offline_image_missing')

    def test_builder_refuses_url_only_offline_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, 'self-contained'):
                build(ROOT / 'samples/supply_ontology_hand', '0.1.2', Path(temporary),
                      'ghcr.io/openbkn-ai/bkn-samples@sha256:' + 'a' * 64)

    def test_self_contained_package_import_and_retry_revalidate_local_layers(self):
        with tempfile.TemporaryDirectory() as temporary, patch('socket.socket', side_effect=AssertionError('network forbidden')):
            temporary = Path(temporary).resolve()
            ref, _ = image_fixture(temporary / 'oci')
            candidate = build(ROOT / 'samples/supply_ontology_hand', '0.1.2', temporary / 'out', ref, temporary / 'oci')
            runtime = RemoteInstallation(ROOT, temporary / 'state', '0.2.0', 'arm64',
                ['vega.catalog', 'knowledge-network.import.kn-json', 'execution.function', 'execution.skill'],
                'ghcr.io/openbkn-ai/executor@sha256:' + 'e' * 64)
            offline = OfflinePackages(ROOT, temporary / 'state', runtime)
            offline.import_package(candidate / 'offline-package.tar.gz', 'admin')
            release = offline.find('supply-chain')
            observed = []
            offline.execute(release, lambda root, version, image, retry: observed.append((version, image, retry)))
            offline.execute(release, lambda root, version, image, retry: observed.append((version, image, retry)), retry=True)
            self.assertEqual(observed, [('0.1.2', ref, False), ('0.1.2', ref, True)])
            cached = offline.directory / 'supply-chain/package.tar.gz'
            cached.write_bytes(b'corrupt')
            with self.assertRaises(ValueError):
                offline.execute(release, lambda *args: self.fail('must not execute invalid package'), retry=True)

    def test_real_offline_http_install_and_retry_both_forbid_pulling(self):
        from installer.contract import build_manifest_index, read_version
        from installer.studio_http import main
        from installer.studio_api import _read_state
        from installer.task_runner import InstallationRunner
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary).resolve()
            ref, _ = image_fixture(temporary / 'oci')
            candidate = build(ROOT / 'samples/supply_ontology_hand', '0.1.4', temporary / 'out', ref, temporary / 'oci')
            apps, runners = [], []
            def make_runner(*args):
                runner = InstallationRunner(*args)
                runners.append(runner)
                return runner
            state = temporary / 'state'
            env = {'BKN_SAMPLES_ROOT': str(ROOT), 'BKN_SAMPLE_STATE_DIR': str(state),
                   'BKN_SAMPLE_PLATFORM_VERSION': '0.2.0', 'BKN_SAMPLE_PLATFORM_CAPABILITIES': '',
                   'BKN_SAMPLE_DATA_IMAGE_REF': '',
                   'BKN_SAMPLE_EXECUTOR_IMAGE_REF': 'ghcr.io/openbkn-ai/executor@sha256:' + 'e' * 64}
            index = build_manifest_index(ROOT, 'a' * 40)
            with patch.dict('os.environ', env), \
                 patch('installer.studio_http.serve', side_effect=lambda app, *args: apps.append(app)), \
                 patch('installer.task_runner.InstallationRunner', side_effect=make_runner), \
                 patch('installer.studio_api.load_indexes', return_value=(read_version(ROOT), index, index)), \
                 patch('installer.deploy_database.deploy_database', side_effect=DeployError('offline_image_missing', 'not present')) as deploy, \
                 patch('installer.catalog_source.read_url', side_effect=AssertionError('catalog network forbidden')):
                main()
                app = apps[0]
                app.import_package(candidate / 'offline-package.tar.gz', 'admin')
                release = OfflinePackages(ROOT, state, None).find('supply-chain')
                app.create_selected('supply-chain', 'admin', None, '0.1.4', release['manifestSha256'])
                self.assertTrue(runners[0].locks['supply-chain'].acquire(timeout=5))
                runners[0].locks['supply-chain'].release()
                first = _read_state(state, 'supply-chain')
                self.assertEqual(first['status'], 'failed')
                app.retry('supply-chain', first['id'], 'admin', None)
                self.assertTrue(runners[0].locks['supply-chain'].acquire(timeout=5))
                runners[0].locks['supply-chain'].release()
                self.assertEqual(_read_state(state, 'supply-chain')['error']['code'], 'offline_image_missing')
                self.assertEqual(deploy.call_count, 2)
                for call in deploy.call_args_list:
                    self.assertTrue(call.kwargs['offline'])
                    self.assertEqual(call.kwargs['data_image_ref'], ref)
