from __future__ import annotations

from collections import defaultdict

from .errors import CannotCompute
from .allocation import finite_quantity, net_requirements
from .warehouse import resolve_warehouse_scope


def shared_contention(
    snap,
    demands: list[dict],
    *,
    warehouse_scope: str | list[str] | None = "production_available",
    substitute_enabled: bool | None = False,
    report_grain: str = "summary",
    demand_mode: str = "production",
) -> dict:
    """Deduct a common available-inventory and unclosed-PO pools in demand list order."""
    if not demands or len(demands) < 2:
        raise CannotCompute("共用料争用至少需要 2 条需求")
    if substitute_enabled is None:
        raise CannotCompute("未确认是否启用替代料，不能算争用")
    if demand_mode not in {"production", "fulfillment"}:
        raise CannotCompute("demand_mode 只能是 production 或 fulfillment")
    if report_grain not in {"summary", "full"}:
        raise CannotCompute(f"report_grain 只能是 summary 或 full：{report_grain}")

    normalized = []
    for item in demands:
        product = (item.get("product") or item.get("product_code") or "").strip()
        qty = item.get("qty", item.get("demand_qty"))
        if not product:
            raise CannotCompute("需求缺少产品编码")
        if qty is None:
            raise CannotCompute(f"{product} 缺少数量，不能算争用（数量未定请改用产品 BOM 共用清单）")
        normalized.append({"product_code": product, "qty": finite_quantity(qty, "需求数量")})

    warehouses = resolve_warehouse_scope(warehouse_scope)
    pool = {}
    transit_pool = {}
    allocations = []
    occurrences = defaultdict(set)
    for index, dem in enumerate(normalized):
        net = net_requirements(snap, dem["product_code"], dem["qty"], scope=warehouse_scope,
                               substitute_enabled=bool(substitute_enabled),
                               include_finished_goods=demand_mode == "fulfillment", finished_goods_scope="finished_goods", include_in_transit=True, transit_pool=transit_pool, pool=pool)
        rows = []
        if net["finished_goods_qty"] > 0:
            rows.append({"material_code": dem["product_code"], "gross_requirement": dem["qty"],
                         "allocated": net["finished_goods_allocated_qty"], "shortage": 0.0,
                         "is_leaf": False, "role": "finished_goods"})
        for line in net["lines"]:
            rows.append({"material_code": line["material_code"],
                         "gross_requirement": line["gross_requirement"],
                         "allocated": line["allocated_qty"],
                         "shortage": line["net_requirement"] if line["is_leaf"] else 0.0,
                         "component_net_requirement": line["net_requirement"],
                         "is_leaf": line["is_leaf"], "source": line["source"]})
        for row in rows:
            occurrences[row["material_code"]].add(index)
        allocations.append({"product_code": dem["product_code"], "demand_qty": dem["qty"],
                            "satisfied": net["feasible"], "lines": rows})
    for allocation in allocations:
        for row in allocation["lines"]:
            row["shared"] = len(occurrences[row["material_code"]]) > 1
    remaining = dict(pool)
    shared_shortages = {
        row["material_code"]
        for allocation in allocations
        for row in allocation["lines"]
        if row["shared"] and row["shortage"] > 0
    }
    summarized_allocations = []
    for allocation in allocations:
        shortages = [
            {
                "material_code": row["material_code"],
                "shortage": row["shortage"],
                "shared": row["shared"],
            }
            for row in allocation["lines"]
            if row["shortage"] > 0
        ]
        distinct = {}
        for item in shortages:
            code = item["material_code"]
            if code in distinct:
                distinct[code]["shortage"] += item["shortage"]
            else:
                distinct[code] = dict(item)
        shortages = list(distinct.values())
        summarized_allocations.append(
            {
                "product_code": allocation["product_code"],
                "demand_qty": allocation["demand_qty"],
                "satisfied": allocation["satisfied"],
                "shortage_count": len(shortages),
                "shortages": shortages,
            }
        )
    result = {
        "demands": normalized,
        "report_grain": report_grain,
        "all_satisfied": all(allocation["satisfied"] for allocation in allocations),
        "unsatisfied_demand_count": sum(
            not allocation["satisfied"] for allocation in allocations
        ),
        "shared_shortage_count": len(shared_shortages),
        "allocations": summarized_allocations,
        "warehouse_scope": warehouse_scope if not isinstance(warehouse_scope, list) else "custom",
        "warehouse_filter": warehouses,
        "substitute_enabled": bool(substitute_enabled),
        "deduction_order": [d["product_code"] for d in normalized],
        "include_in_transit": True,
        "demand_mode": demand_mode,
    }
    if report_grain == "full":
        result["allocations"] = allocations
        result["remaining"] = remaining
    return result
