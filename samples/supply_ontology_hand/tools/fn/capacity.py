from __future__ import annotations

import math

from .bom import explode_leaf_usage
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
    leaves = explode_leaf_usage(
        snap, product, include_substitute=bool(substitute_enabled)
    )
    warehouses = resolve_warehouse_scope(warehouse_scope)
    constraints = []
    qty = None
    bottleneck = None
    for code, item in leaves.items():
        usage = float(item["usage_per_unit"] or 0)
        main_avail = available_qty(snap, code, warehouse_scope)
        main_can = _floor_div(main_avail, usage)
        used_code = code
        used_can = main_can
        source = "main"
        if substitute_enabled:
            for alt in item.get("substitutes") or []:
                alt_usage = float(alt.get("usage_per_unit") or usage)
                alt_can = _floor_div(
                    available_qty(snap, alt["material_code"], warehouse_scope),
                    alt_usage,
                )
                if alt_can > used_can:
                    used_can = alt_can
                    used_code = alt["material_code"]
                    source = "substitute"
        constraints.append(
            {
                "material_code": code,
                "material_name": item.get("material_name", ""),
                "usage_per_unit": usage,
                "available_qty": main_avail,
                "max_build_qty": main_can,
                "chosen_code": used_code,
                "chosen_qty": used_can,
                "source": source,
            }
        )
        if qty is None or used_can < qty:
            qty = used_can
            bottleneck = {
                "material_code": used_code,
                "main_material_code": code,
                "max_build_qty": used_can,
                "source": source,
            }
    theoretical = 0 if qty is None else int(qty)
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
