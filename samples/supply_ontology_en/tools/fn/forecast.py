"""Count open (not closed) forecast documents from inline rows."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

CLOSED_STATUS = 'Closed'


def open_forecast_count(
    forecast_rows: Iterable[Mapping[str, Any]] | None,
    *,
    product_code: str | None = None,
    report_grain: str = "summary",
) -> dict[str, Any]:
    if report_grain not in {"summary", "full"}:
        raise ValueError(f"""report_grain must be summary or full: {report_grain}""")
    rows = [dict(row) for row in (forecast_rows or [])]
    product = (product_code or "").strip() or None
    open_ids: list[str] = []
    excluded_closed = 0
    for row in rows:
        code = str(row.get("material_number") or "").strip()
        if product and code != product:
            continue
        if str(row.get("closestatus_title") or "").strip() == CLOSED_STATUS:
            excluded_closed += 1
            continue
        open_ids.append(str(row.get("id") or row.get("forecast_id") or "").strip())
    result = {
        "open_count": len(open_ids),
        "excluded_closed_count": excluded_closed,
        "input_row_count": len(rows),
        "product_code": product,
        "report_grain": report_grain,
        "exclusion": {
            "field": "closestatus_title",
            "operation": "!=",
            "value": CLOSED_STATUS,
        },
    }
    if report_grain == "full":
        result["open_forecast_ids"] = open_ids
    return result
