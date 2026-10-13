'S1 backward planning pure function. Business rules: skills/production-schedule-backward-planning/references/business-rules.md. Accepts a request-level Snapshot only, without remote queries or runtime CSV. Reuses existing date, supply-status and incoming-supply functions.'

from __future__ import annotations

from datetime import date, datetime, timedelta

from .bom import children_by_parent, product_bom_rows
from .errors import CannotCompute
from .inventory import (
    available_qty,
    has_mrp,
    in_transit_qty,
    po_open_rows,
    pr_open_qty,
)
from .leadtime import leadtime_days
from .snapshot import Snapshot, _f
from .supply_status import supply_status
from .warehouse import resolve_warehouse_scope

MAX_NODES = 5000
DEFAULT_BUSINESS_DATE = "2026-08-25"
REPORT_GRAINS = ("summary", "full_tree")
PURCHASED_ATTRS = ('Purchased', 'Subcontracted')
SUPPLY_STATUSES = (
    "sufficient",
    "anomaly",
    "deadline_risk",
    "po_overdue",
    "no_pr",
    "no_po",
    "po_in_transit",
    "child_short",
    "unscheduled",
    "plan_gap",
    "unknown",
)
RISK_STATUSES = frozenset(
    {"anomaly", "deadline_risk", "po_overdue", "no_pr", "no_po", "child_short"}
)
_PATH_EXIT = object()


def _parse_day(value, label: str) -> date:
    text = str(value if value is not None else "").strip()
    if not text:
        raise CannotCompute(f"""Missing {label}""")
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except ValueError:
        raise CannotCompute(f"""Invalid {label} date (YYYY-MM-DD): {text}""") from None


def _po_deliver_dates(rows: list[dict]) -> list[date]:
    days = []
    for row in rows:
        text = str(row.get("deliverdate") or "").strip()
        if not text:
            continue
        try:
            days.append(datetime.strptime(text[:10], "%Y-%m-%d").date())
        except ValueError:
            continue
    return days


def _validated_request(
    snap: Snapshot,
    product: str | None,
    forecast_id: str | None,
    demand_end: str | None,
    demand_qty,
    substitute_enabled,
    report_grain: str,
) -> tuple[str, str | None, date, float]:
    code = (product or "").strip()
    plan_id = str(forecast_id or "").strip()
    if not isinstance(substitute_enabled, bool):
        raise CannotCompute('substitute_enabled must explicitly be True or False')
    if report_grain not in REPORT_GRAINS:
        raise CannotCompute(f"""report_grain must be {REPORT_GRAINS}: {report_grain}""")
    if plan_id:
        row = _find_forecast(snap, plan_id)
        if not row:
            raise CannotCompute(f"""Forecast not found: {plan_id}""")
        forecast_product = str(row.get("material_number") or "").strip()
        forecast_due = _parse_day(row.get("enddate"), f"""Forecast {plan_id} need date""")
        forecast_qty = _f(row.get("qty"), 0.0)
        if code and forecast_product != code:
            raise CannotCompute(
                f"""Forecast {plan_id} product {forecast_product} differs from requested {code}"""
            )
        if demand_end and _parse_day(demand_end, 'Need Date') != forecast_due:
            raise CannotCompute(f"""Forecast {plan_id} need date differs from requested {demand_end}""")
        if demand_qty is not None and _f(row.get("qty"), 0.0) != float(demand_qty):
            raise CannotCompute(f"""Forecast {plan_id} quantity differs from requested {demand_qty}""")
        return forecast_product, plan_id, forecast_due, forecast_qty

    if not code:
        raise CannotCompute('New demand has no product code')
    due = _parse_day(demand_end, 'Need Date')
    try:
        qty = float(demand_qty)
    except (TypeError, ValueError):
        raise CannotCompute(f"""Demand is not numeric: {demand_qty}""") from None
    if qty <= 0:
        raise CannotCompute(f"""Demand must be positive: {demand_qty}""")
    return code, plan_id or None, due, qty


def _find_forecast(snap: Snapshot, requested_id: str) -> dict | None:
    """Find a forecast while tolerating numeric resource keys losing CSV leading zeroes."""
    direct = snap.forecast_by_id.get(requested_id)
    if direct is not None or not requested_id.isdigit():
        return direct
    canonical = str(int(requested_id))
    return snap.forecast_by_id.get(canonical)


