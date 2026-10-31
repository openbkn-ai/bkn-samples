"""Keep runtime requests distinct from published metric capability definitions."""
import json
import unittest
from pathlib import Path
from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / 'tools/contracts/object-metrics-v1/query_metric.json').read_text())['input_schema']


class MetricRequestsTest(unittest.TestCase):
    def test_upstream_schema_rejects_old_runtime_field(self):
        bad = {'kn_id': 'network', 'metric_id': 'metric', 'version': 1, 'query': {'analysis_dimensions': []}}
        self.assertTrue(list(Draft7Validator(SCHEMA).iter_errors(bad)))


if __name__ == '__main__':
    unittest.main()
