from __future__ import annotations

import math

from .allocation import net_requirements
from .errors import CannotCompute
from .inventory import available_qty
from .warehouse import resolve_warehouse_scope


def _floor_div(avail: float, usage: float) -> int:
    if usage <= 0:
        return 0
    return int(math.floor(avail / usage))


def theoretical_build(
    snap,
    product: str,
    *,
    warehouse_scope: str | list[str] | None = "production_available",
    substitute_enabled: bool | None = False,
    report_grain: str = "summary",
) -> dict:
    product = (product or "").strip()
    if not product:
        raise CannotCompute("缺少产品编码")
    if substitute_enabled is None:
        raise CannotCompute("未确认是否启用替代料，不能算理论可产")
    if report_grain not in {"summary", "full"}:
        raise CannotCompute(f"report_grain 只能是 summary 或 full：{report_grain}")
    warehouses = resolve_warehouse_scope(warehouse_scope)
    def allocate(quantity):
        return net_requirements(snap, product, quantity, scope=warehouse_scope,
                                substitute_enabled=bool(substitute_enabled),
                                include_finished_goods=False)
    # Integer search with a proved infeasible upper bound. A sum of inventory
    # quantities is not a bound when BOM usage is fractional.
    lo, hi = 0, 1
    while allocate(hi)["feasible"]:
        lo = hi
        hi *= 2
        if hi > 2**53:
            raise CannotCompute("理论产量超过可精确计算的整数范围")
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if allocate(mid)["feasible"]:
            lo = mid
        else:
            hi = mid
    theoretical = lo
    boundary = allocate(theoretical + 1)
    constraints = []
    for item in boundary["lines"]:
        if not item["is_leaf"]:
            continue
        constraints.append({
            "material_code": item["material_code"],
            "material_name": item["material_name"],
            "usage_per_unit": item["usage_per_unit"],
            "available_qty": item["available_qty"],
            "max_build_qty": theoretical if item["net_requirement"] > 1e-9 else None,
            "chosen_code": item["material_code"],
            "chosen_qty": theoretical,
            "source": item["source"],
            "boundary_demand_qty": theoretical + 1,
            "boundary_shortage": item["net_requirement"],
        })
    blocked = next((item for item in boundary["lines"]
                    if item["is_leaf"] and item["net_requirement"] > 1e-9), None)
    bottleneck = ({"material_code": blocked["material_code"],
                   "main_material_code": blocked["main_material_code"],
                   "material_name": blocked["material_name"],
                   "max_build_qty": theoretical, "source": blocked["source"]}
                  if blocked else None)
    result = {
        "product_code": product,
        "theoretical_build_qty": theoretical,
        "bottleneck": bottleneck,
        "report_grain": report_grain,
        "constraint_count": len(constraints),
        "warehouse_scope": warehouse_scope if not isinstance(warehouse_scope, list) else "custom",
        "warehouse_filter": warehouses,
        "substitute_enabled": bool(substitute_enabled),
        "include_finished_goods": False,
        "include_in_transit": False,
    }
    if report_grain == "full":
        result["constraints"] = constraints
    return result


def total_sellable(
    snap,
    product: str,
    *,
    production_scope: str | list[str] | None = "production_available",
    finished_goods_scope: str | list[str] | None = "finished_goods",
    substitute_enabled: bool | None = False,
) -> dict:
    product = (product or "").strip()
    if not product:
        raise CannotCompute("缺少产品编码")
    if substitute_enabled is None:
        raise CannotCompute("未确认是否启用替代料，不能算合计可售")
    th = theoretical_build(
        snap,
        product,
        warehouse_scope=production_scope,
        substitute_enabled=substitute_enabled,
    )
    fg_filter = resolve_warehouse_scope(finished_goods_scope)
    prod_filter = resolve_warehouse_scope(production_scope)
    fg_qty = available_qty(snap, product, finished_goods_scope)
    total = int(math.floor(fg_qty + th["theoretical_build_qty"]))
    return {
        "product_code": product,
        "fg_qty": fg_qty,
        "theoretical_build_qty": th["theoretical_build_qty"],
        "total_sellable_qty": total,
        "bottleneck": th.get("bottleneck"),
        "finished_goods_scope": finished_goods_scope if not isinstance(finished_goods_scope, list) else "custom",
        "finished_goods_filter": fg_filter,
        "production_scope": production_scope if not isinstance(production_scope, list) else "custom",
        "production_filter": prod_filter,
        "substitute_enabled": bool(substitute_enabled),
        "include_in_transit": False,
    }


def max_build_without_po(
    snap,
    product: str,
    *,
    warehouse_scope: str | list[str] | None = "production_available",
    substitute_enabled: bool | None = False,
    report_grain: str = "summary",
) -> dict:
    out = theoretical_build(
        snap,
        product,
        warehouse_scope=warehouse_scope,
        substitute_enabled=substitute_enabled,
        report_grain=report_grain,
    )
    out = dict(out)
    out["scene"] = "inventory_build"
    return out
