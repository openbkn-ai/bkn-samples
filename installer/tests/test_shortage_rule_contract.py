"""Keep the English sample's shortage rule payload complete; the Chinese sample no longer publishes it."""
import base64
import importlib.util
import io
import sys
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]


class ShortageRuleContractTest(unittest.TestCase):
    def test_each_native_payload_contains_rule_and_coverage_dependencies(self):
        required={'shortage_rule_runtime.py','managed_execution.py','fn/shortage_rule.py','fn/material_assurance.py','fn/read_complete.py','fn/allocation.py','fn/bom.py'}
        for name in ['supply_ontology_en']:
            path=ROOT/'samples'/name/'tools/native_function_bundle.py'
            spec=importlib.util.spec_from_file_location(name+'_bundle',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            source=module.build_native_function_code(fixed_operation='shortage_rule');compile(source,'rule.py','exec')
            with zipfile.ZipFile(io.BytesIO(base64.b64decode(module._archive_source()))) as archive:
                self.assertTrue(required<=set(archive.namelist()))
            self.assertIn('bkn.query_instance_subgraph',source)
            self.assertNotIn('def handler',source)
