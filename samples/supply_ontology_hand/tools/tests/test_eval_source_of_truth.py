from pathlib import Path

import yaml
import json

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
    assurance = yaml.safe_load((EVAL_DATASETS / "material-assurance-answers-v1.yaml").read_text())
    used.update(name for answer in assurance["answers"] for name in answer["basis"].get("functions", []))
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
    calendar_questions = yaml.safe_load(
        (EVAL_DATASETS / "calendar-month-question-set-v1.yaml").read_text(encoding="utf-8")
    )
    extension_skills = set(calendar_questions["required_skills"])

    assert used <= registered
    assert extension_skills <= registered
    assert registered <= used | extension_skills


def test_current_baseline_metric_basis_resolves_to_delivered_definitions():
    baseline = PACKAGE / "bkn-eval" / "baselines" / "2026-10-12-current-csv"
    manifest = json.loads((baseline / "manifest.json").read_text())
    answers = yaml.safe_load((baseline / manifest["answer_set"]["path"]).read_text())
    names = {entry["name"] for entry in json.loads((PACKAGE / "tools/assets/metrics-create.json").read_text())["entries"]}
    aliases = manifest["metric_name_aliases"]
    references = {name for answer in answers["answers"] for name in answer["basis"].get("metrics", [])}
    assert {aliases.get(name, name) for name in references} <= names


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
