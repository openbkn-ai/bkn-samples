from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[2]


def test_delivery_path_ends_with_core_bkn_eval_without_extension_questions():
    guide = (PACKAGE / "docs" / "import-guide.en-US.md").read_text(encoding="utf-8")
    readme = (PACKAGE / "README.md").read_text(encoding="utf-8")
    evaluation_guide = (PACKAGE / "bkn-eval" / 'Evaluation Guide.md').read_text(encoding="utf-8")
    question_set = (PACKAGE / "bkn-eval" / "datasets" / "sample-question-set-v1.yaml").read_text(encoding="utf-8")
    answer_set = (PACKAGE / "bkn-eval" / "datasets" / "sample-answer-set-v1.yaml").read_text(encoding="utf-8")

    assert 'Capabilities and MCP acceptance' in guide
    assert 'Core 50-question evaluation' in guide
    assert 'Step 8' not in guide
    assert 'Optional scenarios' not in guide
    assert 'core 50 questions' in readme and "BKN-Eval" in readme
    assert '14 functions' not in evaluation_guide
    assert "X-01" not in evaluation_guide
    assert "extensions:" not in question_set
    assert "extension_answers:" not in answer_set
