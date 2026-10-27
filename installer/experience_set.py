"""Experience sets: the sample questions Studio offers after installation, with reference answers.

A set is taken from the sample's evaluation answer set. Packages leave `bkn-eval/` out, so a set
carries its own questions and answers; `check_source` holds the copy to the source in the repository.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "experience-set.schema.json"
# Field names in expected values; any other mapping key is a business value such as a material code.
FIELD_NAME = re.compile(r"^[a-z][a-z0-9_]*$")

_validator: Draft202012Validator | None = None


def _schema_validator() -> Draft202012Validator:
    global _validator
    if _validator is None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        _validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return _validator


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def validate(document) -> list[str]:
    """Checks one set on its own, as a package carries it."""
    errors = [
        f"{'/'.join(str(p) for p in error.absolute_path) or '<root>'}: {error.message}"
        for error in sorted(_schema_validator().iter_errors(document), key=lambda e: list(e.absolute_path))
    ]
    if errors:
        return errors
    seen: set[str] = set()
    for case in document["spec"]["cases"]:
        case_id = case["id"]
        if case_id in seen:
            errors.append(f"{case_id}: duplicate case id")
        seen.add(case_id)
        missing = [value for value in answer_values(case["expected"]) if value not in case["answer"]]
        if missing:
            errors.append(f"{case_id}: answer does not name expected values {missing}")
    return errors


def answer_values(expected) -> list[str]:
    """The values a reader must find in the answer: numbers, codes and other text, not yes/no flags."""
    values: list[str] = []

    def walk(value) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if not FIELD_NAME.fullmatch(key):
                    values.append(key)
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, bool) or value is None:
            return
        elif isinstance(value, (int, float)):
            values.append(_number_text(value))
        else:
            values.append(str(value))

    walk(expected)
    return list(dict.fromkeys(values))


def _number_text(value) -> str:
    number = Decimal(str(value))
    return str(number.quantize(Decimal(1))) if number == number.to_integral_value() else str(number.normalize())


def check_source(sample_dir: Path, document: dict) -> list[str]:
    """Compares a set with the answer set it names; only the repository has that file."""
    source = document["metadata"]["source"]
    path = sample_dir / source["answerSet"]
    if not path.is_file():
        return [f"source answer set is missing: {source['answerSet']}"]
    answer_set = load(path)
    errors: list[str] = []
    if answer_set.get("set_id") != source["setId"]:
        errors.append(f"source setId {source['setId']!r} differs from {answer_set.get('set_id')!r}")
    if answer_set.get("business_date") != document["spec"]["businessDate"]:
        errors.append("businessDate differs from the source business_date")
    answers = {item["id"]: item for item in answer_set.get("answers", [])}
    for case in document["spec"]["cases"]:
        original = answers.get(case["id"])
        if original is None:
            errors.append(f"{case['id']}: not in the source answer set")
            continue
        if case["question"] != original.get("question"):
            errors.append(f"{case['id']}: question differs from the source")
        if case["expected"] != original.get("expected"):
            errors.append(f"{case['id']}: expected differs from the source")
    return errors


def compare_query_result(expected: dict, columns: list[str], rows: list[dict]) -> list[str]:
    """Matches a run_cypher result to expected values.

    A list of values is one column across all rows, compared as a set; a list of records is the
    rows themselves. Any other field is read from a single row.
    """
    errors: list[str] = []
    for field, value in expected.items():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            absent = [key for key in value[0] if key not in columns]
            if absent:
                errors.append(f"{field}: result has no columns {absent}")
                continue
            want = sorted(_record_key(item) for item in value)
            got = sorted(_record_key({key: row.get(key) for key in value[0]}) for row in rows)
            if want != got:
                errors.append(f"{field}: rows {got} differ from {want}")
        elif field not in columns:
            errors.append(f"result has no column {field}")
        elif isinstance(value, list):
            want = sorted((_normal(item) for item in value), key=str)
            got = sorted((_normal(row.get(field)) for row in rows), key=str)
            if want != got:
                errors.append(f"{field}: {got} differs from {want}")
        elif len(rows) != 1:
            errors.append(f"{field}: expected one row, got {len(rows)}")
        elif _normal(rows[0].get(field)) != _normal(value):
            errors.append(f"{field}: {rows[0].get(field)!r} differs from {value!r}")
    return errors


def _normal(value):
    if isinstance(value, bool) or value is None:
        return value
    try:
        return Decimal(str(value)).normalize()
    except InvalidOperation:
        return str(value)


def _record_key(record: dict) -> tuple:
    return tuple(sorted((key, str(_normal(value))) for key, value in record.items()))
