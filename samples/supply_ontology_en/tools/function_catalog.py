"""Single source of truth for Agent-facing supply calculation Tool guidance."""

from __future__ import annotations

EXECUTION_USE_RULE = (
    'Call through execute_tool, copying toolbox_id=owner_id and tool_id=capability_id exactly from discovery. '
    'Pass the business assumptions (substitutes, warehouse scope, need-by date, overdue purchases) explicitly. '
    'Check body.exit_code and result: HTTP 200 alone is not success. Use Cypher for lookups, totals and relations.'
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


KIT_SCHEDULE = {
    "name": "Kit_Schedule",
    "operation": "kit_schedule",
    "description": "Schedules a forecast (whole bill) or one product on a line, checks materials for the planned start and "
                   "records it in a kit schedule plan without changing the forecast. Scheduling the same bill and product "
                   "again updates its plan.",
    # Agents reach it only through the three plan actions; their inputs are described on each parameter.
    "use_rule": "Used by the create, adjust and cancel kit schedule plan actions, not on its own; look up scheduled plans "
                "and kit results with a knowledge network query.",
}
# Calling details (tasks, detail mode, paging) are on the tool parameters; this text is shown to business users.
RULE_USE = "Used by the schedule Gantt to check plans, and in Q&A to check scheduled plans; at most 200 plans per check."
SCHEDULE_RULES = {
    "kit_check_rule": {
        "name": "Kit_Check",
        "description": "Checks materials at each plan's start: backlog first, then confirmed and scheduled plans in start "
                       "order share stock and on-time purchases. Names the key shortage and its arrival; a plan starting too "
                       "early cannot be adopted.",
        "use_rule": RULE_USE,
    },
    "line_check_rule": {
        "name": "Line_Can_Build",
        "description": "Checks that a plan's line can build its products: each product's product line must be one of the "
                       "line's product lines, every product of a whole bill included. A plant or unknown line fails, and "
                       "such a plan cannot be adopted.",
        "use_rule": RULE_USE,
    },
}
KIT_PLAN_ACTIONS = {
    "create": ("Create Kit Schedule Plan", "add",
               "Creates a kit schedule plan for a demand forecast (whole bill) or one of its products and records the "
               "kit result for its planned start. If that bill and product already have an active plan, it is updated instead."),
    "adjust": ("Adjust Kit Schedule Plan", "modify",
               "Moves the selected plan to another line, start or finish and checks its materials again; a new finish "
               "counts as a reschedule."),
    "cancel": ("Cancel Kit Schedule Plan", "modify", "Cancels the selected plan; the bill can then be scheduled again."),
}


def native_tool_description() -> str:
    """Return a concise description of the native Function collection."""
    operations = "；".join(f"{operation}（{spec['name']}）" for operation, spec in FUNCTION_CATALOG.items())
    return (
        f"Supply planning functions: {operations}. "
        "They read the bound knowledge network through sandbox_sdk.bkn at run time; business_date defaults to 2027-02-25."
    )


def native_operation_description() -> str:
    return "Named functions: " + ", ".join(FUNCTION_CATALOG)


__all__ = ["FUNCTION_CATALOG", "KIT_PLAN_ACTIONS", "KIT_SCHEDULE", "SCHEDULE_RULES", "native_operation_description", "native_tool_description"]
