"""Standard deployment must not require a runtime GHCR pull."""
import json
from installer.verify_image_manifest import verify_manifest
from installer.remote_installation import RemoteInstallation
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

    def test_standard_service_and_executor_use_same_swr_tag(self):
        pod = self.render()
        container = pod['containers'][0]
        expected = SWR + '/bkn-sample-studio:0.2.1'
        self.assertEqual(container['image'], expected)
        self.assertEqual(next(e['value'] for e in container['env'] if e['name'] == 'BKN_SAMPLE_EXECUTOR_IMAGE_REF'), expected)

    def test_rendered_executor_is_accepted_by_runtime(self):
        pod = self.render()
        image = next(e['value'] for e in pod['containers'][0]['env']
                     if e['name'] == 'BKN_SAMPLE_EXECUTOR_IMAGE_REF')
        runtime = RemoteInstallation(ROOT, ROOT / 'unused-state', '0.2.1', 'arm64', [], image)
        runtime.require_executor()

    def test_registry_and_full_repository_overrides_remain_explicit(self):
        self.assertEqual(self.render('image.registry=private.example/team')['containers'][0]['image'], 'private.example/team/bkn-sample-studio:0.2.1')
        self.assertEqual(self.render('image.repository=custom.example/other')['containers'][0]['image'], 'custom.example/other:0.2.1')

    def test_legacy_digest_values_do_not_override_tags(self):
        command = ['helm', 'template', 'sample', str(ROOT / 'deploy/charts/bkn-sample-studio'),
                   '--set', 'image.tag=0.2.1', '--set', 'image.digest=' + DIGEST,
                   '--set', 'sampleDatabase.image.digest=' + DIGEST]
        documents = list(yaml.safe_load_all(subprocess.check_output(command, text=True)))
        pod = next(d for d in documents if d and d['kind'] == 'Deployment')['spec']['template']['spec']
        studio = pod['containers'][0]
        self.assertEqual(studio['image'], SWR + '/bkn-sample-studio:0.2.1')
        self.assertEqual(next(e['value'] for e in studio['env'] if e['name'] == 'BKN_SAMPLE_EXECUTOR_IMAGE_REF'), studio['image'])
        database = next(d for d in documents if d and d['kind'] == 'StatefulSet')
        self.assertEqual(database['spec']['template']['spec']['containers'][0]['image'], 'mariadb:11.4.7')

    def test_chart_uses_shared_database_without_legacy_data_image_configuration(self):
        defaults = yaml.safe_load((ROOT / 'deploy/charts/bkn-sample-studio/values.yaml').read_text())
        self.assertNotIn('dataImage', defaults)
        pod = self.render('dataImage.tag=old', 'dataImage.reference=registry.example/data@' + DIGEST)
        env = {e['name']: e.get('value') for e in pod['containers'][0]['env']}
        self.assertNotIn('BKN_SAMPLE_DATA_IMAGE_TAG', env)
        self.assertNotIn('BKN_SAMPLE_DATA_IMAGE_REF', env)
        self.assertEqual(env['BKN_SAMPLE_DB_HOST'], 'bkn-sample-database.default.svc.cluster.local')

    def test_pull_secrets_reach_service(self):
        self.assertEqual(self.render('imagePullSecrets[0].name=registry-key')['imagePullSecrets'], [{'name': 'registry-key'}])


class TargetManifestTest(unittest.TestCase):
    def test_release_builds_only_service_images_for_both_architectures(self):
        path = ROOT / '.github/workflows'
        workflow = yaml.load((path / 'publish-sample-studio.yml').read_text(), Loader=yaml.BaseLoader)
        self.assertIn('v*', workflow['on']['push']['tags'])
        job = workflow['jobs']['publish']
        steps = job['steps']
        builds = [s for s in steps if s.get('uses', '').startswith('docker/build-push-action@')]
        self.assertEqual(len(builds), 2)
        self.assertEqual({s['with']['platforms'] for s in builds}, {'linux/amd64', 'linux/arm64'})
        for step in builds:
            self.assertEqual(step['with']['file'], 'installer/studio/Dockerfile')
            self.assertNotIn('if', step)
            self.assertLess(steps.index(step), next(i for i, s in enumerate(steps) if s.get('id') == 'manifest'))
        self.assertNotIn('data_digest', job['outputs'])
        self.assertNotIn('DATA_DIGEST', workflow['jobs']['candidate-cold-pull']['steps'][1]['env'])
        for step in steps:
            self.assertNotIn('openbkn-ai bkn-samples', step.get('run', ''))
            self.assertNotIn('openbkn-ai/bkn-samples:', step.get('run', ''))
            self.assertNotIn('DATA_DIGEST', step.get('env', {}))
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

    def test_standard_release_requires_swr_before_build_and_packages_version_tag(self):
        workflow = yaml.load((ROOT / '.github/workflows/publish-sample-studio.yml').read_text(), Loader=yaml.BaseLoader)
        steps = workflow['jobs']['publish']['steps']
        version = next(s for s in steps if s.get('id') == 'version')['run']
        self.assertIn('SWR credentials are required', version)
        manifest = next(s for s in steps if s.get('id') == 'manifest')['run']
        self.assertIn('swr.cn-east-3.myhuaweicloud.com/openbkn-ai/bkn-sample-studio@${service_digest}', manifest)
        self.assertIn('verify_image_manifest.py', manifest)
        package = next(s for s in steps if s.get('name') == 'Package the chart for the same version')
        self.assertEqual(package['env']['VERSION'], '${{ steps.version.outputs.value }}')
        self.assertNotIn('SERVICE_IMAGE_DIGEST', package['env'])


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

    def test_rendered_chart_rejects_wrong_registry_tag_and_executor(self):
        rendered = subprocess.check_output([
            'helm', 'template', 'sample', str(ROOT / 'deploy/charts/bkn-sample-studio'),
            '--set', 'image.tag=0.2.1'], text=True)
        documents = list(yaml.safe_load_all(rendered))
        verify_chart(rendered, '0.2.1')
        for target in ('service-ghcr', 'executor-ghcr', 'service-wrong-tag', 'executor-wrong-tag'):
            with self.subTest(target=target):
                changed = deepcopy(documents)
                deployment = next(d for d in changed if d and d['kind'] == 'Deployment' and d['metadata']['name'] == 'bkn-sample-studio')
                studio = next(c for c in deployment['spec']['template']['spec']['containers'] if c['name'] == 'studio')
                bad = 'ghcr.io/openbkn-ai/bkn-sample-studio@' + DIGEST if target.endswith('ghcr') else SWR + '/bkn-sample-studio:0.2.2'
                if target.startswith('service'):
                    studio['image'] = bad
                else:
                    next(e for e in studio['env'] if e['name'] == 'BKN_SAMPLE_EXECUTOR_IMAGE_REF')['value'] = bad
                with self.assertRaisesRegex(ValueError, 'matching SWR version tag'):
                    verify_chart(yaml.safe_dump_all(changed), '0.2.1')
