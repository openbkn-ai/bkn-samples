"""Standard deployment must not require a runtime GHCR pull."""
import json
from installer.verify_image_manifest import verify_manifest
from installer.ci.verify_candidate_chart import verify as verify_chart
from copy import deepcopy
import subprocess
import unittest
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
SWR = 'swr.cn-east-3.myhuaweicloud.com/openbkn-ai'
DIGEST = 'sha256:' + 'a' * 64

class SWRDeliveryTest(unittest.TestCase):
    def render(self, *values):
        command = ['helm', 'template', 'sample', str(ROOT / 'deploy/charts/bkn-sample-studio'), '--set', 'image.tag=0.2.1']
        for value in values:
            command.extend(['--set', value])
        documents = yaml.safe_load_all(subprocess.check_output(command, text=True))
        return next(d for d in documents if d and d['kind'] == 'Deployment')['spec']['template']['spec']

    def test_standard_service_and_executor_use_same_swr_digest(self):
        pod = self.render('image.digest=' + DIGEST)
        container = pod['containers'][0]
        expected = SWR + '/bkn-sample-studio@' + DIGEST
        self.assertEqual(container['image'], expected)
        self.assertEqual(next(e['value'] for e in container['env'] if e['name'] == 'BKN_SAMPLE_EXECUTOR_IMAGE_REF'), expected)

    def test_registry_and_full_repository_overrides_remain_explicit(self):
        self.assertEqual(self.render('image.registry=private.example/team', 'image.digest=' + DIGEST)['containers'][0]['image'], 'private.example/team/bkn-sample-studio@' + DIGEST)
        self.assertEqual(self.render('image.repository=custom.example/other', 'image.digest=' + DIGEST)['containers'][0]['image'], 'custom.example/other@' + DIGEST)

    def test_pull_secrets_reach_service(self):
        self.assertEqual(self.render('imagePullSecrets[0].name=registry-key')['imagePullSecrets'], [{'name': 'registry-key'}])


class TargetManifestTest(unittest.TestCase):
    def test_tag_release_has_one_ordered_data_producer(self):
        path = ROOT / '.github/workflows'
        workflow = yaml.load((path / 'publish-sample-studio.yml').read_text(), Loader=yaml.BaseLoader)
        self.assertIn('v*', workflow['on']['push']['tags'])
        steps = workflow['jobs']['publish']['steps']
        data_builds = [s for s in steps if s.get('with', {}).get('file') == 'installer/image/Dockerfile']
        self.assertEqual(len(data_builds), 2)
        for step in data_builds:
            self.assertNotIn('if', step)
            self.assertLess(steps.index(step), next(i for i, s in enumerate(steps) if s.get('id') == 'manifest'))
        for step in steps:
            self.assertNotIn('"${GITHUB_REF_TYPE}" != "tag"', step.get('run', ''))
        self.assertFalse((path / 'publish-sample-image.yml').exists())

    def manifest(self):
        return {'schemaVersion': 2, 'mediaType': 'application/vnd.docker.distribution.manifest.list.v2+json',
                'manifests': [{'digest': DIGEST, 'platform': {'os': 'linux', 'architecture': arch}} for arch in ('amd64', 'arm64')]}

    def test_target_manifest_is_validated_without_source_registry_equality(self):
        verify_manifest(self.manifest())

    def test_missing_architecture_and_malformed_digest_are_rejected(self):
        manifest = self.manifest()
        manifest['manifests'].pop()
        with self.assertRaises(ValueError):
            verify_manifest(manifest)
        manifest = self.manifest()
        manifest['manifests'][0]['digest'] = 'latest'
        with self.assertRaises(ValueError):
            verify_manifest(manifest)

    def test_standard_release_requires_swr_before_build_and_packages_swr_digest(self):
        workflow = yaml.load((ROOT / '.github/workflows/publish-sample-studio.yml').read_text(), Loader=yaml.BaseLoader)
        steps = workflow['jobs']['publish']['steps']
        version = next(s for s in steps if s.get('id') == 'version')['run']
        self.assertIn('SWR credentials are required', version)
        manifest = next(s for s in steps if s.get('id') == 'manifest')['run']
        self.assertIn('swr.cn-east-3.myhuaweicloud.com/openbkn-ai/bkn-sample-studio@${service_digest}', manifest)
        self.assertIn('verify_image_manifest.py', manifest)
        package = next(s for s in steps if s.get('name') == 'Package the chart for the same version')
        self.assertEqual(package['env']['SERVICE_IMAGE_DIGEST'], '${{ steps.manifest.outputs.service_digest }}')


class PublishedChartGateTest(unittest.TestCase):
    def test_gate_runs_for_every_publication_before_push(self):
        workflow = yaml.load((ROOT / '.github/workflows/publish-sample-studio.yml').read_text(), Loader=yaml.BaseLoader)
        steps = workflow['jobs']['publish']['steps']
        gates = [step for step in steps if 'verify_candidate_chart.py' in step.get('run', '')]
        self.assertEqual(len(gates), 1)
        gate = gates[0]
        self.assertNotIn('if', gate)
        self.assertNotIn('continue-on-error', gate)
        self.assertEqual(gate['env']['VERSION'], '${{ steps.version.outputs.value }}')
        self.assertEqual(gate['env']['SERVICE_DIGEST'], '${{ steps.manifest.outputs.service_digest }}')
        package = next(step for step in steps if 'helm package ' in step.get('run', ''))
        publish = next(step for step in steps if 'helm push ' in step.get('run', ''))
        self.assertLess(steps.index(package), steps.index(gate))
        self.assertLess(steps.index(gate), steps.index(publish))
        self.assertIn('mkdir publication-evidence', gate['run'])
        self.assertIn('helm template candidate "/tmp/charts/bkn-sample-studio-${VERSION}.tgz"', gate['run'])

    def test_rendered_chart_rejects_wrong_registry_digest_and_executor(self):
        rendered = subprocess.check_output([
            'helm', 'template', 'sample', str(ROOT / 'deploy/charts/bkn-sample-studio'),
            '--set', 'image.tag=0.2.1', '--set', 'image.digest=' + DIGEST,
            '--set', 'dataImage.tag=0.2.1'], text=True)
        documents = list(yaml.safe_load_all(rendered))
        verify_chart(rendered, DIGEST, '0.2.1')
        for target in ('service-ghcr', 'executor-ghcr', 'service-wrong-digest', 'executor-wrong-digest'):
            with self.subTest(target=target):
                changed = deepcopy(documents)
                deployment = next(d for d in changed if d and d['kind'] == 'Deployment' and d['metadata']['name'] == 'bkn-sample-studio')
                studio = next(c for c in deployment['spec']['template']['spec']['containers'] if c['name'] == 'studio')
                bad = 'ghcr.io/openbkn-ai/bkn-sample-studio@' + DIGEST if target.endswith('ghcr') else SWR + '/bkn-sample-studio@sha256:' + 'b' * 64
                if target.startswith('service'):
                    studio['image'] = bad
                else:
                    next(e for e in studio['env'] if e['name'] == 'BKN_SAMPLE_EXECUTOR_IMAGE_REF')['value'] = bad
                with self.assertRaisesRegex(ValueError, 'verified SWR digest'):
                    verify_chart(yaml.safe_dump_all(changed), DIGEST, '0.2.1')
