import json
import yaml
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]


def load_kn(sample_name, filename):
    return json.loads(
        (REPO_ROOT / "samples" / sample_name / "kn" / filename).read_text()
    )


def test_english_kn_keeps_only_objects_backed_by_data():
    kn = load_kn("supply_ontology_en", "supply_ontology_en.json")
    object_ids = {item["id"] for item in kn["object_types"]}

    assert len(object_ids) == 11
    assert len(kn["relation_types"]) == 14
    assert "skills" not in object_ids
    mapping = yaml.safe_load((REPO_ROOT / "samples/supply_ontology_en/tools/mapping/object_table_map.yaml").read_text())
    assert object_ids == {item["object_type_id"] for item in mapping["objects"] if item.get("bind", True)}
    manifest = yaml.safe_load((REPO_ROOT / "samples/supply_ontology_en/sample.yaml").read_text())
    assert manifest["spec"]["components"]["skills"] is True
    assert kn["action_types"] == []
    endpoints = {r["source_object_type_id"] for r in kn["relation_types"]} | {r["target_object_type_id"] for r in kn["relation_types"]}
    assert endpoints <= object_ids


def test_kn_has_no_environment_specific_resource_ids():
    text = (REPO_ROOT / "samples" / "supply_ontology_en" / "kn" / "supply_ontology_en.json").read_text()
    assert "d9v" not in text
    assert "localhost" not in text.lower()
