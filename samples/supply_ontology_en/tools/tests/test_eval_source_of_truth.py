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
    assert not (PACKAGE / "docs" / 'Business Question Set.md').exists()
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
    calendar_questions = yaml.safe_load(
        (EVAL_DATASETS / "calendar-month-question-set-v1.yaml").read_text(encoding="utf-8")
    )
    extension_skills = set(calendar_questions["required_skills"])

    assert used <= registered
    assert extension_skills <= registered
    assert registered <= used | extension_skills


def test_frozen_baseline_metric_basis_resolves_to_delivered_definitions():
    answers = yaml.safe_load((EVAL_DATASETS / "sample-answer-set-v1.yaml").read_text())
    names = {entry["name"] for entry in json.loads((PACKAGE / "tools/assets/metrics-create.json").read_text())["entries"]}
    references = {name for answer in answers["answers"] for name in answer["basis"].get("metrics", [])}
    assert references <= names


def test_frozen_baseline_freezes_all_data_and_retains_future_forecasts():
    import csv
    import hashlib
    lock = json.loads((PACKAGE / "dataset.lock").read_text())
    assert lock["baseline_id"] == "supply-en-frozen-v1"
    assert len(lock["files"]) == 12
    for entry in lock["files"]:
        path = PACKAGE / entry["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
        with path.open(encoding="utf-8-sig") as file:
            assert len(list(csv.DictReader(file))) == entry["rows"]
    with (PACKAGE / "data/erp_mds_forecast.csv").open(encoding="utf-8-sig") as file:
        ids = {row["id"] for row in csv.DictReader(file)}
    assert {"0000023181-FUTURE", "0000023181-SHORT", "0000023181-CONTENTION"} <= ids
