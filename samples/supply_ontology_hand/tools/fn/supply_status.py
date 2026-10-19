from __future__ import annotations

from datetime import date, datetime

from .inventory import (
    available_qty,
    has_mrp,
    in_transit_qty,
    po_open_rows,
    pr_open_rows,
)
from .leadtime import leadtime_days


def _parse_date(val) -> date | None:
    if val is None:
        return None
    text = str(val).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt).date()
        except ValueError:
            continue
    return None


def supply_status(
    snap,
    material_code: str,
    *,
    due_date=None,
    gross_requirement: float = 0,
    warehouse_scope: str | list[str] | None = "production_available",
    today: date | None = None,
    child_short: bool = False,
) -> dict:
    """S1 internal 10-bin. No due date → unknown. Not a Type-1 function."""
    code = (material_code or "").strip()
    due = _parse_date(due_date)
    if due is None:
        return {
            "material_code": code,
            "status": "unknown",
            "reason": "无交货日/到位日，不能判定供应状态",
        }
    today = today or date.today()
    avail = available_qty(snap, code, warehouse_scope)
    transit = in_transit_qty(snap, code)
    supply = avail + transit
    gross = float(gross_requirement or 0)
    if supply >= gross and gross >= 0:
        return {"material_code": code, "status": "sufficient", "supply": supply, "gross": gross}

    row = snap.materials.get(code) or {}
    attr = (row.get("materialattr") or "").strip()
    po_rows = po_open_rows(snap, code)
    pr_rows = pr_open_rows(snap, code)
    mrp = has_mrp(snap, code)
    has_po = bool(po_rows)
    has_pr = bool(pr_rows)
    lt = leadtime_days(snap, code) if code in snap.materials else 0
    days_until = (due - today).days

    if attr in ("外购", "委外"):
        if not mrp:
            return {"material_code": code, "status": "anomaly", "supply": supply, "gross": gross}
        if has_po:
            po_dates = [_parse_date(r.get("deliverdate")) for r in po_rows]
            po_dates = [d for d in po_dates if d]
            if po_dates and max(po_dates) <= today:
                return {"material_code": code, "status": "po_overdue", "supply": supply, "gross": gross}
            if po_dates and max(po_dates) > due:
                return {"material_code": code, "status": "deadline_risk", "supply": supply, "gross": gross}
        if not has_po and lt > days_until:
            return {"material_code": code, "status": "deadline_risk", "supply": supply, "gross": gross}
        if not has_pr:
            return {"material_code": code, "status": "no_pr", "supply": supply, "gross": gross}
        if has_pr and not has_po:
            return {"material_code": code, "status": "no_po", "supply": supply, "gross": gross}
        return {"material_code": code, "status": "po_in_transit", "supply": supply, "gross": gross}

    if attr == "自制":
        if child_short:
            return {"material_code": code, "status": "child_short", "supply": supply, "gross": gross}
        if not mrp:
            return {"material_code": code, "status": "unscheduled", "supply": supply, "gross": gross}
        return {"material_code": code, "status": "plan_gap", "supply": supply, "gross": gross}

    if not mrp:
        return {"material_code": code, "status": "anomaly", "supply": supply, "gross": gross}
    return {"material_code": code, "status": "plan_gap", "supply": supply, "gross": gross}
