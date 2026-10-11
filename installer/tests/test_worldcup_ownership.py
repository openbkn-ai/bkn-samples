import importlib.util
import tempfile
import unittest
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "samples/world-cup/scripts/render_worldcup_bkn_vega_placeholders.py"
spec = importlib.util.spec_from_file_location("worldcup_renderer", MODULE)
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


class WorldCupOwnershipTest(unittest.TestCase):
    def test_managed_render_keeps_model_and_adds_version_ownership(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "network.bkn"
            text = (ROOT / "samples/world-cup/kn/network.bkn").read_text()
            path.write_text(text)
            renderer.apply_managed_tags(path, {"sample": "world-cup", "version": "0.1.2", "ownership": {"sample": "world-cup"}})
            rendered = path.read_text()
            _, front, body = rendered.split("---", 2)
            self.assertEqual(body, text.split("---", 2)[2])
            tags = yaml.safe_load(front)["tags"]
            self.assertTrue({"worldcup", "bkn-samples", "bkn-sample-world-cup", "bkn-samples-version-0-1-2"}.issubset(tags))
            renderer.apply_managed_tags(path, {"sample": "world-cup", "version": "0.1.2", "ownership": {"sample": "world-cup"}})
            self.assertEqual(path.read_text(), rendered)

    def test_wrong_sample_cannot_claim_network(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "network.bkn"
            original = (ROOT / "samples/world-cup/kn/network.bkn").read_text()
            path.write_text(original)
            with self.assertRaises(ValueError):
                renderer.apply_managed_tags(path, {"sample": "other", "version": "0.1.2", "ownership": {"sample": "other"}})
            self.assertEqual(path.read_text(), original)
