from pathlib import Path
import yaml

MAP = Path(__file__).resolve().parents[1] / "mapping" / "object_table_map.yaml"
SAMPLE = Path(__file__).resolve().parents[2] / "data"

REQUIRED_OT = {
    "supply_ontology_en_material",
    "supply_ontology_en_product",
    "supply_ontology_en_bom",
    "supply_ontology_en_inventory",
    "supply_ontology_en_supplier",
    "supply_ontology_en_forecast",
    "supply_ontology_en_mrp",
    "supply_ontology_en_pr",
    "supply_ontology_en_po",
    "supply_ontology_en_mps",
    "supply_ontology_en_salesorder",
}


def test_map_covers_all_object_types():
    data = yaml.safe_load(MAP.read_text(encoding="utf-8"))
    objects = data["objects"]
    ids = {o["object_type_id"] for o in objects}
    assert REQUIRED_OT <= ids


def test_required_tables_exist_as_csv():
    data = yaml.safe_load(MAP.read_text(encoding="utf-8"))
    for o in data["objects"]:
        if o.get("bind") is False:
            continue
        table = o["table"]
        assert (SAMPLE / f"{table}.csv").is_file(), table


def test_load_order_mentions_material_before_bom():
    data = yaml.safe_load(MAP.read_text(encoding="utf-8"))
    order = data["load_order"]
    assert order.index("erp_material") < order.index("erp_material_bom")
    assert order.index("hd_product_view") < order.index("sales_order")
