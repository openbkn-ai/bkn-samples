from fn.bom import bom_shared_list
from fn.inventory import layered_inventory
from fn.snapshot import build_snapshot
from fn.substitute import substitute_status


def test_layered_inventory_reads_all_bom_pages_and_filters_unavailable():
    bom = [{"bom_material_code":"P","bom_level":"0","material_code":"P","alt_priority":"0"}]
    bom += [{"bom_material_code":"P","bom_level":"1","material_code":f"M{i}","alt_priority":"0","alt_method":""} for i in range(501)]
    inv = [{"material_code":"M500","warehouse":"W","stock_status":'Available',"available_inventory_qty":"2"}, {"material_code":"M500","warehouse":"W","stock_status":'frozen',"available_inventory_qty":"99"}]
    out = layered_inventory(build_snapshot({"bom":bom,"inventory":inv}), "P", depth=1, warehouse_scope="all")
    assert len(out["lines"]) == 501
    assert next(x for x in out["lines"] if x["material_code"] == "M500")["available_qty"] == 2


def test_substitute_groups_are_parent_scoped_and_include_main_fact():
    rows = [
      {"bom_material_code":"P","bom_level":"0","material_code":"P","alt_priority":"0"},
      {"bom_material_code":"P","bom_level":"1","material_code":"A","parent_material_code":"PA","alt_group_no":"1","alt_priority":"0","alt_method":""},
      {"bom_material_code":"P","bom_level":"1","material_code":"AT","parent_material_code":"PA","alt_group_no":"1","alt_priority":"1","alt_method":'Alternate'},
      {"bom_material_code":"P","bom_level":"1","material_code":"B","parent_material_code":"PB","alt_group_no":"1","alt_priority":"0","alt_method":""},
      {"bom_material_code":"P","bom_level":"1","material_code":"BT","parent_material_code":"PB","alt_group_no":"1","alt_priority":"1","alt_method":'Alternate'},
    ]
    out = substitute_status(build_snapshot({"bom":rows}), "P", substitute_enabled=False)
    assert out["group_count"] == 2
    assert {g["parent_material_code"] for g in out["groups"]} == {"PA", "PB"}
    assert {m["material_code"] for g in out["groups"] for m in g["members"]} == {"A","AT","B","BT"}


def test_bom_shared_rejects_duplicate_product_arguments():
    snap = build_snapshot({"bom":[{"bom_material_code":"P","bom_level":"0","material_code":"P","alt_priority":"0"}]})
    try:
        bom_shared_list(snap, ["P", "P"])
    except Exception as exc:
        assert 'different products' in str(exc)
    else:
        raise AssertionError("duplicate product list must be rejected")
