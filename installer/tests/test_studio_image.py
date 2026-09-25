import unittest
from pathlib import Path

DOCKERFILE = Path(__file__).resolve().parents[2] / "installer/studio/Dockerfile"


class StudioImageTest(unittest.TestCase):
    def test_catalog_image_can_run_the_world_cup_hook(self):
        text = DOCKERFILE.read_text(encoding="utf-8")
        self.assertIn("bash", text)
        self.assertIn("jq", text)
        self.assertIn("PyYAML", text)
        self.assertIn("SQLAlchemy", text)
        self.assertIn("PyMySQL", text)


if __name__ == "__main__":
    unittest.main()
