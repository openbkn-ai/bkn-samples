"""Facts the native Functions read inside their sandbox, and the calculation they run.

The caller supplies business parameters only. The Function reads the BOM trees of the
requested products, stock of every material in them, and, when the question needs them,
purchase lines and signed sales orders through ``sandbox_sdk.bkn``; then it runs
``fn.planning``.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from fn import CannotCompute, build_capacity, demand_coverage, resolve_warehouse_scope
from fn.read_complete import read_complete

KN_ID = "supply_ontology_hand"
OPERATIONS = ("build_capacity", "demand_coverage")
_OBJECT_TYPES = {
    "bom": "supply_ontology_hand_bom",
    "inventory": "supply_ontology_hand_inventory",
    "purchase_order": "supply_ontology_hand_po",
    "sales_order": "supply_ontology_hand_salesorder",
}
_PAGE_SIZE = 500
_MAX_ROWS_PER_DATASET = 50_000


def _equal(field: str, value: Any) -> dict[str, Any]:
    return {"field": field, "operation": "==", "value": value, "value_from": "const"}


def _in(field: str, values: list[str]) -> dict[str, Any]:
    return {"field": field, "operation": "in", "value": values, "value_from": "const"}


def _and(conditions: list[dict[str, Any]]) -> dict[str, Any]:
    return conditions[0] if len(conditions) == 1 else {"operation": "and", "sub_conditions": conditions}


def _page_rows(page: Mapping[str, Any]) -> list[dict[str, Any]]:
    for key in ("datas", "data", "rows"):
        rows = page.get(key)
        if isinstance(rows, list):
            return [dict(row) for row in rows if isinstance(row, Mapping)]
    return []


def _products(operation: str, params: Mapping[str, Any]) -> list[str]:
    if operation == "build_capacity":
        products = params.get("products")
        if not isinstance(products, list) or not [p for p in products if str(p or "").strip()]:
            raise CannotCompute("请提供至少一个产品编码")
        return sorted({str(p).strip() for p in products if str(p or "").strip()})
    demands = params.get("demands")
    if not isinstance(demands, list) or not demands:
        raise CannotCompute('请按 [{"product": "产品编码", "qty": 数量}] 提供至少一条需求')
    products = []
    for demand in demands:
        if not isinstance(demand, Mapping) or not str(demand.get("product") or "").strip() or not demand.get("qty"):
            raise CannotCompute("每条需求都要有产品编码和大于 0 的数量")
        products.append(str(demand["product"]).strip())
    return sorted(set(products))


def load_bkn_rows(operation: str, query_object_instance: Callable[..., Mapping[str, Any]],
                  parameters: Mapping[str, Any] | None = None) -> dict[str, list[dict[str, Any]]]:
    """Read only the facts the question needs, filtered on the server."""
    if operation not in OPERATIONS:
        raise CannotCompute(f"未知函数：{operation}")
    params = dict(parameters or {})
    products = _products(operation, params)

    def read(dataset: str, condition: dict[str, Any]) -> list[dict[str, Any]]:
        return read_complete(query_object_instance, {"kn_id": KN_ID, "ot_id": _OBJECT_TYPES[dataset], "condition": condition},
                             _page_rows, page_size=_PAGE_SIZE, max_rows=_MAX_ROWS_PER_DATASET)

    bom = read("bom", _in("bom_material_code", products))
    codes = sorted(set(products) | {str(row.get("material_code") or "") for row in bom} - {""})
    stock = [_in("material_code", codes), _equal("stock_status", "可用")]
    warehouses = resolve_warehouse_scope(params.get("warehouse_scope", "all"))
    if warehouses:
        stock.append(_in("warehouse", warehouses))
    rows = {"bom": bom, "inventory": read("inventory", _and(stock))}
    if params.get("need_by") or params.get("chase_overdue_po"):
        rows["purchase_order"] = read("purchase_order", _and([_in("material_number", codes),
                                                               _equal("rowclosestatus_title", "正常"),
                                                               _equal("rowterminatestatus_title", "正常")]))
    if operation == "build_capacity" or params.get("reserve_signed_backlog"):
        rows["sales_order"] = read("sales_order", _in("product_code", products))
    return rows


def execute_from_bkn_rows(operation: str, rows: Mapping[str, list[dict[str, Any]]],
                          parameters: Mapping[str, Any] | None = None) -> dict[str, Any]:
    params = dict(parameters or {})
    common = {key: params[key] for key in ("substitute_enabled", "warehouse_scope", "need_by", "chase_overdue_po",
                                           "business_date") if params.get(key) is not None}
    if operation == "build_capacity":
        products = list(dict.fromkeys(str(p).strip() for p in params["products"] if str(p or "").strip()))
        return {"products": [build_capacity(rows, product, **common) for product in products]}
    if operation == "demand_coverage":
        extra = {key: params[key] for key in ("reserve_signed_backlog", "use_finished_goods") if params.get(key) is not None}
        return demand_coverage(rows, list(params["demands"]), **common, **extra)
    raise CannotCompute(f"未知函数：{operation}")


__all__ = ["KN_ID", "OPERATIONS", "execute_from_bkn_rows", "load_bkn_rows"]
