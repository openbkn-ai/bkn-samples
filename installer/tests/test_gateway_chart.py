"""Render the Chart's existing-Ingress gateway defaults and operator overrides."""
import shutil
import subprocess
import unittest
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[2]
CHART = ROOT / 'deploy/charts/bkn-sample-studio'
GATEWAY = 'http://ingress-nginx-controller.ingress-nginx.svc.cluster.local'
@unittest.skipUnless(shutil.which('helm'), 'Helm is required for rendered Chart checks')
class GatewayChartTest(unittest.TestCase):
    def render(self, *args):
        result = subprocess.run(['helm','template','test',str(CHART),'-n','customer',*args],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        docs = [d for d in yaml.safe_load_all(result.stdout) if d]
        pod = next(d for d in docs if d['kind']=='Deployment')['spec']['template']['spec']
        return docs,pod
    def test_default_reuses_existing_ingress_without_new_proxy_resources(self):
        docs,pod=self.render()
        self.assertEqual([c['name'] for c in pod['containers']],['studio'])
        env={e['name']:e.get('value','') for e in pod['containers'][0]['env']}
        self.assertEqual(env['BKN_BASE_URL'],GATEWAY)
        self.assertEqual(env['BKN_BACKEND_URL'],'')
        self.assertFalse(any(d['kind']=='ConfigMap' for d in docs))
        self.assertEqual([d['metadata']['name'] for d in docs if d['kind']=='Service'],['bkn-sample-studio'])
    def test_operator_gateway_and_health_addresses_remain_independent(self):
        _,pod=self.render('--set','baseURL=http://custom-internal.example','--set','backendURL=http://backend.example')
        env={e['name']:e.get('value','') for e in pod['containers'][0]['env']}
        self.assertEqual(env['BKN_BASE_URL'],'http://custom-internal.example')
        self.assertEqual(env['BKN_BACKEND_URL'],'http://backend.example')
    def test_gateway_change_does_not_modify_installer_or_data_image_selection(self):
        _,pod=self.render('--set','image.digest=sha256:'+'a'*64,'--set','dataImage.reference=registry.example/data@sha256:'+'b'*64)
        studio=pod['containers'][0]
        env={e['name']:e.get('value','') for e in studio['env']}
        self.assertTrue(studio['image'].endswith('@sha256:'+'a'*64))
        self.assertEqual(env['BKN_SAMPLE_EXECUTOR_IMAGE_REF'],studio['image'])
        self.assertEqual(env['BKN_SAMPLE_DATA_IMAGE_REF'],'registry.example/data@sha256:'+'b'*64)
