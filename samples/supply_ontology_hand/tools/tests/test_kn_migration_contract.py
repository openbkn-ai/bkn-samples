import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]


def load_kn(sample_name, filename):
    return json.loads(
        (REPO_ROOT / "samples" / sample_name / "kn" / filename).read_text()
    )


def test_chinese_kn_is_full_capability_snapshot():
    kn = load_kn("supply_ontology_hand", "supply_ontology_hand.json")
    object_ids = {item["id"] for item in kn["object_types"]}
    action_ids = {item["id"] for item in kn["action_types"]}

    assert len(object_ids) >= 14
    assert len(kn["relation_types"]) >= 13
    assert "skills" in object_ids
    assert "supply_ontology_hand_act_mon_close" in action_ids


def test_kn_has_no_environment_specific_resource_ids():
    text = (REPO_ROOT / "samples" / "supply_ontology_hand" / "kn" / "supply_ontology_hand.json").read_text()
    assert "d9v" not in text
    assert "localhost" not in text.lower()
