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
    product: str | None = None, demands: list | None = None,
    substitute_enabled: bool | None = None, warehouse_scope: str | None = None,
    need_by: str | None = None, chase_overdue_po: bool | None = None,
    reserve_signed_backlog: bool | None = None, use_finished_goods: bool | None = None,
    business_date: str | None = None,
) -> dict:
    """Run the fixed calculation with facts the Function reads itself."""
    params = {key: value for key, value in locals().items() if value is not None}
    rows = load_bkn_rows(_FIXED_OPERATION, bkn.query_object_instance, params)
    result = execute_from_bkn_rows(_FIXED_OPERATION, rows, params)
    result["data_source"] = {"knowledge_network_id": KN_ID,
                             "loaded_rows": {name: len(items) for name, items in rows.items()}}
    return result
'''


def _archive_source() -> str:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted((TOOLS / "fn").rglob("*.py")):
            archive.write(file_path, file_path.relative_to(TOOLS))
        archive.write(TOOLS / "managed_execution.py", "managed_execution.py")
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
    return bootstrap + "\n" + textwrap.dedent(ENTRY_SOURCE).lstrip()
