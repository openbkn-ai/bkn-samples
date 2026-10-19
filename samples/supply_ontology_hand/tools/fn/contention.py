from __future__ import annotations

from collections import defaultdict

from .errors import CannotCompute
from .inventory import available_qty, in_transit_qty
from .kitting import kitting_net_demand
from .warehouse import resolve_warehouse_scope


def shared_contention(
    snap,
    demands: list[dict],
    *,
    warehouse_scope: str | list[str] | None = "production_available",
    substitute_enabled: bool | None = False,
    report_grain: str = "summary",
) -> dict:
    """Deduct shared available+in-transit in demand list order."""
    if not demands or len(demands) < 2:
        raise CannotCompute("共用料争用至少需要 2 条需求")
    if substitute_enabled is None:
        raise CannotCompute("未确认是否启用替代料，不能算争用")
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
        normalized.append({"product_code": product, "qty": float(qty)})

    warehouses = resolve_warehouse_scope(warehouse_scope)
    per_demand = []
    pool: dict[str, float] = defaultdict(float)
    seen_materials: dict[str, int] = defaultdict(int)
    for dem in normalized:
        kit = kitting_net_demand(
            snap,
            dem["product_code"],
            dem["qty"],
            warehouse_scope=warehouse_scope,
            substitute_enabled=substitute_enabled,
            report_grain="full",
        )
        per_demand.append(kit)
        for line in kit["lines"]:
            code = line["material_code"]
            seen_materials[code] += 1
            if code not in pool:
                pool[code] = available_qty(snap, code, warehouse_scope) + in_transit_qty(
                    snap, code
                )

    remaining = dict(pool)
    allocations = []
    for kit in per_demand:
        rows = []
        ok = True
        for line in kit["lines"]:
            code = line["material_code"]
            need = float(line["gross_requirement"])
            have = remaining.get(code, 0.0)
            take = min(have, need)
            remaining[code] = have - take
            short = max(0.0, need - take)
            if short > 0:
                ok = False
            rows.append(
                {
                    "material_code": code,
                    "gross_requirement": need,
                    "allocated": take,
                    "shortage": short,
                    "shared": seen_materials[code] > 1,
                }
            )
        allocations.append(
            {
                "product_code": kit["product_code"],
                "demand_qty": kit["demand_qty"],
                "satisfied": ok,
                "lines": rows,
            }
        )
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
    }
    if report_grain == "full":
        result["allocations"] = allocations
        result["remaining"] = remaining
    return result
