"""Backend version probes must not redirect authenticated platform operations."""
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import yaml

from installer.contract import build_manifest_index, read_version
from installer.platform_version import read_backend_version
from installer.remote_catalog import merge_remote
from installer.runtime import caller_env, openbkn_json
from installer.studio_http import main
from installer.uninstall import platform_client

ROOT = Path(__file__).resolve().parents[2]


class ApiRoutingTest(unittest.TestCase):
    def test_optional_health_address_does_not_replace_gateway_or_bypass_failure(self):
        index = build_manifest_index(ROOT, 'a' * 40)
        for backend in ('', 'http://backend.example:13014'):
            with self.subTest(backend=backend), tempfile.TemporaryDirectory() as directory:
                apps = []
                env = {'BKN_SAMPLES_ROOT': str(ROOT), 'BKN_SAMPLE_STATE_DIR': directory,
                       'BKN_BASE_URL': 'http://gateway.example', 'BKN_BACKEND_URL': backend,
                       'BKN_SAMPLE_PLATFORM_VERSION': '', 'BKN_SAMPLE_CATALOG_URL': '',
                       'BKN_SAMPLE_EXECUTOR_IMAGE_REF': 'ghcr.io/openbkn-ai/bkn-sample-studio:0.2.0'}
                with patch.dict('os.environ', env), \
                     patch('installer.studio_api.load_indexes', return_value=(read_version(ROOT), index, index)), \
                     patch('installer.studio_http.serve', side_effect=lambda app, *args: apps.append(app)), \
                     patch('installer.platform_version.read_backend_version', return_value='0.2.0') as health, \
                     patch('installer.remote_catalog.merge_remote', wraps=merge_remote) as merge:
                    main()
                    catalog = apps[0].catalog('admin')
                    health.assert_called_with(backend or env['BKN_BASE_URL'])
                    self.assertTrue(any(c['installable'] for c in catalog['samples']))
                    cli = caller_env('Bearer routing-test')
                    self.assertEqual(cli['BKN_BASE_URL'], env['BKN_BASE_URL'])
                    self.assertEqual(cli['BKN_TOKEN'], 'routing-test')
                    health.return_value = ''
                    unavailable = apps[0].catalog('admin')
                    self.assertEqual(merge.call_args.args[-1].platform_version, '')
                    self.assertEqual(health.call_count, 2)

    def test_real_http_probe_and_authenticated_gateway_routes_are_separate(self):
        calls = []
        def handler(service):
            class Handler(BaseHTTPRequestHandler):
                def do_GET(self):
                    calls.append((service, self.path, self.headers.get('Authorization')))
                    health = self.path == '/api/bkn-backend/v1/health'
                    status = 200 if health or service == 'gateway' else 404
                    payload = {'ServerVersion': '0.2.0'} if health else {'entries': []}
                    data = json.dumps(payload).encode()
                    self.send_response(status)
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                def log_message(self, *args):
                    pass
            return Handler
        servers = []
        for service in ('backend', 'gateway'):
            server = ThreadingHTTPServer(('127.0.0.1', 0), handler(service))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            servers.append(server)
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
        backend, gateway = [f'http://127.0.0.1:{s.server_port}' for s in servers]
        with patch.dict('os.environ', {'BKN_BASE_URL': gateway, 'BKN_BACKEND_URL': backend,
                                       'NO_PROXY': '127.0.0.1', 'no_proxy': '127.0.0.1'}):
            self.assertEqual(read_backend_version(backend), '0.2.0')
            api = platform_client('Bearer routing-test')
            for path in ('/api/vega-backend/v1/catalogs/catalog-owned',
                         '/api/bkn-backend/v1/knowledge-networks/network-owned',
                         '/api/agent-operator-integration/v1/tool-box/tool-owned'):
                self.assertEqual(api('GET', path), {'entries': []})
            def cli_run(argv, env):
                # The CLI adapter receives the original gateway plus the caller token.
                self.assertEqual(argv[:5], ['openbkn', '--json', 'vega', 'catalog', 'list'])
                self.assertEqual(env['BKN_BASE_URL'], gateway)
                self.assertEqual(env['BKN_TOKEN'], 'routing-test')
                from subprocess import CompletedProcess
                return CompletedProcess(argv, 0, '{"entries": []}', '')
            openbkn_json(['vega', 'catalog', 'list'], cli_run, caller_env('Bearer routing-test'))
        self.assertEqual(calls[0], ('backend', '/api/bkn-backend/v1/health', None))
        self.assertEqual(len(calls), 4)
        self.assertTrue(all(service == 'gateway' and auth == 'Bearer routing-test'
                            for service, _, auth in calls[1:]))

    def test_chart_does_not_default_business_calls_to_backend_only(self):
        values = yaml.safe_load((ROOT / 'deploy/charts/bkn-sample-studio/values.yaml').read_text())
        self.assertEqual(values['baseURL'], 'http://ingress-nginx-controller.ingress-nginx.svc.cluster.local')
        self.assertEqual(values['backendURL'], '')
