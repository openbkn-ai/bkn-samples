import importlib.util
import json
from pathlib import Path

import yaml

from function_catalog import FUNCTION_CATALOG
from register_skills import local_skills


PACKAGE = Path(__file__).resolve().parents[2]
EVAL_DATASETS = PACKAGE / "bkn-eval" / "datasets"
V4 = PACKAGE / "bkn-eval" / "baselines" / "2026-10-30-business-scenarios-v4"


def load_v4():
    questions = yaml.safe_load((V4 / "question-set-v4.yaml").read_text(encoding="utf-8"))
    answers = yaml.safe_load((V4 / "answer-set-v4.yaml").read_text(encoding="utf-8"))
    return questions, answers


def test_v4_scenario_set_is_the_formal_question_source():
    questions, answers = load_v4()
    ids = [item["id"] for item in questions["questions"]]

    assert len(ids) == 50 == len(set(ids))
    assert ids == [item["id"] for item in answers["answers"]]
    assert questions["answer_set_access"] == "forbidden"
    assert all("expected" not in item for item in questions["questions"])
    assert {item["difficulty"] for item in questions["questions"]} == {"基础", "中等", "复杂"}
    assert not (PACKAGE / "docs" / "业务问答测试集.md").exists()


def test_v4_answers_are_what_the_oracle_computes_from_the_delivered_csv():
    spec = importlib.util.spec_from_file_location("v4_oracle", V4 / "oracle.py")
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    _, answers = load_v4()

    computed = {item["id"]: json.loads(json.dumps(item["expected"], default=str)) for item in oracle.QUESTIONS}
    assert {item["id"]: item["expected"] for item in answers["answers"]} == computed


def test_skills_name_every_published_function():
    text = "\n".join((path / "SKILL.md").read_text(encoding="utf-8") for _, path in local_skills())
    for operation, spec in FUNCTION_CATALOG.items():
        assert operation in text and spec["name"] in text


def test_current_baseline_keeps_questions_and_versions_the_three_data_changes():
    baseline = PACKAGE / "bkn-eval" / "baselines" / "2026-10-12-current-csv"
    questions = yaml.safe_load((baseline / "question-set-v2.yaml").read_text())
    historical = yaml.safe_load((EVAL_DATASETS / "sample-question-set-v1.yaml").read_text())
    current_answers = yaml.safe_load((baseline / "answer-set-v2.yaml").read_text())
    old_answers = yaml.safe_load((EVAL_DATASETS / "sample-answer-set-v1.yaml").read_text())
    assert questions["questions"] == historical["questions"]
    assert {entry["id"] for entry in questions["questions"]} == {entry["id"] for entry in current_answers["answers"]}
    changed = {current["id"] for old, current in zip(old_answers["answers"], current_answers["answers"]) if old != current}
    assert changed == {"M-07", "M-08", "M-12"}
