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
    "description": "Schedules a forecast (whole bill) or one product on a line, kit-checks the planned start and writes "
                   "a kit schedule plan without changing the forecast. An active plan for the same forecast and product is "
                   "updated; status Cancelled cancels it.",
    "use_rule": "Run only through the three kit schedule plan actions: create (new instance; object_input carries bill_no, "
                "product_code [empty string for the whole bill], line_code, planned_start, planned_finish, plan_status [usually Scheduled], "
                "source_scenario, planner), adjust (modify the selected plan: new line, start, finish, scenario, planner) and cancel "
                "(modify the selected plan: planner). Use Cypher on the kit schedule plan to look up scheduled plans and kit results.",
}
RULE_USE = ("Schedule Gantt rule tool, mounted (execute_tool in Q&A): tasks (key, start, resource, values: bill_no, "
            "product_code, line_code, planned_start, plan_status), at most 200; returns pass, severity, text, related. "
            "Kit_Check with mode=detail, task, query lists a plan's shortages.")
SCHEDULE_RULES = {
    "kit_check_rule": {
        "name": "Kit_Check",
        "description": "Checks whether plans are kitted at their planned start: backlog first, then confirmed and scheduled "
                       "plans in start order share stock and on-time purchases. Names the key shortage and its arrival; "
                       "mode=detail with one task returns its shortage table.",
        "use_rule": RULE_USE,
    },
    "line_check_rule": {
        "name": "Line_Can_Build",
        "description": "Checks that each plan's line can build its products: each product's product line must be one of the line's "
                       "product lines, every product of a whole bill included; a plant or unknown line fails. Failures are hard.",
        "use_rule": RULE_USE,
    },
}
KIT_PLAN_ACTIONS = {
    "create": ("Create Kit Schedule Plan", "add",
               "Schedule: create a kit schedule plan for a forecast (whole bill) or one of its products and record the kit check "
               "of the planned start. If the forecast + product already has an active plan, that plan is updated instead."),
    "adjust": ("Adjust Kit Schedule Plan", "modify",
               "Reschedule or move the selected plan to another line and kit-check it again; moving the finish adds a reschedule."),
    "cancel": ("Cancel Kit Schedule Plan", "modify", "Set the selected plan to Cancelled; the demand can be scheduled again."),
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
