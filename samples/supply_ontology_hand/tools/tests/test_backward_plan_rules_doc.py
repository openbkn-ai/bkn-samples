"""The backward-plan function keeps its business rules next to the sample."""
from pathlib import Path

PACK = Path(__file__).resolve().parents[2]


def test_backward_plan_points_to_its_business_rules():
    source = (PACK / "tools/fn/backward_plan.py").read_text(encoding="utf-8")
    assert "docs/backward-plan-business-rules.md" in source
    assert (PACK / "docs/backward-plan-business-rules.md").read_text(encoding="utf-8").strip()


def test_sample_publishes_no_agent_skills():
    import yaml
    assert yaml.safe_load((PACK / "sample.yaml").read_text())["spec"]["components"]["skills"] is False
    assert not (PACK / "skills").exists()
