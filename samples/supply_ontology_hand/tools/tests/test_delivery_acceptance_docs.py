from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[2]
V4 = "bkn-eval/baselines/2026-10-30-business-scenarios-v4/README.md"


def test_delivery_path_points_to_the_prd_and_the_v4_scenario_set():
    guide = (PACKAGE / "docs" / "openbkn-hand-import-guide_cn.md").read_text(encoding="utf-8")
    readme = (PACKAGE / "README.md").read_text(encoding="utf-8")

    assert "业务能力与 MCP 验收" in guide
    assert "业务场景 50 题评测" in guide
    assert "指标" not in guide
    assert "docs/PRD.zh-CN.md" in readme and V4 in readme
    assert "指标、" not in readme
