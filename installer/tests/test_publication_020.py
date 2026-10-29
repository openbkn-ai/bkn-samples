"""Original020 compatibility must not silently inherit a newer install protocol."""
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('build_candidate_020', ROOT / 'tools/publication/build_candidate_020.py')


def load():
    module = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(module)
    return module


class Original020PublicationTest(unittest.TestCase):
    def test_pinned_builder_narrows_only_platform_constraint(self):
        module = load()
        source = module.read_legacy_source(ROOT)
        transformed = module.compatible_source(source)
        original = b'"platformVersion": ">=0.2.0 <0.3.0"'
        replacement = b'"platformVersion": ">=0.2.0 <0.2.1"'
        self.assertEqual(hashlib.sha256(source).hexdigest(), module.LEGACY_SHA256)
        self.assertEqual(transformed, source.replace(original, replacement))
        self.assertIn(b'samples.openbkn.ai/offline.v1', transformed)
        self.assertEqual(transformed.count(replacement), 1)

    def test_rejects_tampered_builder(self):
        module = load()
        source = module.read_legacy_source(ROOT)
        with self.assertRaisesRegex(ValueError, 'digest'):
            module.compatible_source(source + b'\n')

    def test_uses_current_source_root(self):
        legacy = load().load_legacy(ROOT)
        self.assertEqual(legacy['ROOT'], ROOT)
        self.assertTrue(legacy['included'](Path('tools/fn/allocation.py')))
        self.assertFalse(legacy['included'](Path('bkn-eval/datasets/sample-answer-set-v1.yaml')))
        self.assertFalse(legacy['included'](Path('experience/experience-set.yaml')))

    def test_untracked_runtime_file_cannot_be_silently_omitted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            sample = root / 'samples/supply_ontology_hand'
            sample.mkdir(parents=True)
            (sample / 'allocation.py').write_text('new runtime code')
            module = load()
            with patch.object(module, 'ROOT', root), self.assertRaisesRegex(ValueError, 'stage all new sample files'):
                module.build(sample, '0.1.16', root / 'out', 'image@sha256:' + '0' * 64, allow_dirty=True)

    def test_final_build_rejects_staged_but_uncommitted_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            sample = root / 'samples/supply_ontology_hand'
            sample.mkdir(parents=True)
            (sample / 'allocation.py').write_text('new runtime code')
            subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
            module = load()
            with patch.object(module, 'ROOT', root), self.assertRaisesRegex(ValueError, 'clean source commit'):
                module.build(sample, '0.1.16', root / 'out', 'image@sha256:' + '0' * 64)
