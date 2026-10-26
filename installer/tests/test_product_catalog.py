"""Product upgrades select separate directories and preserve their independent history."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from installer.catalog_source import OfficialCatalog, ProductCatalog, RAW_PREFIX, REF_URL
from installer.tests.test_catalog_source import SCHEMA, ROOT
from tools.publication.validate import compare_baseline


class ProductCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)
        self.version = '0.2.0'
        self.source = ProductCatalog(self.state, SCHEMA, ROOT, lambda: self.version)

    def document(self, version):
        return json.loads((ROOT / 'catalogs' / version / 'catalog.json').read_text())

    def test_product_switch_isolated_cache_sequence_and_restart(self):
        documents = {v: self.document(v) for v in ('0.2.0', '0.2.1')}
        documents['0.2.0']['metadata']['sequence'] = 99
        def read(url, _limit):
            if url == REF_URL:
                return json.dumps({'object': {'sha': 'a' * 40}}).encode()
            return json.dumps(documents[url.split('/')[-2]]).encode()
        with patch('installer.catalog_source.read_url', side_effect=read) as network:
            self.assertEqual(self.source.refresh()['status'], 'updated')
            self.version = '0.2.1'
            self.assertEqual(self.source.refresh()['status'], 'unchanged')
            self.assertEqual(self.source.metadata()['productVersion'], self.version)
            self.assertEqual(self.source.source().cache['catalog']['metadata']['sequence'], 1)
            urls = [call.args[0] for call in network.call_args_list]
            self.assertIn(RAW_PREFIX + 'a' * 40 + '/catalogs/0.2.1/catalog.json', urls)
        for version in documents:
            cache = self.state / 'catalogs' / version / 'official.json'
            self.assertEqual(json.loads(cache.read_text())['catalog'], documents[version])
        restarted = ProductCatalog(self.state, SCHEMA, ROOT, lambda: self.version)
        self.assertEqual(restarted.entries(), documents['0.2.1']['spec']['entries'])
        self.version = '0.2.0'
        self.assertEqual(restarted.source().cache['catalog']['metadata']['sequence'], 99)

    def test_unknown_product_never_reads_legacy_catalog_or_main_fallback(self):
        for version in ('', 'latest', '../0.2.0', '0.2.01'):
            self.version = version
            with patch('installer.catalog_source.read_url') as network:
                self.assertEqual(self.source.entries(), [])
                self.assertEqual(self.source.refresh()['code'], 'platform_version_unavailable')
                network.assert_not_called()
        self.version = '0.2.2'
        self.assertEqual(self.source.entries(), [])
        with patch('installer.catalog_source.read_url', side_effect=OSError('not published')):
            self.assertEqual(self.source.refresh()['status'], 'failed')
        self.assertEqual(self.source.entries(), [])

    def test_other_product_payload_rejected_and_last_good_cache_preserved(self):
        self.version = '0.2.1'
        original = self.source.entries()
        with patch('installer.catalog_source.read_url', side_effect=[
                json.dumps({'object': {'sha': 'a' * 40}}).encode(),
                json.dumps(self.document('0.2.0')).encode()]):
            self.assertEqual(self.source.refresh()['status'], 'failed')
        self.assertEqual(self.source.entries(), original)

    def test_fixed_source_still_requires_matching_product_path_and_payload(self):
        pinned = RAW_PREFIX + 'a' * 40 + '/catalogs/0.2.1/catalog.json'
        source = OfficialCatalog(self.state, SCHEMA, pinned, platform_version='0.2.1')
        with patch('installer.catalog_source.read_url', return_value=json.dumps(self.document('0.2.1')).encode()) as read:
            self.assertEqual(source.refresh()['status'], 'updated')
            read.assert_called_once_with(pinned, 2 * 1024 * 1024)
        for bad in (pinned.replace('0.2.1', '0.2.0'), pinned.replace('catalogs/0.2.1/', ''),
                    pinned.replace('a' * 40, 'main')):
            with self.assertRaises(ValueError):
                OfficialCatalog(self.state, SCHEMA, bad, platform_version='0.2.1')

    def test_mismatched_pin_returns_controlled_error_without_fallback(self):
        from installer.studio_http import StudioApp, dispatch
        for path in ('catalog.json', 'catalogs/0.2.0/catalog.json'):
            source = ProductCatalog(self.state, SCHEMA, ROOT, lambda: '0.2.1',
                                    RAW_PREFIX + 'a' * 40 + '/' + path)
            app = StudioApp(
                catalog=lambda role: {'samples': source.entries()},
                refresh=lambda role: source.refresh(),
                create=lambda *args: source.entries(), retry=None, get=None,
                notes=lambda *args: source.notes('supply-chain', '0.1.9', 'en-US'),
                authenticate=lambda token: 'admin')
            routes = [('GET', '/api/studio/samples'), ('POST', '/api/studio/samples/refresh'),
                      ('POST', '/api/studio/samples/supply-chain/installations'),
                      ('GET', '/api/studio/samples/supply-chain/versions/0.1.9/release-notes')]
            with patch('installer.catalog_source.read_url') as network:
                for method, route in routes:
                    status, payload = dispatch(app, method, route, None, b'')
                    self.assertEqual(status, 409)
                    self.assertEqual(payload['code'], 'catalog_configuration_invalid')
                    self.assertNotIn(RAW_PREFIX, payload['message'])
                network.assert_not_called()
            self.assertEqual(source.sources, {})

    def test_product_directory_rejects_rewrite_and_removal_with_advanced_sequence(self):
        original = self.document('0.2.1')
        for change in ('rewrite', 'remove', 'rollback'):
            new = copy.deepcopy(original)
            new['metadata']['sequence'] += 1
            if change == 'rewrite':
                new['spec']['entries'][0]['manifest']['digest'] = 'sha256:' + 'b' * 64
            elif change == 'remove':
                new['spec']['entries'].pop()
            else:
                new['metadata']['sequence'] = 1
                new['metadata']['revision'] = 'changed'
            def view(d):
                return d, {(e['sampleId'], e['version']): e for e in d['spec']['entries']}
            with self.assertRaises(ValueError):
                compare_baseline(view(new), view(original))

    def test_current_directories_have_distinct_published_packages(self):
        entries = [self.document(v)['spec']['entries'] for v in ('0.2.0', '0.2.1')]
        ids = [{(e['sampleId'], e['version']) for e in group} for group in entries]
        self.assertFalse(ids[0] & ids[1])
        self.assertTrue(all('>=0.2.1' in e['requires']['platformVersion'] for e in entries[1]))


if __name__ == '__main__':
    unittest.main()
