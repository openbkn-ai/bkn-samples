from __future__ import annotations

from collections import defaultdict

from .bom import bom_list
from .errors import CannotCompute
from .snapshot import Snapshot, _f
from .warehouse import resolve_warehouse_scope


def available_qty(
    snap: Snapshot,
    material_code: str,
    warehouse_scope: str | list[str] | None = "production_available",
) -> float:
    warehouses = resolve_warehouse_scope(warehouse_scope)
    total = 0.0
    code = (material_code or "").strip()
    for row in snap.inv_by_material.get(code, []):
        wh = (row.get("warehouse") or "").strip()
        if warehouses and wh not in warehouses:
            continue
        total += _f(row.get("available_inventory_qty"), 0.0)
    return total


def reserved_qty(
    snap: Snapshot,
    material_code: str,
    warehouse_scope: str | list[str] | None = "production_available",
) -> float:
    warehouses = resolve_warehouse_scope(warehouse_scope)
    total = 0.0
    code = (material_code or "").strip()
    for row in snap.inv_by_material.get(code, []):
        wh = (row.get("warehouse") or "").strip()
        if warehouses and wh not in warehouses:
            continue
        total += _f(row.get("reserved_inventory_qty"), 0.0)
    return total


def in_transit_qty(snap: Snapshot, material_code: str) -> float:
    """Unclosed PO open qty: max(0, qty - actqty). PR is not included."""
    code = (material_code or "").strip()
    total = 0.0
    for row in snap.po_by_material.get(code, []):
        status = (row.get("rowclosestatus_title") or "").strip()
        if status == "已关闭":
            continue
        qty = _f(row.get("qty"), 0.0)
        act = _f(row.get("actqty"), 0.0)
        total += max(0.0, qty - act)
    return total


def pr_open_qty(snap: Snapshot, material_code: str) -> float:
    code = (material_code or "").strip()
    total = 0.0
    for row in snap.pr_by_material.get(code, []):
        status = (row.get("rowclosestatus_title") or "").strip()
        if status == "已关闭":
            continue
        qty = _f(row.get("qty"), 0.0)
        joined = _f(row.get("joinqty"), 0.0)
        total += max(0.0, qty - joined)
    return total


def has_mrp(snap: Snapshot, material_code: str) -> bool:
    code = (material_code or "").strip()
    for row in snap.mrp_by_material.get(code, []):
        status = (row.get("closestatus_title") or "").strip()
        if status == "已关闭":
            continue
        return True
    return False


def po_open_rows(snap: Snapshot, material_code: str) -> list[dict]:
    code = (material_code or "").strip()
    return [
        row
        for row in snap.po_by_material.get(code, [])
        if (row.get("rowclosestatus_title") or "").strip() != "已关闭"
    ]


def pr_open_rows(snap: Snapshot, material_code: str) -> list[dict]:
    code = (material_code or "").strip()
    return [
        row
        for row in snap.pr_by_material.get(code, [])
        if (row.get("rowclosestatus_title") or "").strip() != "已关闭"
    ]


def layered_inventory(
    snap: Snapshot,
    product: str,
    *,
    depth: int | None = 1,
    warehouse_scope: str | list[str] | None = "production_available",
    include_substitute: bool = False,
) -> dict:
    product = (product or "").strip()
    if not product:
        raise CannotCompute("缺少产品编码")
    listing = bom_list(
        snap,
        product,
        depth=depth,
        include_substitute=include_substitute,
        report_grain="full",
        page_size=500,
    )
    warehouses = resolve_warehouse_scope(warehouse_scope)
    lines = []
    for line in listing["lines"]:
        code = line["material_code"]
        lines.append(
            {
                **line,
                "available_qty": available_qty(snap, code, warehouse_scope),
                "reserved_qty": reserved_qty(snap, code, warehouse_scope),
            }
        )
    return {
        "product_code": product,
        "depth": depth,
        "warehouse_scope": warehouse_scope if not isinstance(warehouse_scope, list) else "custom",
        "warehouse_filter": warehouses,
        "lines": lines,
        "note": "reserved 仅展示，P0 不扣减",
    }
