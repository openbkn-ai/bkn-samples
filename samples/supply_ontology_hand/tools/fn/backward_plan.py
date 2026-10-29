"""S1 生产计划齐套倒排纯函数（口径 SSOT：导入指南“业务能力与 MCP 验收”、
skills/production-schedule-backward-planning/references/business-rules.md）。

只吃请求级 Snapshot，不做远程查询，不读运行时 CSV。日期公式、供应状态、
在途口径全部复用既有函数，不在本模块复制公式。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
import math

from dataclasses import replace
from .allocation import finite_quantity, net_requirements
from .bom import product_bom_rows
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
PURCHASED_ATTRS = ("外购", "委外")
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
        raise CannotCompute(f"缺少{label}")
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except ValueError:
        raise CannotCompute(f"{label}不是合法日期（YYYY-MM-DD）：{text}") from None


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
        raise CannotCompute("替代料策略必须显式传入 True 或 False")
    if report_grain not in REPORT_GRAINS:
        raise CannotCompute(f"report_grain 只能是 {REPORT_GRAINS}：{report_grain}")
    if plan_id:
        row = _find_forecast(snap, plan_id)
        if not row:
            raise CannotCompute(f"预测单不存在：{plan_id}")
        forecast_product = str(row.get("material_number") or "").strip()
        forecast_due = _parse_day(row.get("enddate"), f"预测单 {plan_id} 截止日")
        forecast_qty = finite_quantity(row.get("qty"), "预测需求量", positive=True)
        if code and forecast_product != code:
            raise CannotCompute(
                f"预测单 {plan_id} 的产品为 {forecast_product}，与请求 {code} 不一致"
            )
        if demand_end and _parse_day(demand_end, "需求截止日") != forecast_due:
            raise CannotCompute(f"预测单 {plan_id} 截止日与请求 {demand_end} 不一致")
        if demand_qty is not None and _f(row.get("qty"), 0.0) != float(demand_qty):
            raise CannotCompute(f"预测单 {plan_id} 需求量与请求 {demand_qty} 不一致")
        return forecast_product, plan_id, forecast_due, forecast_qty

    if not code:
        raise CannotCompute("新增需求缺少产品编码")
    due = _parse_day(demand_end, "需求截止日")
    try:
        qty = float(demand_qty)
    except (TypeError, ValueError):
        raise CannotCompute(f"需求量不是数字：{demand_qty}") from None
    if not math.isfinite(qty) or qty <= 0:
        raise CannotCompute(f"需求量必须为正数：{demand_qty}")
    return code, plan_id or None, due, qty


def _find_forecast(snap: Snapshot, requested_id: str) -> dict | None:
    """Find a forecast while tolerating numeric resource keys losing CSV leading zeroes."""
    direct = snap.forecast_by_id.get(requested_id)
    if direct is not None or not requested_id.isdigit():
        return direct
    canonical = str(int(requested_id))
    return snap.forecast_by_id.get(canonical)



def _allocated_receipts(snap, code, quantity, pools, today):
    """Reserve dated PO remainders once, in future-date order; old dates are uncertain."""
    if code not in pools:
        rows = []
        for row in po_open_rows(snap, code):
            days = _po_deliver_dates([row])
            day = days[0] if days else None
            remaining = max(0.0, finite_quantity(row.get("qty", 0), "采购数量") -
                            finite_quantity(row.get("actqty", 0), "采购已收数量"))
            rows.append([day, remaining, row])
        rows.sort(key=lambda x: (x[0] is None or x[0] < today, x[0] or date.max))
        pools[code] = rows
    used = []
    for entry in pools[code]:
        take = min(quantity, entry[1])
        if take > 0:
            used.append({**entry[2], "qty": take, "actqty": 0})
            entry[1] -= take
            quantity -= take
    return used


def backward_plan(snap: Snapshot, product: str | None = None, *,
                  forecast_id: str | None = None, demand_end: str | None = None,
                  demand_qty=None, business_date: str | None = None,
                  warehouse_scope="production_available", substitute_enabled: bool,
                  report_grain: str = "summary") -> dict:
    """Customer supply plan: net finished goods, then net each component position.

    Dates are conditional planning estimates. Unreceived POs with absent or
    overdue dates never become a confirmed customer arrival date.
    """
    code, plan_id, due, qty = _validated_request(snap, product, forecast_id,
        demand_end, demand_qty, substitute_enabled, report_grain)
    today = _parse_day(DEFAULT_BUSINESS_DATE if business_date is None else business_date, "业务日期")
    net = net_requirements(snap, code, qty, scope=warehouse_scope,
        substitute_enabled=substitute_enabled, include_finished_goods=True,
        finished_goods_scope="finished_goods", include_in_transit=True,
        expand_covered_branches=True, max_nodes=MAX_NODES)
    fg = net["finished_goods_qty"]
    base = dict(product_code=code, forecast_id=plan_id, demand_qty=qty,
        demand_end=due.isoformat(), business_date=today.isoformat(), today=today.isoformat(),
        warehouse_scope=warehouse_scope if isinstance(warehouse_scope, str) else "custom",
        warehouse_filter=resolve_warehouse_scope(warehouse_scope),
        finished_goods_filter=resolve_warehouse_scope("finished_goods"),
        finished_goods_qty=fg, remaining_finished_goods_qty=max(0., fg-qty),
        root_net_demand=net["root_net_demand"], substitute_enabled=substitute_enabled,
        report_grain=report_grain)
    summary = {status: 0 for status in SUPPLY_STATUSES}
    if net["root_net_demand"] == 0:
        late = max(0, (today-due).days)
        return {**base, "fulfillment_mode":"finished_goods", "production_plan_required":False,
            "customer_earliest_available_date":today.isoformat(), "customer_late_days":late,
            "can_deliver_on_time":late == 0, "max_delay_days":late, "delay_a":[], "delay_b":[],
            "nodes":[], "node_count_total":0, "gaps":[], "supply_status_summary":summary,
            "uncertain_supply_items":[], "warnings":["成品现货已覆盖需求，未启动制造倒排。"]}
    root = dict(material_code=code, parent_material_code="", bom_level=0,
        cumulative_usage=1., gross_requirement=qty, available_qty=fg,
        inventory_allocated_qty=net["finished_goods_allocated_qty"], in_transit_qty=0.,
        po_allocated_qty=0., net_requirement=net["root_net_demand"], is_leaf=False,
        parent_index=None)
    traces = [root] + [dict(line, parent_index=0 if line["parent_index"] is None
                           else line["parent_index"]+1) for line in net["lines"]]
    nodes, receipt_pools = [], {}
    for trace in traces:
        material = trace["material_code"]
        lt = leadtime_days(snap, material)
        parent = trace["parent_index"]
        end = due if parent is None else nodes[parent]["_start"] - timedelta(days=1)
        # One-day stock handling only when the complete position is covered.
        gantt = 1 if trace["net_requirement"] <= 1e-9 else max(lt, 1)
        start = end - timedelta(days=lt if parent is None else gantt)
        used = _allocated_receipts(snap, material, trace["po_allocated_qty"], receipt_pools, today)
        nodes.append({**trace, "usage_per_unit":trace["cumulative_usage"],
            "start_date":start.isoformat(), "end_date":end.isoformat(),
            "lead_time_days":lt, "_start":start, "_end":end, "_gantt_days":gantt,
            "_used_po":used, "_has_mrp":has_mrp(snap, material)})
    children = [[] for _ in nodes]
    for i, item in enumerate(nodes):
        if item["parent_index"] is not None:
            children[item["parent_index"]].append(i)
    ready = [today for _ in nodes]
    lower_ready = [today for _ in nodes]
    short_below = [False for _ in nodes]
    uncertain, gaps, delay_a, delay_b = [], [], {}, {}
    for i in range(len(nodes)-1, -1, -1):
        item = nodes[i]
        material = item["material_code"]
        residual = item["net_requirement"]
        short_below[i] = any(short_below[j] or
            (nodes[j]["is_leaf"] and nodes[j]["net_requirement"] > 1e-9) for j in children[i])
        dates = [today]
        unknown = False
        for row in item["_used_po"]:
            ds = _po_deliver_dates([row])
            if not ds or ds[0] < today:
                unknown = True
                uncertain.append({"material_code":material, "quantity":row["qty"],
                    "deliverdate":row.get("deliverdate"), "reason":"未收货采购日期缺失或已过期，需确认实际到货日"})
            else:
                dates.append(ds[0])
        if residual > 1e-9:
            if children[i]:
                if any(ready[j] is None for j in children[i] if nodes[j]["gross_requirement"] > 0):
                    unknown = True
                relevant = [lower_ready[j] for j in children[i]
                            if nodes[j]["gross_requirement"] > 0]
                dates.append(max(relevant, default=today) + timedelta(days=max(item["lead_time_days"],1)+1))
            else:
                dates.append(today + timedelta(days=max(item["lead_time_days"],1)))
        lower_ready[i] = max(dates)
        ready[i] = None if unknown else lower_ready[i]
        attr = str((snap.materials.get(material) or {}).get("materialattr") or "").strip()
        # Status gets this position's allocated pool, never the original global stock again.
        local = replace(snap, inv_by_material={material:[{"available_inventory_qty":item["inventory_allocated_qty"]}]},
                        po_by_material={material:item["_used_po"]})
        status = supply_status(local, material, due_date=item["_end"],
            gross_requirement=item["gross_requirement"], warehouse_scope="all",
            today=today, child_short=short_below[i])["status"]
        shortage = residual if item["is_leaf"] else 0.
        candidates = []
        if i and shortage > 1e-9 and attr in PURCHASED_ATTRS:
            late = max(0, (today+timedelta(days=max(item["lead_time_days"],1))-item["_end"]).days)
            if late: candidates.append((late,"A"))
        allocated_dates = _po_deliver_dates(item["_used_po"])
        latest = max((d for d in allocated_dates if d >= today), default=None)
        if i and latest and latest > item["_end"]:
            candidates.append(((latest-item["_end"]).days,"B"))
        days, cls = max(candidates, default=(0,""))
        item.update(supply_status=status, delay_class=cls, delay_days=days,
            evidence=dict(material_attr=attr, usage_per_unit=item["usage_per_unit"],
                gross_requirement=item["gross_requirement"], available_qty=item["available_qty"],
                in_transit_qty=item["in_transit_qty"],
                supply_qty=item["inventory_allocated_qty"]+item["po_allocated_qty"],
                shortage_qty=shortage, manufacturing_qty=residual if not item["is_leaf"] else 0.,
                open_pr_qty=pr_open_qty(snap,material), open_po_count=len(item["_used_po"]),
                latest_po_deliver_date=latest.isoformat() if latest else "",
                has_open_mrp=item["_has_mrp"], lead_time_days=item["lead_time_days"],
                gantt_days=item["_gantt_days"], child_short=short_below[i]))
        summary[status] += 1
        if shortage > 1e-9:
            gaps.append({key:item[key] for key in ("material_code","parent_material_code","bom_level",
                "end_date","gross_requirement","available_qty","in_transit_qty","supply_status")} | {"shortage_qty":shortage})
        if cls:
            entry = {key:item[key] for key in ("material_code","parent_material_code","bom_level",
                "delay_class","delay_days","end_date","start_date","lead_time_days","supply_status","evidence")}
            bucket = delay_a if cls == "A" else delay_b
            if material not in bucket or bucket[material]["delay_days"] < days: bucket[material] = entry
    earliest = ready[0]
    late = max(0,(earliest-due).days) if earliest is not None else None
    can_deliver = earliest <= due if earliest is not None else (False if lower_ready[0] > due else None)
    max_delay = max([v["delay_days"] for v in [*delay_a.values(),*delay_b.values()]],default=0)
    reported = nodes if report_grain == "full_tree" else [n for n in nodes if n["bom_level"] == 0 or
        n["delay_class"] or n["supply_status"] in RISK_STATUSES or n["evidence"]["shortage_qty"] > 0]
    for item in nodes:
        for key in tuple(item):
            if key.startswith("_"): item.pop(key)
    return {**base, "fulfillment_mode":"production_plan", "production_plan_required":True,
        "customer_earliest_available_date":earliest.isoformat() if earliest is not None else None,
        "customer_late_days":late, "customer_earliest_lower_bound":lower_ready[0].isoformat(), "can_deliver_on_time":can_deliver, "max_delay_days":max_delay,
        "delay_a":sorted(delay_a.values(),key=lambda r:(-r["delay_days"],r["material_code"])),
        "delay_b":sorted(delay_b.values(),key=lambda r:(-r["delay_days"],r["material_code"])),
        "nodes":reported,"node_count_total":len(nodes),"gaps":list(reversed(gaps)),
        "supply_status_summary":summary, "uncertain_supply_items":uncertain,
        "warnings":["到货与制造日期为标准提前期模型估算；分配、产能、质检和发运条件需业务确认。"]}
