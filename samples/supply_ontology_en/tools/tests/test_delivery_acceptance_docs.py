from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[2]
V4 = "bkn-eval/baselines/2026-10-30-business-scenarios-v4/README.md"


def test_delivery_path_points_to_the_prd_and_the_v4_scenario_set():
    guide = (PACKAGE / "docs" / "import-guide.en-US.md").read_text(encoding="utf-8")
    readme = (PACKAGE / "README.md").read_text(encoding="utf-8")

    assert "Capabilities and MCP acceptance" in guide
    assert "Business-scenario 50-question evaluation" in guide
    assert "metric" not in guide.lower()
    assert "docs/PRD.en-US.md" in readme and V4 in readme
    assert "metrics, native functions" not in readme.lower()
