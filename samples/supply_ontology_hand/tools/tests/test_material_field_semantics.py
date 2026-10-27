"""Sample-owned metadata and evaluation contract for Foundry #2516."""
import csv
import json
from pathlib import Path

import yaml

import import_kn as importer
from fn.leadtime import leadtime_details
from fn.snapshot import build_snapshot

PACKAGE = Path(__file__).resolve().parents[2]
KN = PACKAGE / "kn" / f"{PACKAGE.name}.json"


def material_properties(payload):
    material = next(o for o in payload["object_types"] if o["id"].endswith("_material"))
    return {p["name"]: p for p in material["data_properties"]}


def test_material_classifications_keep_distinct_meanings():
    fields = material_properties(json.loads(KN.read_text()))
    assert fields["group_name"]["display_name"] != fields["group_type"]["display_name"]
    for name, other in [("group_name", "group_type"), ("group_type", "group_name")]:
        prop = fields[name]
        assert prop["mapped_field"]["name"] == name
        # Both descriptions must identify the other field and distinguish it.
        assert other in prop["comment"]
        assert ("不同" in prop["comment"]) or ("distinct" in prop["comment"])


def test_import_sends_the_classification_metadata_without_rewriting(monkeypatch):
    source = json.loads(KN.read_text())
    sent = []
    lookups = 0

    def call(args):
        nonlocal lookups
        if args[2:4] == ["bkn", "get"]:
            lookups += 1
            if lookups == 1:
                raise RuntimeError("fixture network does not exist")
            return json.dumps({"id": source["id"], "name": source["name"]})
        assert args[2] == "call"
        sent.append(json.loads(args[-1]))
        return '{}'

    monkeypatch.setattr(importer, "run_cmd", call)
    assert importer.import_kn(KN)["verified"]
    assert len(sent) == 1
    actual = material_properties(sent[0])
    expected = material_properties(source)
    for name in ["group_name", "group_type"]:
        assert actual[name] == expected[name]


def test_field_semantics_case_matches_csv_and_requires_all_facts():
    datasets = PACKAGE / "bkn-eval" / "datasets"
    questions = yaml.safe_load((datasets / "material-field-questions-v1.yaml").read_text())
    answers = yaml.safe_load((datasets / "material-field-answers-v1.yaml").read_text())
    assert questions["audience"] == "evaluated_agent"
    assert questions["answer_set_access"] == "forbidden"
    assert answers["evaluated_agent_access"] == "forbidden"
    assert [q["id"] for q in questions["questions"]] == [a["id"] for a in answers["answers"]] == ["MF-01"]
    expected = answers["answers"][0]["answer"]
    with (PACKAGE / "data" / "erp_material.csv").open(encoding="utf-8-sig") as f:
        row = next(r for r in csv.DictReader(f) if r["material_code"] == expected["material_code"])
    result = leadtime_details(build_snapshot({"material": [row]}), row["material_code"])
    assert result["leadtime_days"] == expected["leadtime_days"] == 1
    assert result["source_field"] == expected["source_field"] == "product_fixedleadtime"
    assert expected["group_name"] == row["group_name"]
    assert expected["group_type"] == row["group_type"]
    assert expected["group_name"] != expected["group_type"]
    assert {"leadtime_days", "source_field", "unit", "group_name", "group_type"} <= expected.keys()
    assert answers["answers"][0]["all_facts_required"] is True
