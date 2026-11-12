"""Kit check for a scheduled demand: can production start on the planned date, and if not, when.

Uses the same netting as ``demand_coverage``: the products' signed backlog is reserved first
(due-date order), finished goods are not used (this is a production plan), and open purchase
lines due from the business date to the checked date count as supply. Overdue lines do not.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from decimal import Decimal
from typing import Any

from .planning import DEFAULT_BUSINESS_DATE, demand_coverage, is_open_po

KIT_COVERED = "Covered"
KIT_SHORT = "Short"


def _number(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral_value() else float(round(value, 6))


def day(value: Any) -> str:
    """Date part of a date or datetime value (``2027-03-01``, ``2027-03-01 08:00:00``, ISO with zone)."""
    text = str(value or "").strip()
    if len(text) < 10 or text[4] != "-" or text[7] != "-":
        raise ValueError(f"not a valid date: {value!r}")
    return text[:10]


def _arrivals(rows: Mapping[str, Iterable[Mapping[str, Any]]], business_date: str) -> list[str]:
    return sorted({str(r.get("deliverdate") or "")[:10] for r in rows.get("purchase_order", ())
                   if is_open_po(r) and str(r.get("deliverdate") or "")[:10] >= business_date})


def kit_check(rows: Mapping[str, Iterable[Mapping[str, Any]]], demands: list[Mapping[str, Any]], planned_start: Any, *,
              business_date: str = DEFAULT_BUSINESS_DATE, names: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Return kit status at the planned start, the kit date, and the key shortage if any.

    ``kit_date`` is the earliest date production could start with all materials in hand: on or before
    the planned start when the plan is covered, after it (the purchase arrival that closes the gap) when
    it is short, empty when open purchases never close the gap.
    """
    start = max(day(planned_start), business_date)
    rows = {key: list(value) for key, value in rows.items()}

    def cover(need_by: str) -> dict[str, Any]:
        return demand_coverage(rows, demands, need_by=need_by, reserve_signed_backlog=True,
                               use_finished_goods=False, business_date=business_date)

    at_start = cover(start)
    arrivals = _arrivals(rows, business_date)
    if at_start["all_covered"]:
        kit_date = next((d for d in [business_date, *[a for a in arrivals if a < start]] if cover(d)["all_covered"]), start)
        return {"kit_status": KIT_COVERED, "kit_date": kit_date, "key_material": "", "shortage_note": "",
                "shortages": {}, "reserved_backlog_orders": at_start["reserved_backlog_orders"]}
    shortages: dict[str, Decimal] = defaultdict(Decimal)
    for item in at_start["demands"]:
        for code, qty in item["shortages"].items():
            shortages[code] += Decimal(str(qty))
    kit_date = next((d for d in arrivals if d > start and cover(d)["all_covered"]), "")
    ranked = sorted(shortages.items(), key=lambda kv: (-kv[1], kv[0]))
    names = names or {}
    key = ranked[0][0]

    def label(code: str) -> str:
        return f"{code} {names[code]}" if names.get(code) else code

    listed = "; ".join(f"{label(code)} short {_number(qty)}" for code, qty in ranked[:3])
    more = f"{len(ranked)} materials in all"
    when = f"kitted on {kit_date} once open purchases arrive on schedule" if kit_date else "open purchases cannot close the gap; new orders are needed"
    return {"kit_status": KIT_SHORT, "kit_date": kit_date, "key_material": key,
            "shortage_note": f"Short at planned start {start}: {listed} ({more}); {when}.",
            "shortages": {code: _number(qty) for code, qty in ranked},
            "reserved_backlog_orders": at_start["reserved_backlog_orders"]}


__all__ = ["KIT_COVERED", "KIT_SHORT", "day", "kit_check"]
