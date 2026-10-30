import importlib.util
import json
from pathlib import Path

import yaml

from function_catalog import FUNCTION_CATALOG
from register_skills import local_skills


PACKAGE = Path(__file__).resolve().parents[2]
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
    assert {item["difficulty"] for item in questions["questions"]} == {"basic", "medium", "complex"}


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

