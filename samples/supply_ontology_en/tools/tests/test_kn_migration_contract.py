import csv
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

    assert len(object_ids) == 14
    assert len(kn["relation_types"]) == 21
    assert "skills" not in object_ids
    mapping = yaml.safe_load((REPO_ROOT / "samples/supply_ontology_en/tools/mapping/object_table_map.yaml").read_text())
    # The kit schedule plan is a dataset the sample writes, bound by setup_kit_plan_dataset.py, not a table.
    assert object_ids == {item["object_type_id"] for item in mapping["objects"] if item.get("bind", True)} | {
        "supply_ontology_en_kitplan"}
    manifest = yaml.safe_load((REPO_ROOT / "samples/supply_ontology_en/sample.yaml").read_text())
    assert manifest["spec"]["components"]["skills"] is True
    assert kn["action_types"] == []
    endpoints = {r["source_object_type_id"] for r in kn["relation_types"]} | {r["target_object_type_id"] for r in kn["relation_types"]}
    assert endpoints <= object_ids


def test_kn_has_no_environment_specific_resource_ids():
    text = (REPO_ROOT / "samples" / "supply_ontology_en" / "kn" / "supply_ontology_en.json").read_text()
    assert "d9v" not in text
    assert "localhost" not in text.lower()


def test_production_plans_reach_their_products():
    """A production plan names the product it makes; scheduling follows it to the product's BOM."""
    kn = load_kn("supply_ontology_en", "supply_ontology_en.json")
    relation = next(r for r in kn["relation_types"] if r["id"] == "supply_ontology_en_mps2prod")
    assert (relation["source_object_type_id"], relation["target_object_type_id"]) == (
        "supply_ontology_en_mps",
        "supply_ontology_en_product",
    )
    rule = relation["mapping_rules"][0]
    assert (rule["source_property"]["name"], rule["target_property"]["name"]) == (
        "material_number",
        "material_number",
    )
    data = REPO_ROOT / "samples" / "supply_ontology_en" / "data"
    with (data / "hd_product_view.csv").open(encoding="utf-8") as products:
        codes = {row["material_code"] for row in csv.DictReader(products)}
    with (data / "erp_production_work_order.csv").open(encoding="utf-8") as plans:
        rows = list(csv.DictReader(plans))
    assert rows and all(row["material_number"] in codes for row in rows)
