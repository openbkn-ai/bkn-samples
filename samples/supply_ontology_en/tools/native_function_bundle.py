"""Build the self-contained OpenBKN native Function payload.

The Foundry Function Runtime executes an ``@tool`` entrypoint in an isolated
sandbox. This builder packages the planning calculations and lets the official
``sandbox_sdk.bkn`` read the facts each call needs.
"""

from __future__ import annotations

import base64
import io
import textwrap
import zipfile
from pathlib import Path


TOOLS = Path(__file__).resolve().parent


ENTRY_SOURCE = r'''
from sandbox_sdk import bkn, tool
from managed_execution import KN_ID, execute_from_bkn_rows, load_bkn_rows

@tool
def supply_function(
    products: list | None = None, demands: list | None = None,
    substitute_enabled: bool | None = None, warehouse_scope: str | None = None,
    need_by: str | None = None, chase_overdue_po: bool | None = None,
    reserve_signed_backlog: bool | None = None, use_finished_goods: bool | None = None,
    business_date: str | None = None,
) -> dict:
    """Run the fixed calculation with facts the Function reads itself."""
    # An action sends every declared input; an empty string means "not set" (e.g. no need_by).
    params = {key: value for key, value in locals().items() if value is not None and value != ""}
    rows = load_bkn_rows(_FIXED_OPERATION, bkn.query_object_instance, params)
    result = execute_from_bkn_rows(_FIXED_OPERATION, rows, params)
    result["data_source"] = {"knowledge_network_id": KN_ID,
                             "loaded_rows": {name: len(items) for name, items in rows.items()}}
    return result
'''

KIT_ENTRY_SOURCE = r'''
from sandbox_sdk import bkn, tool
import bkn_osdk
from kit_schedule import OT_PLAN, schedule
from managed_execution import KN_ID

@tool
def kit_schedule(
    bill_no: str | None = None, product_code: str | None = None, line_code: str | None = None,
    planned_start: str | None = None, planned_finish: str | None = None, plan_status: str | None = None,
    source_scenario: str | None = None, planner: str | None = None, plan_id: str | None = None,
) -> dict:
    """Create, reschedule or cancel one kit-schedule plan and record its kit check."""
    params = {key: value for key, value in locals().items() if value is not None}
    definition = bkn_osdk.call(f"/api/bkn-backend/v1/knowledge-networks/{KN_ID}/object-types/{OT_PLAN}")
    entries = definition.get("entries") if isinstance(definition, dict) else None
    resource = ((entries[0] if entries else definition) or {}).get("data_source", {}).get("id")
    if not resource:
        raise ValueError("kit-schedule plan object has no dataset")

    def write(plan_id: str, row: dict):
        return bkn_osdk.call(f"/api/vega-backend/v1/resources/{resource}/data/{plan_id}", method="PUT", body=row)

    return schedule(params, bkn.query_object_instance, write)
'''


RULE_ENTRY_SOURCE = r'''
from sandbox_sdk import bkn, tool
import bkn_osdk
import schedule_rules

@tool
def schedule_rule(tasks: list | None = None, scenario: dict | None = None, mode: str | None = None,
                  task: dict | None = None, locale: str | None = None, query: dict | None = None) -> dict:
    """Check schedule-Gantt tasks (kit-schedule plans), or with mode "detail" explain one task as a table."""
    # The tasks already carry the scenario's changes; the edits only say which ones moved.
    # The SDK reader only inside a conversation: touching it elsewhere leaves a directory in the shared workspace.
    read = schedule_rules.tool_query(bkn.query_object_instance if schedule_rules.in_conversation(bkn) else None,
                                     bkn_osdk.call)
    if _FIXED_OPERATION == "kit_check_rule" and mode == "detail":
        return schedule_rules.kit_check_detail(task, read, scenario=scenario, locale=locale, page=query)
    if _FIXED_OPERATION == "kit_check_rule":
        return schedule_rules.kit_check(tasks, read, scenario=scenario, locale=locale)
    return schedule_rules.line_check(tasks, read)
'''


def _archive_source() -> str:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted((TOOLS / "fn").rglob("*.py")):
            archive.write(file_path, file_path.relative_to(TOOLS))
        archive.write(TOOLS / "managed_execution.py", "managed_execution.py")
        archive.write(TOOLS / "kit_schedule.py", "kit_schedule.py")
        archive.write(TOOLS / "schedule_rules.py", "schedule_rules.py")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def build_native_function_code(*, fixed_operation: str) -> str:
    """Return Foundry-compatible Function code fixed to one operation."""
    bootstrap = textwrap.dedent(
        f'''\
        import base64
        import io
        import sys
        import tempfile
        import zipfile

        _SUPPLY_SOURCE = {_archive_source()!r}
        _FIXED_OPERATION = {fixed_operation!r}
        root = tempfile.mkdtemp(prefix="supply_native_function_")
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(_SUPPLY_SOURCE))) as archive:
            archive.extractall(root)
        sys.path.insert(0, root)
        '''
    )
    entry = (KIT_ENTRY_SOURCE if fixed_operation == "kit_schedule"
             else RULE_ENTRY_SOURCE if fixed_operation.endswith("_rule") else ENTRY_SOURCE)
    return bootstrap + "\n" + textwrap.dedent(entry).lstrip()
