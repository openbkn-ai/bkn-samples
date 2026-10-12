from __future__ import annotations

from datetime import date, datetime
from math import isfinite

from .errors import CannotCompute
from .snapshot import _f

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


def dated_po_supply(rows: list[dict], *, today: date, due: date, required: float) -> dict:
    """Only future/today net receipts are reliable; overdue receipts need confirmation."""
    dated = []
    receipts = []
    overdue = unknown = total = 0.0
    for row in rows:
        qty = max(0.0, _f(row.get("qty")) - _f(row.get("actqty")))
        if (row.get("rowclosestatus_title") or "").strip() == "已关闭" or qty <= 0:
            continue
        total += qty
        day = _parse_date(row.get("deliverdate"))
        if day is None:
            unknown += qty
            eligibility = "undated"
        elif day <= today:
            overdue += qty
            eligibility = "overdue_unconfirmed"
        else:
            dated.append((day, qty))
            eligibility = "on_time" if day <= due else "late"
        receipts.append({"net_open_qty": qty,
                         "deliver_date": day.isoformat() if day else "",
                         "eligibility": eligibility,
                         "included_in_on_time_qty": eligibility == "on_time"})
    cumulative = 0.0
    sufficient_day = None
    on_time = sum(qty for day, qty in dated if day <= due)
    for day, qty in sorted(dated):
        cumulative += qty
        if sufficient_day is None and cumulative >= required and required > 0:
            sufficient_day = day
    return {"open_po_qty": total, "on_time_po_qty": on_time,
            "reliable_po_qty": cumulative, "overdue_po_qty": overdue,
            "undated_po_qty": unknown, "sufficient_po_date": sufficient_day.isoformat() if sufficient_day else "",
            "po_receipts": receipts}


def supply_status(
    snap,
    material_code: str,
    *,
    due_date=None,
    gross_requirement: float = 0,
    warehouse_scope: str | list[str] | None = "all",
    today: date | None = None,
    child_short: bool = False,
    available_override: float | None = None,
    po_rows_override: list[dict] | None = None,
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
    today = today or date(2026, 8, 25)
    gross = float(gross_requirement or 0)
    if not isfinite(gross) or gross < 0:
        raise CannotCompute("需求量必须是有限非负数")
    avail = available_qty(snap, code, warehouse_scope) if available_override is None else available_override
    po_rows = po_open_rows(snap, code) if po_rows_override is None else po_rows_override
    evidence = dated_po_supply(po_rows, today=today, due=due, required=max(0, gross - avail))
    supply = avail + evidence["on_time_po_qty"]
    payload = {"material_code": code, "supply": supply, "gross": gross,
               "available_qty": avail, "business_date": today.isoformat(), "due_date": due.isoformat(),
               "on_time_covered": due >= today and supply >= gross,
               "on_time_shortage_qty": max(0.0, gross - supply),
               "coverage_basis": "confirmed_inventory_and_valid_dated_open_po_only",
               "deadline_elapsed": due < today, **evidence}
    if due < today:
        return {**payload, "status": "deadline_risk", "reason": "需求日期早于业务日期，当前供应不能证明过去按期覆盖"}
    if supply >= gross:
        return {**payload, "status": "sufficient"}
    row = snap.materials.get(code) or {}
    attr = (row.get("materialattr") or "").strip()
    pr_rows = pr_open_rows(snap, code)
    mrp = has_mrp(snap, code)
    has_po = evidence["open_po_qty"] > 0
    has_pr = bool(pr_rows)
    lt = leadtime_days(snap, code) if code in snap.materials else 0
    days_until = (due - today).days
    if evidence["overdue_po_qty"] > 0:
        return {**payload, "status": "po_overdue", "reason": "过期未收货 PO 需重新确认到货日"}
    if evidence["undated_po_qty"] > 0:
        return {**payload, "status": "unknown", "reason": "未收货 PO 缺少有效到货日"}

    if attr in ("外购", "委外"):
        if not mrp:
            return {**payload, "status": "anomaly"}
        if has_po and any(day > due for day, _qty in [(d, q) for d, q in [( _parse_date(r.get("deliverdate")), max(0.0, _f(r.get("qty")) - _f(r.get("actqty")))) for r in po_rows] if d is not None and q > 0]):
            return {**payload, "status": "deadline_risk"}
        if not has_po and lt > days_until:
            return {**payload, "status": "deadline_risk"}
        if not has_pr:
            return {**payload, "status": "no_pr"}
        if has_pr and not has_po:
            return {**payload, "status": "no_po"}
        return {**payload, "status": "po_in_transit"}

    if attr == "自制":
        if child_short:
            return {**payload, "status": "child_short"}
        if not mrp:
            return {**payload, "status": "unscheduled"}
        return {**payload, "status": "plan_gap"}

    if not mrp:
        return {**payload, "status": "anomaly"}
    return {**payload, "status": "plan_gap"}
