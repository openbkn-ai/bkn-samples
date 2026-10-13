"""Single source of truth for Agent-facing supply calculation Tool guidance."""

from __future__ import annotations


def _spec(
    name: str,
    operation: str,
    description: str,
    *,
    use_when: str = 'Choose the function matching the business scenario.',
    do_not_use_when: str = 'Use only for this business scenario.',
    minimum_business_inputs: list[str] | None = None,
) -> dict[str, object]:
    return {
        "name": name,
        "operation": operation,
        "description": description,
        "use_when": use_when,
        "do_not_use_when": do_not_use_when,
        "minimum_business_inputs": minimum_business_inputs or [],
    }


FUNCTION_CATALOG = {
    "bom_list": _spec(
        'BOM_Structure',
        "bom_list",
        'Use case: BOM structure. Input: product, optional depth/alternates. Result: summary counts and first-level mains; full returns paged rows.',
        use_when='Use to inspect product structure, first-level main components or material counts.',
        do_not_use_when='Use a different function for where-used impact or multi-product allocation.',
        minimum_business_inputs=["product"],
    ),
    "bom_shared_list": _spec(
        'Shared_BOM',
        "bom_shared_list",
        'Use case: shared BOMs. Input: at least two products, optional depth/alternates. Result: shared component structure without stock or allocation analysis.',
    ),
    "layered_inventory": _spec(
        'BOM_Stock',
        "layered_inventory",
        'Use case: component stock. Input: product, optional depth/scope. Result: BOM levels, available stock and resolved scope; repeated positions share stock.',
    ),
    "substitute_status": _spec(
        'Alternate_Status',
        "substitute_status",
        'Use case: alternatives. Input: exactly one of product/material_code, optional scope/policy. Result: position-specific groups, candidates, usage and available stock.',
    ),
    "theoretical_build": _spec(
        'Manufacturing_Capacity',
        "theoretical_build",
        'Use case: stock-supported manufacturing. Input: product, explicit alternate policy, optional scope (all). Result: capacity and bottlenecks; excludes finished goods and incoming supply.',
    ),
    "total_sellable": _spec(
        'Total_Sellable',
        "total_sellable",
        'Use case: current sellable capacity. Input: product, explicit alternate policy, optional scopes (all). Result: finished stock, manufacturing capacity and total sellable; no incoming supply.',
        use_when='Use for current stock, sellable capacity or direct shipment coverage.',
        do_not_use_when='Do not substitute a structure-only backward plan for production scheduling, receipt dates or delay analysis.',
        minimum_business_inputs=["product", "substitute_enabled"],
    ),
    "kitting_net_demand": _spec(
        'Demand_Coverage',
        "kitting_net_demand",
        'Use case: fixed demand. Input: product, quantity, explicit alternate policy, optional scope (all). Result: coverage, all shortages and suggested replenishment; finished/component stock first, no POs.',
    ),
    "shared_contention": _spec(
        'Shared_Demand_Allocation',
        "shared_contention",
        'Use case: shared stock allocation. Input: ordered demands, explicit alternate policy, optional scope (all). Result: per-demand coverage and shortages; full adds allocations and remaining pool.',
        use_when='Use to assess simultaneous coverage for multiple products with explicit quantities.',
        do_not_use_when='For one product or structure-only comparison without quantities, choose another function.',
        minimum_business_inputs=["demands", "substitute_enabled"],
    ),
    "max_build_without_po": _spec(
        'Stock_Only_Capacity',
        "max_build_without_po",
        'Use case: no-purchase manufacturing. Input: product, explicit alternate policy, optional scope (all). Result: deterministic capacity and bottlenecks, excluding finished goods and incoming supply.',
    ),
    "leadtime_days": _spec(
        'Lead_Time',
        "leadtime_days",
        'Use case: standard lead time. Input: material_code. Result: leadtime_days, purchase/production caliber, material type, source field and unit; missing type keeps the marked production default.',
    ),
    "supply_status": _spec(
        'Supply_Status',
        "supply_status",
        'Use case: dated material coverage. Input: material, need date, gross quantity, business date, optional scope (all). Result: on-time coverage/shortage and stock/net PO evidence; excludes overdue, undated and closed POs.',
    ),
    "open_forecast_count": _spec(
        'Open_Forecast_Count',
        "open_forecast_count",
        'Use case: open forecast count. Input: optional product. Result: record count and exclusions; full adds IDs. Not forecast demand quantity.',
    ),
    "backward_plan": _spec(
        'Backward_Plan',
        "backward_plan",
        'Use case: deadline coverage. Input: forecast ID and alternate policy, or product/quantity/deadline/policy. Result: direct-stock or net production plan, customer/internal delays and evidence. Default business date: 2026-08-25.',
        use_when='Use when finished stock is insufficient or production timing, receipt risks or delays need analysis.',
        do_not_use_when='If finished stock covers customer demand, retain the direct-shipment result instead of applying manufacturing backward planning.',
        minimum_business_inputs=["product", "demand_qty", "demand_end", "substitute_enabled"],
    ),
    "material_where_used": _spec(
        'Where_Used',
        "material_where_used",
        'Use case: which products use a material. Input: material_code. Result: affected_product_count and products, including alternate branches by default; full adds BOM paths.',
        use_when='Use to find products affected by a material, identify common materials or assess shortage impact.',
        do_not_use_when='Do not use to inspect a single product BOM.',
        minimum_business_inputs=["material_code"],
    ),
}


def native_tool_description() -> str:
    """Return a concise description of the native Function collection."""
    operations = "；".join(
        f"{operation}（{spec['name']}）" for operation, spec in FUNCTION_CATALOG.items()
    )
    return (
        'Supply EN function catalog. Choose a named function by business question:'
        f"{operations}。"
        'Each function accepts only scenario-specific parameters and reads its bound knowledge network through sandbox_sdk.bkn at runtime.'
        'backward_plan defaults business_date to 2026-08-25.'
    )


def native_operation_description() -> str:
    return 'Available named functions:' + "、".join(FUNCTION_CATALOG)


__all__ = ["FUNCTION_CATALOG", "native_operation_description", "native_tool_description"]
