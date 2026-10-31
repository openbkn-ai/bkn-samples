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
        "Buildable_Quantity_and_ATP",
        "build_capacity",
        "Per product, nets the BOM level by level and returns finished goods, the most units current stock can build, "
        "signed backlog, available to promise and blocking materials. need_by adds purchases due by that date; "
        "chase_overdue_po adds overdue ones.",
        use_when="How many units of one or more products can be built or promised now, how much more can be accepted, "
                 "which material blocks them, or how many more units open purchase lines due by a date would allow. "
                 "Pass several products in one call instead of calling once per product.",
        do_not_use_when="Use Cypher for stock, backlog, forecasts, open purchase quantities or BOM lists.",
        minimum_business_inputs=["products"],
    ),
    "demand_coverage": _spec(
        "Demand_Coverage_and_Shortages",
        "demand_coverage",
        "Evaluates demands in order on one shared stock pool: finished goods first, then BOM netting. "
        "Returns coverage, units to build and bottom-level shortages. reserve_signed_backlog protects backlog first; "
        "use_finished_goods=false plans a work order.",
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