def _walk(
    snap: Snapshot,
    product: str,
    *,
    demand_qty: float,
    demand_end: date,
    warehouse_scope,
    warnings: list[str],
) -> list[dict]:
    'Main-component backward tree in preorder; skip cycles with a warning and reject more than MAX_NODES nodes.'
    tree = children_by_parent(snap, product, include_substitute=False)
    nodes: list[dict] = []
    # Expand in preorder without recursion; release path entries when leaving each node.
    on_path: set[str] = set()
    # (material, parent material, level, cumulative usage, required date, parent index)
    stack: list[tuple] = [(product, "", 0, 1.0, demand_end, None)]
    while stack:
        entry = stack.pop()
        if entry[0] is _PATH_EXIT:
            on_path.discard(entry[1])
            continue
        code, parent, level, usage, end, parent_index = entry
        lead_time = leadtime_days(snap, code)
        available = available_qty(snap, code, warehouse_scope)
        in_transit = in_transit_qty(snap, code)
        mrp = has_mrp(snap, code)
        satisfied = not mrp and (available + in_transit) > 0
        gantt_days = 1 if satisfied else max(lead_time, 1)
        # Schedule the root by standard lead time and children by their Gantt duration.
        start = end - timedelta(days=lead_time if level == 0 else gantt_days)
        gross = demand_qty * usage
        nodes.append(
            {
                "material_code": code,
                "parent_material_code": parent,
                "bom_level": level,
                "usage_per_unit": usage,
                "gross_requirement": gross,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "lead_time_days": lead_time,
                "available_qty": available,
                "in_transit_qty": in_transit,
                "supply_status": "",
                "delay_class": "",
                "delay_days": 0,
                "evidence": {},
                "_start": start,
                "_end": end,
                "_gantt_days": gantt_days,
                "_has_mrp": mrp,
                "_parent_index": parent_index,
            }
        )
        if len(nodes) > MAX_NODES:
            raise CannotCompute(f"""Backward tree exceeds {MAX_NODES} nodes; narrow the scope and recalculate""")
        index = len(nodes) - 1
        on_path.add(code)
        children = []
        # Stop expanding a component when its available supply covers the node demand.
        # This net-demand boundary prevents false shortages below covered components.
        if available + in_transit >= gross:
            stack.append((_PATH_EXIT, code))
            continue
        for row in tree.get(code, []):
            child = (row.get("material_code") or "").strip()
            if not child:
                continue
            if child in on_path:
                warnings.append(f"""Skipping BOM cycle: {code} → {child}""")
                continue
            children.append(
                (
                    child,
                    code,
                    level + 1,
                    usage * _f(row.get("standard_usage"), 1.0),
                    start - timedelta(days=1),
                    index,
                )
            )
        stack.append((_PATH_EXIT, code))
        stack.extend(reversed(children))
    return nodes


def _mark_child_shortage(nodes: list[dict]) -> list[bool]:
    'Preorder places children after parents, enabling one reverse pass to aggregate shortages bottom-up.'
    short_below = [False] * len(nodes)
    for index in range(len(nodes) - 1, -1, -1):
        item = nodes[index]
        parent_index = item["_parent_index"]
        if parent_index is None:
            continue
        supply = item["available_qty"] + item["in_transit_qty"]
        if short_below[index] or supply < item["gross_requirement"]:
            short_below[parent_index] = True
    return short_below


def _classify_delay(
    item: dict,
    *,
    today: date,
    material_attr: str,
    po_rows: list[dict],
) -> tuple[str, int, date | None]:
    latest_po = max(_po_deliver_dates(po_rows), default=None)
    if item["bom_level"] == 0:
        return "", 0, latest_po
    if (
        material_attr in PURCHASED_ATTRS
        and not po_rows
        and item["_start"] < today
        and item["available_qty"] < item["gross_requirement"]
    ):
        arrival = today + timedelta(days=item["lead_time_days"])
        delay = max(0, (arrival - item["_end"]).days)
        if delay > 0:
            return "A", delay, latest_po
    if latest_po and latest_po > item["_end"]:
        return "B", (latest_po - item["_end"]).days, latest_po
    return "", 0, latest_po


def _keep_largest(bucket: dict[str, dict], entry: dict) -> None:
    current = bucket.get(entry["material_code"])
    if current is None or entry["delay_days"] > current["delay_days"]:
        bucket[entry["material_code"]] = entry


def _sorted_delays(bucket: dict[str, dict]) -> list[dict]:
    return sorted(
        bucket.values(), key=lambda row: (-row["delay_days"], row["material_code"])
    )


