from __future__ import annotations

from .allocation import finite_quantity, net_requirements
from .errors import CannotCompute
from .inventory import available_qty, in_transit_qty
from .warehouse import resolve_warehouse_scope


def kitting_net_demand(
    snap,
    product: str,
    qty: float,
    *,
    warehouse_scope: str | list[str] | None = "all",
    substitute_enabled: bool | None = False,
    report_grain: str = "summary",
) -> dict:
    product = (product or "").strip()
    if not product:
        raise CannotCompute('Missing product code')
    if qty is None:
        raise CannotCompute('Missing quantity X; cannot calculate net demand')
    if substitute_enabled is None:
        raise CannotCompute('Explicitly confirm the alternate policy before calculating net demand')
    try:
        demand_qty = float(qty)
    except (TypeError, ValueError) as exc:
        raise CannotCompute('Invalid quantity X') from exc
    demand_qty = finite_quantity(demand_qty, 'quantity X')
    if report_grain not in {"summary", "full"}:
        raise CannotCompute(f"""report_grain must be summary or full: {report_grain}""")

    allocation = net_requirements(snap, product, demand_qty, scope=warehouse_scope, substitute_enabled=bool(substitute_enabled), include_finished_goods=True)
    warehouses = resolve_warehouse_scope(warehouse_scope)
    lines = []
    gaps = []
    for item in allocation["lines"]:
        code = item["material_code"]
        gross = item["gross_requirement"]
        avail = item["available_qty"]
        net = item["net_requirement"]
        source = item["source"]
        usage = item["usage_per_unit"]
        transit = 0.0
        rec = {
            "material_code": code,
            "main_material_code": item["main_material_code"],
            "l1_parent": item.get("parent_material_code", ""),
            "material_name": "",
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
        "include_in_transit": False,
        "finished_goods_qty": allocation["finished_goods_qty"],
        "finished_goods_allocated_qty": allocation["finished_goods_allocated_qty"],
        "root_net_demand": allocation["root_net_demand"],
    }
    if report_grain == "full":
        result["lines"] = lines
    return result
