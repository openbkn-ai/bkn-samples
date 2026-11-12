"""Build the self-contained code of each machine-scheduling Function.

The Function Runtime runs an ``@tool`` entry point in a sandbox. Each Function carries the rule
module and the runtime as a zip, fixed to one operation, the network and its language.
"""

from __future__ import annotations

import base64
import io
import json
import textwrap
import zipfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
MODULES = ("machine_schedule.py", "schedule_runtime.py")
SCHEDULED = ("manufacturing_operations", "maintenance_work_orders")

RULE_ENTRY = r'''
from sandbox_sdk import bkn, tool
import bkn_osdk
import schedule_runtime


@tool
def schedule_rule(tasks: list | None = None, scenario: dict | None = None, mode: str | None = None,
                  task: dict | None = None, locale: str | None = None, query: dict | None = None) -> dict:
    """Check schedule tasks (operations) against one rule; mode "detail" returns one task's paged table."""
    return schedule_runtime.rule(_OPERATION, bkn.query_object_instance, call=bkn_osdk.call, tasks=tasks, scenario=scenario, mode=mode,
                                 task=task, locale=locale, detail_query=query)
'''

OPERATION_ENTRY = r'''
from sandbox_sdk import bkn, tool
import bkn_osdk
import schedule_runtime


@tool
def adjust_operation_schedule(operation_id: str | None = None, planned_machine_id: str | None = None,
                              planned_start_date: str | None = None, planned_end_date: str | None = None) -> dict:
    """Move one operation to a machine of its work centre and new planned days."""
    params = {k: v for k, v in locals().items() if v not in (None, "")}
    return schedule_runtime.adjust_operation(bkn.query_object_instance, bkn_osdk.call, params)
'''

MAINTENANCE_ENTRY = r'''
from sandbox_sdk import bkn, tool
import bkn_osdk
import schedule_runtime


@tool
def adjust_maintenance_work_order(maintenance_work_order_id: str | None = None, planned_start_date: str | None = None,
                                  planned_end_date: str | None = None) -> dict:
    """Move one maintenance work order's planned days; its due day stays."""
    params = {k: v for k, v in locals().items() if v not in (None, "")}
    return schedule_runtime.adjust_maintenance(bkn.query_object_instance, bkn_osdk.call, params)
'''

ENTRIES = {"adjust_operation_schedule": OPERATION_ENTRY, "adjust_maintenance_work_order": MAINTENANCE_ENTRY}


def _archive() -> str:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in MODULES:
            info = zipfile.ZipInfo(name, date_time=(2027, 2, 28, 0, 0, 0))  # stable bytes, stable digest
            archive.writestr(info, (TOOLS / name).read_bytes())
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def settings() -> dict:
    contract = json.loads((ROOT / "model-contract.json").read_text(encoding="utf-8"))
    language = "zh" if contract.get("language") == "zh-cn" else "en"
    fields = {t: contract["object_types"][t]["fields"] for t in SCHEDULED}
    return {"language": language, "fields": fields}


def build(operation: str, kn_id: str) -> str:
    """The Function code for one operation: a rule tool (``*_rule``) or one of the two adjust functions."""
    entry = RULE_ENTRY if operation.endswith("_rule") else ENTRIES[operation]
    s = settings()
    bootstrap = textwrap.dedent(f'''\
        import base64
        import io
        import sys
        import tempfile
        import zipfile

        _SOURCE = {_archive()!r}
        _OPERATION = {operation.removesuffix("_rule")!r}
        _root = tempfile.mkdtemp(prefix="mfg_schedule_")
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(_SOURCE))) as _archive:
            _archive.extractall(_root)
        sys.path.insert(0, _root)
        import schedule_runtime as _runtime
        _runtime.KN_ID = {kn_id!r}
        _runtime.LANGUAGE = {s["language"]!r}
        _runtime.FIELDS = {s["fields"]!r}
        ''')
    return bootstrap + "\n" + textwrap.dedent(entry).lstrip()


__all__ = ["build", "settings"]
