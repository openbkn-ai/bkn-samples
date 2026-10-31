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
}


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

    def __init__(self):
        self.calls: list[dict] = []

    def __call__(self, **query):
        self.calls.append(query)
        rows = [r for r in reversed(table(TABLES[query["ot_id"]])) if _matches(r, query.get("condition"))]
        start = query.get("offset", 0)
        return {"datas": [dict(r) for r in rows[start:start + query["limit"]]], "total_count": len(rows)}
