"""Keep published sample identifiers compatible with the API resource limits."""
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ('manufacturing-industry-en-us', 'manufacturing-industry-zh-cn')
RESOURCE_MAX_LENGTH = 128


class ManufacturingBknIdentifierTest(unittest.TestCase):
    def test_every_imported_identifier_and_display_name_fits_api_limits(self):
        for sample in SAMPLES:
            with self.subTest(sample=sample):
                network = ROOT / 'samples' / sample / 'kn'
                observed = {'knowledge_network': 0, 'object_type': 0,
                            'relation_type': 0, 'concept_group': 0}
                long_relation_fields = {'id': 0, 'name': 0}
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
                        self.assertLessEqual(
                            len(value), RESOURCE_MAX_LENGTH,
                            f'{path}: {field} exceeds API limit')
                        if resource_type == 'relation_type' and len(value) > 40:
                            long_relation_fields[field] += 1
                    self.assertRegex(document['id'], r'^[a-z][a-z0-9_]*$', path)
                    self.assertNotIn((resource_type, document['id']), identifiers, path)
                    identifiers.add((resource_type, document['id']))
                    if resource_type == 'relation_type':
                        self.assertEqual(path.stem, document['id'], path)
                self.assertEqual(observed, {'knowledge_network': 1, 'object_type': 40,
                                            'relation_type': 71, 'concept_group': 3})
                self.assertEqual(long_relation_fields, {'id': 62, 'name': 62})

    def test_original_long_acceptance_fixtures_are_preserved(self):
        english_network = ROOT / 'samples' / 'manufacturing-industry-en-us' / 'kn' / 'network.bkn'
        network = yaml.safe_load(english_network.read_text(encoding='utf-8').split('---\n', 2)[1])
        self.assertEqual(network['name'], 'End-to-End Manufacturing Operations Sample')

        relation_id = (
            'material_issue_transactions_material_requirement_id_'
            'to_production_order_material_requirements')
        self.assertEqual(len(relation_id), 93)
        for sample in SAMPLES:
            relation = ROOT / 'samples' / sample / 'kn' / 'relation_types' / f'{relation_id}.bkn'
            self.assertTrue(relation.is_file(), relation)


if __name__ == '__main__':
    unittest.main()
