from __future__ import annotations

from .bom import explode_leaf_usage
from .errors import CannotCompute
from .inventory import available_qty, in_transit_qty
from .warehouse import resolve_warehouse_scope


def kitting_net_demand(
    snap,
    product: str,
    qty: float,
    *,
    warehouse_scope: str | list[str] | None = "production_available",
    substitute_enabled: bool | None = False,
    report_grain: str = "summary",
) -> dict:
    product = (product or "").strip()
    if not product:
        raise CannotCompute("缺少产品编码")
    if qty is None:
        raise CannotCompute("缺少数量 X，不能算净需求")
    if substitute_enabled is None:
        raise CannotCompute("未确认是否启用替代料，不能算净需求")
    try:
        demand_qty = float(qty)
    except (TypeError, ValueError) as exc:
        raise CannotCompute("数量 X 无效") from exc
    if demand_qty < 0:
        raise CannotCompute("数量 X 不能为负")
    if report_grain not in {"summary", "full"}:
        raise CannotCompute(f"report_grain 只能是 summary 或 full：{report_grain}")

    leaves = explode_leaf_usage(
        snap, product, include_substitute=bool(substitute_enabled)
    )
    warehouses = resolve_warehouse_scope(warehouse_scope)
    lines = []
    gaps = []
    for code, item in leaves.items():
        usage = float(item["usage_per_unit"] or 0)
        gross = demand_qty * usage
        avail = available_qty(snap, code, warehouse_scope)
        transit = in_transit_qty(snap, code)
        chosen = code
        source = "main"
        if substitute_enabled:
            best_cover = avail + transit
            for alt in item.get("substitutes") or []:
                alt_code = alt["material_code"]
                cover = available_qty(snap, alt_code, warehouse_scope) + in_transit_qty(
                    snap, alt_code
                )
                if cover > best_cover:
                    best_cover = cover
                    chosen = alt_code
                    source = "substitute"
                    avail = available_qty(snap, alt_code, warehouse_scope)
                    transit = in_transit_qty(snap, alt_code)
        net = max(0.0, gross - avail - transit)
        rec = {
            "material_code": chosen,
            "main_material_code": code,
            "l1_parent": item.get("l1_parent", ""),
            "material_name": item.get("material_name", ""),
            "gross_requirement": gross,
            "available_qty": avail,
            "in_transit_qty": transit,
            "net_requirement": net,
            # This is the replenishment quantity justified by this demand
            # snapshot only.  MOQ, safety stock and other policies require
            # separate business input and must not be silently added.
            "recommended_replenishment_qty": net,
            "source": source,
        }
        lines.append(rec)
        if net > 0:
            gaps.append(rec)
    result = {
        "product_code": product,
        "demand_qty": demand_qty,
        "kitting_ok": len(gaps) == 0,
        "report_grain": report_grain,
        "line_count": len(lines),
        "gap_count": len(gaps),
        "gaps": gaps,
        "warehouse_scope": warehouse_scope if not isinstance(warehouse_scope, list) else "custom",
        "warehouse_filter": warehouses,
        "substitute_enabled": bool(substitute_enabled),
        "include_in_transit": True,
    }
    if report_grain == "full":
        result["lines"] = lines
    return result
