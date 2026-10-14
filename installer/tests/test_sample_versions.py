"""Service upgrades must not relabel sample artifacts or their installation state."""
import json
import tempfile
import unittest
import yaml
from pathlib import Path
from unittest.mock import patch

from installer.contract import ContractError, build_manifest_index, validate_repository
from installer.studio_api import get_sample_release_notes, list_samples
from installer.release import merge_catalog
from installer.tests.test_contract import base_document, write_sample
from installer.tests.test_deploy_database import FakeKubectl, DIGEST
from installer.deploy_database import deploy_database


class SampleVersionTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / 'VERSION').write_text('0.2.0\n')
        (self.root / 'samples').mkdir()
        self.document = base_document()
        self.document['metadata']['version'] = '1.4.2'
        write_sample(self.root, 'fixture', self.document)
        folder = self.root / 'samples/fixture/releases/1.4.2'
        folder.mkdir(parents=True)
        (folder / 'release-notes.en-US.md').write_text('Sample notes, not service notes.\n')

    def index(self):
        return build_manifest_index(self.root, 'a' * 40)

    def test_service_upgrade_preserves_declared_sample_version_digest_and_notes(self):
        before = self.index()
        (self.root / 'VERSION').write_text('0.3.0\n')
        after = self.index()
        self.assertEqual(before['version'], '0.2.0')
        self.assertEqual(after['version'], '0.3.0')
        self.assertEqual(before['samples'], after['samples'])
        self.assertEqual(after['samples'][0]['version'], '1.4.2')
        self.assertEqual(after['samples'][0]['releaseNotes']['version'], '1.4.2')

    def test_card_and_notes_use_sample_version_and_preserve_existing_receipt(self):
        index = self.index()
        state = self.root / 'state'
        state.mkdir()
        receipt = {'id': 'installed-fixture', 'sample': 'fixture', 'version': '1.4.2',
                   'status': 'installed', 'stages': {'verify': 'succeeded'}}
        (state / 'fixture.json').write_text(json.dumps(receipt))
        result = list_samples(pinned_version='0.2.0', image_index=index, repo_index=index,
                              state_dir=state, actor_role='admin')
        self.assertEqual(result['version'], '0.2.0')
        self.assertEqual(result['samples'][0]['version'], '1.4.2')
        self.assertEqual(result['samples'][0]['installedVersion'], '1.4.2')
        self.assertFalse(result['samples'][0]['updateAvailable'])
        notes = get_sample_release_notes(sample='fixture', version='1.4.2', actor_role='admin',
            pinned_version='0.2.0', image_index=index, repo_index=index, state_dir=state, locale='en-US')
        self.assertEqual(notes['version'], '1.4.2')
        self.assertEqual(json.loads((state / 'fixture.json').read_text()), receipt)

    def test_legacy_index_does_not_inherit_service_version(self):
        index = self.index()
        index['samples'][0].pop('version')
        index['samples'][0].pop('releaseNotes')
        for service_version in ['0.2.0', '0.3.0']:
            index['version'] = service_version
            result = list_samples(pinned_version=service_version, image_index=index, repo_index=index,
                                  state_dir=self.root, actor_role='admin')
            self.assertEqual(result['samples'][0]['version'], '0.1.0')

    def test_version_mismatch_rejects_bundle_even_with_same_content_digest(self):
        image, repo = self.index(), self.index()
        repo['samples'][0]['version'] = '1.4.3'
        result = merge_catalog('0.2.0', image, repo)
        self.assertFalse(result['samples'][0]['installable'])

    def test_rejects_invalid_declared_sample_versions(self):
        for version in [None, 2, '0.2', '01.2.3', 'latest']:
            with self.subTest(version=version):
                self.document['metadata']['version'] = version
                (self.root / 'samples/fixture/sample.yaml').write_text(yaml.safe_dump(self.document))
                with self.assertRaises(ContractError):
                    validate_repository(self.root)

    def test_database_version_is_independent_from_shared_image_tag(self):
        kubectl = FakeKubectl()
        with patch.dict('os.environ', {'BKN_SAMPLE_DATA_IMAGE_REF': '', 'BKN_SAMPLE_DATA_IMAGE_TAG': ''}), \
             patch('installer.deploy_database.registry_digests', return_value=(DIGEST, DIGEST)) as lookup:
            result = deploy_database(self.root, 'fixture', kubectl, sleep=lambda _: None, attempts=1)
        lookup.assert_called_once_with('0.2.0')
        self.assertEqual(result['version'], '1.4.2')
        self.assertIn('value: "1.4.2"', kubectl.applied[0])
        self.assertIn("sample_version='1.4.2'", kubectl.applied[0])

    def test_fixed_remote_or_offline_release_overrides_legacy_contract_version(self):
        kubectl = FakeKubectl()
        result = deploy_database(self.root, 'fixture', kubectl, sleep=lambda _: None, attempts=1,
            data_image_ref='ghcr.io/openbkn-ai/bkn-samples@' + DIGEST,
            sample_release_version='1.5.0')
        self.assertEqual(result['version'], '1.5.0')
        self.assertIn('value: "1.5.0"', kubectl.applied[0])
        self.assertIn("sample_version='1.5.0'", kubectl.applied[0])
