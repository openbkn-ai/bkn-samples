from pathlib import Path

import yaml


PACKAGE = Path(__file__).resolve().parents[2]
EVAL_DATASETS = PACKAGE / "bkn-eval" / "datasets"


def test_bkn_eval_is_the_only_formal_question_source():
    questions = yaml.safe_load(
        (EVAL_DATASETS / "sample-question-set-v1.yaml").read_text(encoding="utf-8")
    )
    answers = yaml.safe_load(
        (EVAL_DATASETS / "sample-answer-set-v1.yaml").read_text(encoding="utf-8")
    )

    question_ids = {item["id"] for item in questions["questions"]}
    answer_ids = {item["id"] for item in answers["answers"]}

    assert len(question_ids) == 50
    assert question_ids == answer_ids
    assert not (PACKAGE / "docs" / "业务问答测试集.md").exists()
    assert not (PACKAGE / "docs" / "qa-eval-set.yaml").exists()
    assert not (PACKAGE / "docs" / "payloads" / "qa-eval-set.yaml").exists()
