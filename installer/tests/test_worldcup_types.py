"""Validate the loader contract against models and every locked data cell."""
import csv
import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class WorldCupTypesTest(unittest.TestCase):
    def test_both_languages_cover_csv_columns_match_models_and_convert_locked_data(self):
        contracts = []
        for sample in ('world-cup', 'world-cup-en'):
            root = ROOT / 'samples' / sample
            spec = importlib.util.spec_from_file_location(sample, root / 'db/load_worldcup.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            contract = json.loads((root / 'db/column-types.json').read_text())
            contracts.append(contract)
            for data in (root / 'data').glob('*.csv'):
                table = module.table_name(data)
                model = (root / 'kn/object_types' / (data.stem + '.bkn')).read_text()
                modeled = dict(re.findall(r'^\| (\w+) \| [^|]+ \| (string|integer) \|', model, re.M))
                self.assertTrue(modeled)
                for field, kind in modeled.items():
                    self.assertEqual(contract[table][field], kind, (sample, table, field))
                with data.open(newline='', encoding='utf-8-sig') as stream:
                    reader = csv.DictReader(stream)
                    self.assertEqual(set(reader.fieldnames), set(contract[table]))
                    for row in reader:
                        for field, value in row.items():
                            converted = module.convert_value(value, contract[table][field])
                            if value and contract[table][field] == 'integer':
                                self.assertIsInstance(converted, int)
                            elif value:
                                self.assertEqual(converted, value)
            sql = module.create_table_sql('wc_matches', ['match_id', 'home_team_score'])
            self.assertIn('`home_team_score` BIGINT', sql)
            self.assertIn('`match_id` VARCHAR(255)', sql)
            self.assertEqual(module.convert_value('000034', 'string'), '000034')
            for bad in ('3.5', 'nan', 'true', str(2 ** 63)):
                with self.assertRaises(ValueError):
                    module.convert_value(bad, 'integer')
            with self.assertRaises(ValueError):
                module.column_types('wc_matches', ['unknown_column'])
        self.assertEqual(contracts[0], contracts[1])


if __name__ == '__main__':
    unittest.main()
