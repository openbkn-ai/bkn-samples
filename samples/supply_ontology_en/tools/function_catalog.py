"""Single source of truth for Agent-facing supply calculation Tool guidance."""

from __future__ import annotations

EXECUTION_USE_RULE = (
    'Call through execute_tool, copying toolbox_id=owner_id and tool_id=capability_id exactly from discovery. '
    'Check body.exit_code and result: HTTP 200 alone does not mean the calculation succeeded. '
    'Use Cypher, not a function, for lookups, totals and following relations.'
)


def _spec(name: str, operation: str, description: str, *, use_when: str, do_not_use_when: str,
          minimum_business_inputs: list[str]) -> dict[str, object]:
    return {
        "name": name,
        "operation": operation,
        "description": description,
        "use_rule": EXECUTION_USE_RULE,
        "use_when": use_when,
        "do_not_use_when": do_not_use_when,
        "minimum_business_inputs": minimum_business_inputs,
    }


FUNCTION_CATALOG = {
    "build_capacity": _spec(
        "Buildable quantity and available to promise",
        "build_capacity",
        "Nets the BOM level by level and returns, for each product on its own: finished-goods stock, the most units "
        "current stock can still build, signed backlog, available to promise (finished goods + buildable − backlog) "
        "and the materials that block one more unit. Defaults: current Available stock, all warehouses, no alternates. "
        "need_by adds open purchase lines due by that date; chase_overdue_po=true adds overdue open lines.",
        use_when="How many units of one or more products can be built or promised now, how much more can be accepted, "
                 "which material blocks them, or how many more units open purchase lines due by a date would allow. "
                 "Pass several products in one call instead of calling once per product.",
        do_not_use_when="Use Cypher for stock, backlog, forecasts, open purchase quantities or BOM lists.",
        minimum_business_inputs=["products"],
    ),
    "demand_coverage": _spec(
        "Demand coverage and shortages",
        "demand_coverage",
        "Evaluates demands in array order against one shared stock pool: finished goods first, then BOM netting level "
        "by level. Returns whether each demand is covered, the units to manufacture and the bottom-level shortages. "
        "reserve_signed_backlog=true first reserves these products' signed backlog by promised date; "
        "use_finished_goods=false plans a work order without finished goods. In-transit and alternate options match the buildable-quantity function.",
        use_when="Whether one or more demands (new orders, backlog, planned work orders) are covered, what is short and by how much, or how competing orders share stock.",
        do_not_use_when="Use the buildable-quantity function when only the maximum buildable quantity is asked.",
        minimum_business_inputs=["demands"],
    ),
}


def native_tool_description() -> str:
    """Return a concise description of the native Function collection."""
    operations = "；".join(f"{operation}（{spec['name']}）" for operation, spec in FUNCTION_CATALOG.items())
    return (
        f"Supply planning functions: {operations}. "
        "They read the bound knowledge network through sandbox_sdk.bkn at run time; business_date defaults to 2026-08-25."
    )


def native_operation_description() -> str:
    return "Named functions: " + ", ".join(FUNCTION_CATALOG)


__all__ = ["FUNCTION_CATALOG", "native_operation_description", "native_tool_description"]
