"""Keep published manufacturing BKN identifiers compatible with the API's 40-character limit."""
import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ('manufacturing-industry-en-us', 'manufacturing-industry-zh-cn')


class ManufacturingBknIdentifierTest(unittest.TestCase):
    def test_every_imported_identifier_and_display_name_fits_api_limits(self):
        for sample in SAMPLES:
            with self.subTest(sample=sample):
                network = ROOT / 'samples' / sample / 'kn'
                observed = {'knowledge_network': 0, 'object_type': 0,
                            'relation_type': 0, 'concept_group': 0}
                identifiers = set()
                for path in network.rglob('*.bkn'):
                    text = path.read_text(encoding='utf-8')
                    frontmatter = text.split('---\n', 2)[1]
                    document = yaml.safe_load(frontmatter)
                    resource_type = document['type']
                    self.assertIn(resource_type, observed, path)
                    observed[resource_type] += 1
                    for field in ('id', 'name'):
                        value = document[field]
                        self.assertLessEqual(len(value), 40, f'{path}: {field} exceeds API limit')
                    self.assertRegex(document['id'], r'^[a-z][a-z0-9_]*$', path)
                    self.assertNotIn((resource_type, document['id']), identifiers, path)
                    identifiers.add((resource_type, document['id']))
                    if resource_type == 'relation_type':
                        self.assertEqual(path.stem, document['id'], path)
                self.assertEqual(observed, {'knowledge_network': 1, 'object_type': 40,
                                            'relation_type': 71, 'concept_group': 3})


if __name__ == '__main__':
    unittest.main()
