"""Build the self-contained OpenBKN native Function payload.

The Foundry Function Runtime executes an ``@tool`` entrypoint in an isolated
sandbox.  This builder packages the existing pure calculation modules and lets
the official ``sandbox_sdk.bkn`` acquire required BKN facts internally.
"""

from __future__ import annotations

import base64
import io
import textwrap
import zipfile
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
PACKAGE_PATHS = (TOOLS / "fn", TOOLS / "context")


ENTRY_SOURCE = r'''
from sandbox_sdk import bkn, tool
from managed_execution import KN_ID, execute_from_bkn_rows, load_bkn_rows

@tool
def supply_function(
    product: str | None = None, products: list | None = None,
    depth: int | None = None, include_substitute: bool | None = None,
    warehouse_scope: str | None = None, substitute_enabled: bool | None = None,
    production_scope: str | None = None, finished_goods_scope: str | None = None,
    qty: float | None = None, demands: list | None = None,
    material_code: str | None = None, due_date: str | None = None,
    gross_requirement: float | None = None, child_short: bool | None = None,
    product_code: str | None = None, forecast_id: str | None = None,
    demand_end: str | None = None, demand_qty: float | None = None,
    business_date: str | None = None, report_grain: str | None = None,
    page_size: int | None = None, offset: int | None = None,
) -> dict:
    """Run the fixed operation with facts loaded by the Function itself."""
    params = {key: value for key, value in locals().items() if value is not None}
    rows = load_bkn_rows(_FIXED_OPERATION, bkn.query_object_instance, params)
    result = execute_from_bkn_rows(_FIXED_OPERATION, rows, params)
    result["data_source"] = {
        "knowledge_network_id": KN_ID,
        "loaded_datasets": list(rows),
    }
    return result
'''


def _archive_source() -> str:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for package in PACKAGE_PATHS:
            for file_path in sorted(package.rglob("*.py")):
                archive.write(file_path, file_path.relative_to(TOOLS))
        archive.write(TOOLS / "managed_execution.py", "managed_execution.py")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def build_native_function_code(*, fixed_operation: str | None = None) -> str:
    """Return Foundry-compatible Function code, optionally fixed to one operation."""
    encoded = _archive_source()
    fixed = repr(fixed_operation)
    bootstrap = textwrap.dedent(
        f'''\
        import base64
        import io
        import sys
        import tempfile
        import zipfile

        _SUPPLY_SOURCE = {encoded!r}
        _FIXED_OPERATION = {fixed}
        root = tempfile.mkdtemp(prefix="supply_native_function_")
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(_SUPPLY_SOURCE))) as archive:
            archive.extractall(root)
        sys.path.insert(0, root)
        '''
    )
    return bootstrap + "\n" + textwrap.dedent(ENTRY_SOURCE).lstrip()
