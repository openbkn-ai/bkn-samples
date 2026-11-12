"""Write a kit-schedule plan: schedule a demand forecast (or one of its products) on a production line.

The Function runs inside the sandbox as the caller. It reads the demand, the line, the facts the kit
check needs and the existing plans through ``sandbox_sdk.bkn``; it writes the plan row into the
plan dataset with ``bkn_osdk.call`` (vega dataset document PUT). The demand forecast is not changed.

One forecast number + product code (empty = whole bill) has at most one active plan (status not
cancelled): scheduling it again updates that plan and, when the planned finish moves, adds one to
its reschedule count and keeps the previous finish.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any

from fn import CannotCompute, DEFAULT_BUSINESS_DATE
from fn.kitplan import day, kit_check
from fn.read_complete import read_complete
from managed_execution import KN_ID, _equal, _in, _page_rows, load_bkn_rows

OT_PLAN = f"{KN_ID}_kitplan"
OT_FORECAST = f"{KN_ID}_forecast"
OT_LINE = f"{KN_ID}_line"
OT_PRODUCT = f"{KN_ID}_product"
SCHEDULED, CONFIRMED, CANCELLED = "已排", "已确认", "已取消"
STATUSES = (SCHEDULED, CONFIRMED, CANCELLED)
OPEN_FORECAST = "正常"
LINE_KIND = "产线"
ZONE = "+08:00"
FIELDS = ("plan_id", "bill_no", "product_code", "line_code", "planned_start", "planned_finish", "quantity", "kit_date",
          "kit_status", "key_material", "shortage_note", "plan_status", "reschedule_count", "previous_finish",
          "source_scenario", "planner", "planned_at")


def moment(value: Any, default_time: str) -> str:
    """Normalise a date or datetime to ``YYYY-MM-DDTHH:MM:SS+08:00``; a bare date gets ``default_time``."""
    text = str(value or "").strip()
    day(text)
    if len(text) == 10:
        return f"{text}T{default_time}{ZONE}"
    text = text.replace(" ", "T", 1)
    if len(text) == 16:
        text += ":00"
    if text.endswith("Z") or "+" in text[10:] or "-" in text[10:]:
        return text
    return text[:19] + ZONE


def _text(params: Mapping[str, Any], key: str) -> str:
    return str(params.get(key) or "").strip()


def schedule(params: Mapping[str, Any], query: Callable[..., Mapping[str, Any]], write: Callable[[str, dict], Any],
             *, now: datetime | None = None, business_date: str = DEFAULT_BUSINESS_DATE) -> dict[str, Any]:
    """Create, update or cancel one plan and return the plan with its kit check."""

    def read(ot_id: str, condition: dict[str, Any]) -> list[dict[str, Any]]:
        return read_complete(query, {"kn_id": KN_ID, "ot_id": ot_id, "condition": condition}, _page_rows,
                             page_size=500, max_rows=50_000)

    plan_id, bill, product = _text(params, "plan_id"), _text(params, "bill_no"), _text(params, "product_code")
    status = _text(params, "plan_status") or SCHEDULED
    if status not in STATUSES:
        raise CannotCompute(f"计划状态只能是{'、'.join(STATUSES)}")
    existing = None
    if plan_id:
        found = read(OT_PLAN, _equal("plan_id", plan_id))
        if not found:
            raise CannotCompute(f"没有找到计划 {plan_id}")
        existing = found[0]
        bill = bill or str(existing.get("bill_no") or "")
        product = product if "product_code" in params else str(existing.get("product_code") or "")
    if not bill:
        raise CannotCompute("请提供预测单号")
    plans = read(OT_PLAN, _equal("bill_no", bill))
    same = [p for p in plans if str(p.get("product_code") or "") == product]
    if existing is None:
        existing = next((p for p in same if p.get("plan_status") != CANCELLED), None)
    stamp = f"{business_date}T{(now or datetime.now()).strftime('%H:%M:%S')}{ZONE}"
    planner = _text(params, "planner") or (str(existing.get("planner") or "") if existing else "")

    if status == CANCELLED:
        if existing is None or existing.get("plan_status") == CANCELLED:
            raise CannotCompute(f"{bill} {product or '整单'} 没有可取消的有效计划")
        row = {**{k: existing.get(k) for k in FIELDS}, "plan_status": CANCELLED, "planner": planner, "planned_at": stamp}
        write(str(row["plan_id"]), _clean(row))
        return {"action": "cancelled", "plan": _clean(row)}

    line_code = _text(params, "line_code") or (str(existing.get("line_code") or "") if existing else "")
    if not line_code:
        raise CannotCompute("请提供产线编码")
    start = moment(params.get("planned_start") or (existing or {}).get("planned_start"), "08:00:00")
    finish = moment(params.get("planned_finish") or (existing or {}).get("planned_finish"), "20:00:00")
    if finish < start:
        raise CannotCompute("计划完工不能早于计划开工")
    lines = [r for r in read(OT_FORECAST, _equal("billno", bill))
             if r.get("closestatus_title") == OPEN_FORECAST and (not product or r.get("material_number") == product)]
    if not lines:
        raise CannotCompute(f"预测单 {bill}{' 的产品 ' + product if product else ''} 没有未关闭的需求")
    line = next(iter(read(OT_LINE, _equal("line_code", line_code))), None)
    if line is None or line.get("line_kind") != LINE_KIND:
        raise CannotCompute(f"{line_code} 不是可排产的产线")
    codes = sorted({str(r["material_number"]) for r in lines})
    wrong = sorted(str(p.get("material_number")) for p in read(OT_PRODUCT, _in("material_number", codes))
                   if p.get("line_code") != line_code)
    if wrong:
        raise CannotCompute(f"产品 {'、'.join(wrong)} 不在产线 {line_code} 的可生产产品线内")

    demands = [{"product": str(r["material_number"]), "qty": r["qty"]} for r in lines]
    facts = load_bkn_rows("demand_coverage", query, {"demands": demands, "need_by": day(start), "reserve_signed_backlog": True})
    names = {str(r.get("material_code")): str(r.get("material_name") or "") for r in facts.get("bom", [])}
    kit = kit_check(facts, demands, start, business_date=business_date, names=names)

    if existing is not None:
        moved = str(existing.get("planned_finish") or "") != finish
        row = {**{k: existing.get(k) for k in FIELDS},
               "reschedule_count": int(existing.get("reschedule_count") or 0) + (1 if moved else 0),
               "previous_finish": existing.get("planned_finish") if moved else existing.get("previous_finish"),
               "plan_status": status if "plan_status" in params and _text(params, "plan_status") else existing.get("plan_status")}
        action = "updated"
    else:
        number = f"KP-{bill[3:] if bill.startswith('YCD') else bill}-{product or 'ALL'}-{len(same) + 1:02d}"
        row = {"plan_id": number, "reschedule_count": 0, "previous_finish": None, "plan_status": status}
        action = "created"
    row.update(bill_no=bill, product_code=product, line_code=line_code, planned_start=start, planned_finish=finish,
               quantity=round(sum(float(r["qty"]) for r in lines)) if product else None,
               kit_date=kit["kit_date"] or None, kit_status=kit["kit_status"], key_material=kit["key_material"],
               shortage_note=kit["shortage_note"], source_scenario=_text(params, "source_scenario") or row.get("source_scenario"),
               planner=planner, planned_at=stamp)
    write(str(row["plan_id"]), _clean(row))
    return {"action": action, "plan": _clean(row), "shortages": kit["shortages"],
            "reserved_backlog_orders": kit["reserved_backlog_orders"]}


def _clean(row: Mapping[str, Any]) -> dict[str, Any]:
    """Dataset documents carry no empty values; numbers stay numbers."""
    out = {}
    for key in FIELDS:
        value = row.get(key)
        if value is None or value == "":
            continue
        if key in ("quantity", "reschedule_count"):
            value = int(value)
        out[key] = value
    return out


__all__ = ["CANCELLED", "CONFIRMED", "FIELDS", "OT_PLAN", "SCHEDULED", "moment", "schedule"]
