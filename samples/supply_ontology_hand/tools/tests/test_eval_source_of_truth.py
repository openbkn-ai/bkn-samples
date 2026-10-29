from pathlib import Path

import yaml

from function_catalog import FUNCTION_CATALOG
from register_skills import local_skills


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


def test_bkn_eval_covers_every_published_function_by_its_actual_name():
    answers = yaml.safe_load(
        (EVAL_DATASETS / "sample-answer-set-v1.yaml").read_text(encoding="utf-8")
    )
    used = {
        name
        for answer in answers["answers"]
        for name in answer["basis"].get("functions", [])
    }
    published = {spec["name"] for spec in FUNCTION_CATALOG.values()}

    assert used <= published
    assert published <= used


def test_bkn_eval_covers_every_registered_skill():
    answers = yaml.safe_load(
        (EVAL_DATASETS / "sample-answer-set-v1.yaml").read_text(encoding="utf-8")
    )
    used = {
        name
        for answer in answers["answers"]
        for name in answer["basis"].get("skills", [])
    }
    registered = {name for name, _ in local_skills()}

    assert used <= registered
    assert registered <= used


def test_evaluated_paper_contains_only_original_questions_and_business_date():
    questions = yaml.safe_load((EVAL_DATASETS / "sample-question-set-v1.yaml").read_text())
    original = yaml.safe_load((PACKAGE / "bkn-eval/baselines/2026-10-29-020-accuracy/historical/customer-question-set-v1.yaml").read_text())
    assert set(questions) == {"business_date", "questions"}
    assert questions["questions"] == original["questions"]
    assert all(set(item) == {"id", "question"} for item in questions["questions"])


def test_published_skills_do_not_contain_evaluator_scoring_instructions():
    import re

    for path in (PACKAGE / "skills").rglob("*.md"):
        text = path.read_text()
        assert "评分" not in text, path
        assert "金标" not in text, path
        assert "题目未要求" not in text, path
        assert not re.search(r"\b[MFRS]-\d{2}\b", text), path
