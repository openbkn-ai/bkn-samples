"""CSV rows served the way the platform's object query returns them, for native-function tests."""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data"
TABLES = {
    "supply_ontology_en_bom": "erp_material_bom",
    "supply_ontology_en_inventory": "erp_real_time_inventory",
    "supply_ontology_en_po": "erp_purchase_order",
    "supply_ontology_en_salesorder": "sales_order",
    "supply_ontology_en_forecast": "erp_mds_forecast",
    "supply_ontology_en_line": "production_line",
    "supply_ontology_en_product": "hd_product_view",
    "supply_ontology_en_material": "erp_material",
    "supply_ontology_en_kitplan": "kit_schedule_plan",
    "supply_ontology_en_mps": "erp_production_work_order",
}
# Object property names that differ from the table column they map.
RENAMED = {"supply_ontology_en_product": {"material_code": "material_number"}}


@lru_cache(maxsize=None)
def table(name: str) -> tuple[dict, ...]:
    with (DATA / f"{name}.csv").open(newline="", encoding="utf-8-sig") as fh:
        return tuple(csv.DictReader(fh))


def csv_rows() -> dict[str, list[dict]]:
    return {"bom": list(table("erp_material_bom")), "inventory": list(table("erp_real_time_inventory")),
            "purchase_order": list(table("erp_purchase_order")), "sales_order": list(table("sales_order"))}


def _matches(row: dict, condition: dict | None) -> bool:
    if not condition:
        return True
    operation = condition["operation"]
    if operation == "and":
        return all(_matches(row, item) for item in condition["sub_conditions"])
    value = row.get(condition["field"])
    if operation == "==":
        return value == condition["value"]
    if operation == "in":
        return value in condition["value"]
    raise AssertionError(f"unexpected operation {operation}")


class FakeObjectQuery:
    """Records each query and pages through matching CSV rows in reverse, unlike file order."""

    def __init__(self, objects: dict[str, list[dict]] | None = None):
        self.calls: list[dict] = []
        self.objects = objects or {}

    def _rows(self, ot_id: str) -> list[dict]:
        if ot_id in self.objects:
            return [dict(r) for r in self.objects[ot_id]]
        rename = RENAMED.get(ot_id, {})
        return [{rename.get(k, k): v for k, v in r.items()} for r in table(TABLES[ot_id])]

    def __call__(self, **query):
        self.calls.append(query)
        rows = [r for r in reversed(self._rows(query["ot_id"])) if _matches(r, query.get("condition"))]
        start = query.get("offset", 0)
        return {"datas": [dict(r) for r in rows[start:start + query["limit"]]], "total_count": len(rows)}
