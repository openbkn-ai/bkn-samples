"""Render the actual Chart to protect the internal/external gateway contract."""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CHART = ROOT / 'deploy/charts/bkn-sample-studio'
PREFIXES = ('bkn-backend', 'ontology-manager', 'vega-backend', 'agent-operator-integration',
            'ontology-query', 'agent-retrieval', 'mf-model-manager', 'mf-model-api', 'agent-observability')


@unittest.skipUnless(shutil.which('helm'), 'Helm is required for rendered Chart checks')
class GatewayChartTest(unittest.TestCase):
    def render(self, *args, namespace='openbkn'):
        result = subprocess.run(['helm', 'template', 'test', str(CHART), '-n', namespace, *args],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        documents = [d for d in yaml.safe_load_all(result.stdout) if d]
        deployment = next(d for d in documents if d['kind'] == 'Deployment')
        return documents, deployment['spec']['template']

    def test_default_is_loopback_only_and_overrides_stale_external_base(self):
        docs, pod = self.render('--set', 'baseURL=https://untrusted.example')
        containers = pod['spec']['containers']
        studio = next(c for c in containers if c['name'] == 'studio')
        env = {e['name']:e.get('value') for e in studio['env']}
        self.assertEqual(env['BKN_BASE_URL'], 'http://127.0.0.1:8082')
        proxy = next(c for c in containers if c['name'] == 'internal-gateway')
        self.assertNotIn('ports', proxy)
        self.assertIn('@sha256:', proxy['image'])
        self.assertEqual(proxy['readinessProbe']['exec']['command'][-1], 'http://127.0.0.1:8082/healthz')
        service = next(d for d in docs if d['kind'] == 'Service' and d['metadata']['name'] == 'bkn-sample-studio')
        self.assertEqual([p['targetPort'] for p in service['spec']['ports']], [8080])
        config = next(d for d in docs if d['kind'] == 'ConfigMap')['data']['default.conf.template']
        self.assertIn('listen 127.0.0.1:8082;', config)
        self.assertNotIn('listen 0.0.0.0', config)
        self.assertIn('proxy_pass $sample_upstream$request_uri;', config)
        self.assertIn('proxy_set_header Authorization $http_authorization;', config)
        self.assertIn('proxy_request_buffering off;', config)
        self.assertIn('default "";', config)
        self.assertIn('if ($sample_upstream = "") { return 404; }', config)
        for prefix in PREFIXES:
            self.assertIn('~^/api/'+prefix+'/', config)

    def test_namespace_and_upstream_changes_roll_out_the_proxy(self):
        docs, pod = self.render(namespace='customer')
        config = next(d for d in docs if d['kind'] == 'ConfigMap')['data']['default.conf.template']
        self.assertIn('bkn-backend-svc.customer.svc.cluster.local:13014', config)
        self.assertIn('ontology-query-svc.customer.svc.cluster.local:13018', config)
        self.assertNotIn('.openbkn.svc.cluster.local', config)
        _, changed = self.render('--set', 'internalGateway.upstreams.vega=http://custom-vega.customer.svc.cluster.local:1234',namespace='customer')
        self.assertNotEqual(pod['metadata']['annotations']['checksum/internal-gateway'],
                            changed['metadata']['annotations']['checksum/internal-gateway'])

    def test_external_gateway_mode_is_explicit_and_preserves_health_override(self):
        docs, pod = self.render('--set', 'internalGateway.enabled=false', '--set', 'baseURL=https://trusted.example',
                                '--set', 'backendURL=http://backend.example')
        self.assertEqual([c['name'] for c in pod['spec']['containers']], ['studio'])
        self.assertFalse(any(d['kind']=='ConfigMap' for d in docs))
        env = {e['name']:e.get('value') for e in pod['spec']['containers'][0]['env']}
        self.assertEqual(env['BKN_BASE_URL'], 'https://trusted.example')
        self.assertEqual(env['BKN_BACKEND_URL'], 'http://backend.example')
        self.assertNotIn('checksum/internal-gateway', pod['metadata'].get('annotations',{}))
        missing = subprocess.run(['helm','template','test',str(CHART),'--set','internalGateway.enabled=false'],capture_output=True,text=True)
        self.assertNotEqual(missing.returncode,0)
        self.assertIn('baseURL must supply a unified gateway',missing.stderr)
