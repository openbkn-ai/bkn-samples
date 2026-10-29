from __future__ import annotations

from .allocation import finite_quantity, net_requirements
from .errors import CannotCompute
from .warehouse import resolve_warehouse_scope


def kitting_net_demand(
    snap,
    product: str,
    qty: float,
    *,
    warehouse_scope: str | list[str] | None = "production_available",
    substitute_enabled: bool | None = False,
    report_grain: str = "summary",
    demand_mode: str = "production",
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
    demand_qty = finite_quantity(demand_qty, "数量 X")
    if demand_mode not in {"production", "fulfillment"}:
        raise CannotCompute("demand_mode 只能是 production 或 fulfillment")
    if report_grain not in {"summary", "full"}:
        raise CannotCompute(f"report_grain 只能是 summary 或 full：{report_grain}")

    transit_pool = {}
    allocation = net_requirements(snap, product, demand_qty, scope=warehouse_scope, substitute_enabled=bool(substitute_enabled), include_finished_goods=demand_mode == "fulfillment", finished_goods_scope="finished_goods", include_in_transit=True, transit_pool=transit_pool)
    warehouses = resolve_warehouse_scope(warehouse_scope)
    lines = []
    gaps = []
    for item in allocation["lines"]:
        code = item["material_code"]
        gross = item["gross_requirement"]
        avail = item["available_qty"]
        net = item["net_requirement"]
        source = item["source"]
        transit = item["in_transit_qty"]
        rec = {
            "material_code": code,
            "main_material_code": item["main_material_code"],
            "l1_parent": item.get("parent_material_code", ""),
            "material_name": item["material_name"],
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
        rec["is_leaf"] = item["is_leaf"]
        rec["allocated_qty"] = item["allocated_qty"]
        if net > 1e-9 and item["is_leaf"]:
            gaps.append(rec)
    # Business questions ask distinct material kinds; keep BOM positions in
    # full lines while combining repeated leaf gaps for the summary.
    by_code = {}
    for gap in gaps:
        code = gap["material_code"]
        if code not in by_code:
            by_code[code] = dict(gap)
        else:
            combined = by_code[code]
            for field in ("gross_requirement", "available_qty", "in_transit_qty",
                          "net_requirement", "recommended_replenishment_qty", "allocated_qty"):
                combined[field] += gap[field]
            combined["l1_parent"] = ""
    gaps = list(by_code.values())
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
        "demand_mode": demand_mode,
        "finished_goods_qty": allocation["finished_goods_qty"],
        "finished_goods_allocated_qty": allocation["finished_goods_allocated_qty"],
        "root_net_demand": allocation["root_net_demand"],
    }
    if report_grain == "full":
        result["lines"] = lines
    return result
