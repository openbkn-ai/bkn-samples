from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[2]


def test_delivery_path_ends_with_core_bkn_eval_without_extension_questions():
    guide = (PACKAGE / "docs" / "openbkn-hand-import-guide_cn.md").read_text(encoding="utf-8")
    readme = (PACKAGE / "README.md").read_text(encoding="utf-8")
    evaluation_guide = (PACKAGE / "bkn-eval" / "体验评测指南.md").read_text(encoding="utf-8")
    question_set = (PACKAGE / "bkn-eval" / "datasets" / "sample-question-set-v1.yaml").read_text(encoding="utf-8")
    answer_set = (PACKAGE / "bkn-eval" / "datasets" / "sample-answer-set-v1.yaml").read_text(encoding="utf-8")

    assert "步骤 6：业务能力与 MCP 验收" in guide
    assert "步骤 7：核心 50 题系统评测对比" in guide
    assert "步骤 8" not in guide
    assert "场景扩展（可选）" not in guide
    assert "步骤 7" in readme and "BKN-Eval" in readme
    assert "14 个" not in evaluation_guide
    assert "X-01" not in evaluation_guide
    assert "extensions:" not in question_set
    assert "extension_answers:" not in answer_set