def backward_plan(
    snap: Snapshot,
    product: str | None = None,
    *,
    forecast_id: str | None = None,
    demand_end: str | None = None,
    demand_qty=None,
    business_date: str | None = None,
    warehouse_scope: str | list[str] | None = "all",
    substitute_enabled: bool,
    report_grain: str = "summary",
) -> dict:
    "Build one product's main-component backward plan from one forecast. MAX_NODES is fixed and not exposed as a request parameter. Explicit alternate policy is echoed without changing the main-component tree."
    code, plan_id, due, qty = _validated_request(
        snap,
        product,
        forecast_id,
        demand_end,
        demand_qty,
        substitute_enabled,
        report_grain,
    )
    if not product_bom_rows(snap, code):
        raise CannotCompute(f"""No BOM: {code}""")
    effective_business_date = (
        DEFAULT_BUSINESS_DATE if business_date is None else business_date
    )
    today = _parse_day(effective_business_date, 'Business Date')
    warehouse_filter = resolve_warehouse_scope(warehouse_scope)
    finished_goods_filter = warehouse_filter
    finished_goods_qty = available_qty(snap, code, warehouse_scope)

    # This function is used for a customer delivery commitment as well as a
    # production-plan diagnosis.  A finished-goods shipment must never be
    # rejected merely because a hypothetical new manufacturing run is late.
    if finished_goods_qty >= qty:
        return {
            "product_code": code,
            "forecast_id": plan_id,
            "demand_qty": qty,
            "demand_end": due.isoformat(),
            "business_date": today.isoformat(),
            "today": today.isoformat(),
            "warehouse_scope": warehouse_scope if isinstance(warehouse_scope, str) else "custom",
            "warehouse_filter": warehouse_filter,
            "finished_goods_filter": finished_goods_filter,
            "finished_goods_qty": finished_goods_qty,
            "remaining_finished_goods_qty": finished_goods_qty - qty,
            "fulfillment_mode": "finished_goods",
            "production_plan_required": False,
            "customer_earliest_available_date": today.isoformat(),
            "customer_late_days": max(0, (today - due).days),
            "substitute_enabled": substitute_enabled,
            "report_grain": report_grain,
            "can_deliver_on_time": today <= due,
            "delivery_commitment_status": "confirmed_on_time" if today <= due else "confirmed_late",
            "uncertain_supply_items": [],
            "max_delay_days": max(0, (today - due).days),
            "delay_a": [],
            "delay_b": [],
            "nodes": [],
            "node_count_total": 0,
            "gaps": [],
            "supply_status_summary": {status: 0 for status in SUPPLY_STATUSES},
            "warnings": ['Finished stock covers demand; manufacturing backward planning was not started.'],
        }

    warnings: list[str] = []
    if substitute_enabled:
        warnings.append('Alternates enabled: the tree still uses main BOM rows; alternates support later assessment only')
    production_qty = max(0.0, qty - finished_goods_qty)
    nodes = _walk(
        snap,
        code,
        demand_qty=production_qty,
        demand_end=due,
        warehouse_scope=warehouse_scope,
        warnings=warnings,
    )

    short_below = _mark_child_shortage(nodes)
    summary = {status: 0 for status in SUPPLY_STATUSES}
    delay_a: dict[str, dict] = {}
    delay_b: dict[str, dict] = {}
    gaps: list[dict] = []
    for index, item in enumerate(nodes):
        material_row = snap.materials.get(item["material_code"]) or {}
        material_attr = (material_row.get("materialattr") or "").strip()
        po_rows = po_open_rows(snap, item["material_code"])
        open_pr = pr_open_qty(snap, item["material_code"])
        supply = item["available_qty"] + item["in_transit_qty"]
        shortage = max(0.0, item["gross_requirement"] - supply)
        status_result = supply_status(
            snap,
            item["material_code"],
            due_date=item["_end"],
            gross_requirement=item["gross_requirement"],
            warehouse_scope=warehouse_scope,
            today=today,
            child_short=short_below[index],
        )
        status = status_result["status"]
        delay_class, delay_days, latest_po = _classify_delay(
            item,
            today=today,
            material_attr=material_attr,
            po_rows=po_rows,
        )
        item["supply_status"] = status
        item["delay_class"] = delay_class
        item["delay_days"] = delay_days
        item["evidence"] = {
            "material_attr": material_attr,
            "usage_per_unit": item["usage_per_unit"],
            "gross_requirement": item["gross_requirement"],
            "available_qty": item["available_qty"],
            "in_transit_qty": item["in_transit_qty"],
            "supply_qty": supply,
            "shortage_qty": shortage,
            "open_pr_qty": open_pr,
            "open_po_count": len(po_rows),
            "latest_po_deliver_date": latest_po.isoformat() if latest_po else "",
            "has_open_mrp": item["_has_mrp"],
            "lead_time_days": item["lead_time_days"],
            "gantt_days": item["_gantt_days"],
            "child_short": short_below[index],
        }
        summary[status] = summary.get(status, 0) + 1
        if shortage > 0:
            gaps.append(
                {
                    "material_code": item["material_code"],
                    "parent_material_code": item["parent_material_code"],
                    "bom_level": item["bom_level"],
                    "end_date": item["end_date"],
                    "gross_requirement": item["gross_requirement"],
                    "available_qty": item["available_qty"],
                    "in_transit_qty": item["in_transit_qty"],
                    "shortage_qty": shortage,
                    "supply_status": status,
                }
            )
        if delay_class:
            entry = {
                "material_code": item["material_code"],
                "parent_material_code": item["parent_material_code"],
                "bom_level": item["bom_level"],
                "delay_class": delay_class,
                "delay_days": delay_days,
                "end_date": item["end_date"],
                "start_date": item["start_date"],
                "lead_time_days": item["lead_time_days"],
                "supply_status": status,
                "evidence": dict(item["evidence"]),
            }
            _keep_largest(delay_a if delay_class == "A" else delay_b, entry)

    for item in nodes:
        for key in ("_start", "_end", "_gantt_days", "_has_mrp", "_parent_index"):
            item.pop(key)

    max_delay_days = max(
        [row["delay_days"] for row in (*delay_a.values(), *delay_b.values())],
        default=0,
    )
    customer_readiness = []
    for gap in gaps:
        material_code = gap["material_code"]
        open_po_dates = [day for day in _po_deliver_dates(po_open_rows(snap, material_code)) if day >= today]
        if open_po_dates:
            customer_readiness.append(min(open_po_dates))
        else:
            customer_readiness.append(
                today + timedelta(days=leadtime_days(snap, material_code))
            )
    customer_earliest = max(customer_readiness, default=today)
    customer_late_days = max(0, (customer_earliest - due).days)
    if report_grain == "full_tree":
        reported = list(nodes)
    else:
        reported = [
            item
            for item in nodes
            if item["bom_level"] == 0
            or item["delay_class"]
            or item["supply_status"] in RISK_STATUSES
            or item["evidence"]["shortage_qty"] > 0
        ]
    # Unknown receipts are uncertainty; an established missed date is a
    # negative result, not an unknown result.
    blocking_statuses = {"unknown", "po_overdue", "child_short"}
    uncertain_items = [
        item["material_code"] for item in nodes
        if item.get("supply_status") in blocking_statuses
    ]
    warnings_out = list(warnings)
    if uncertain_items:
        warnings_out.append(
            'Unknown supply, overdue receipts or critical component shortages prevent a definite delivery commitment:'
            + ",".join(uncertain_items)
        )
    known_late = (due < today or max_delay_days > 0 or customer_late_days > 0
                  or any(item.get("supply_status") == "deadline_risk" for item in nodes))
    can_deliver = False if known_late else (None if uncertain_items else True)
    return {
        "product_code": code,
        "forecast_id": plan_id,
        "demand_qty": qty,
        "demand_end": due.isoformat(),
        "business_date": today.isoformat(),
        "today": today.isoformat(),
        "warehouse_scope": warehouse_scope if isinstance(warehouse_scope, str) else "custom",
        "warehouse_filter": warehouse_filter,
        "finished_goods_filter": finished_goods_filter,
        "finished_goods_qty": finished_goods_qty,
        "remaining_finished_goods_qty": max(0.0, finished_goods_qty - qty),
        "fulfillment_mode": "production_plan",
        "production_plan_required": True,
        "customer_earliest_available_date": customer_earliest.isoformat(),
        "customer_late_days": customer_late_days,
        "substitute_enabled": substitute_enabled,
        "report_grain": report_grain,
        "can_deliver_on_time": can_deliver,
        "max_delay_days": max_delay_days,
        "delay_a": _sorted_delays(delay_a),
        "delay_b": _sorted_delays(delay_b),
        "nodes": reported,
        "node_count_total": len(nodes),
        "gaps": gaps,
        "supply_status_summary": summary,
        "warnings": warnings_out,
        "delivery_commitment_status": "confirmed_late" if known_late else ("cannot_confirm" if uncertain_items else "confirmed_by_function_caliber"),
        "uncertain_supply_items": uncertain_items,
    }
