"""Schedule rule checks for kit-schedule plans: are materials kitted at the planned start, can the line build it.

Kit check, on one shared pool for all the plans checked together:

- the signed backlog of the plans' products is reserved first, in promised-date order (the same
  netting as ``demand_coverage``);
- then confirmed plans in planned-start order, then scheduled plans in planned-start order (ties by
  key); a plan uses available stock plus open purchase lines due from the business date to its
  start, without finished goods (it is a production plan); overdue lines are not supply;
- only real issue and production records hold material: a product of the plan with a started
  production order for the plan's forecast has drawn its materials (they are out of stock already)
  and is not checked again; the plan's other products, and confirmed plans without one, compete like
  any other; a plan all of whose products have started passes and draws nothing;
- the plans checked are the network's active plans with the scenario's changes; a task sent that is
  one of them replaces it (same plan ID or key), and a task that is not (the plan an unscheduled
  demand would make) is checked on its own on top of them, so it takes no stock from other such
  proposals; a batch check and the detail of one task therefore always give the same answer;
- for every material a plan is short of, the ready date is the open-purchase arrival after the start
  that closes its gap, or else the business date plus its purchase lead time (no purchase request
  yet; an overdue line counts as needing a new order). The plan's earliest start ``at`` is the latest
  ready date; the materials that set it are the key materials.

Severity: a start before ``at`` is hard. When ``at`` is on or before the start, the gap is covered only
by materials that still need a purchase request placed now: soft.

Two outputs from one analysis: the check (one short result per task, for a batch) and the detail (one
paged table of a plan's short materials, rows grouped by reason).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from .kitplan import KIT_COVERED, KIT_PENDING, KIT_SHORT
from .planning import DEFAULT_BUSINESS_DATE, Plan, is_open_po, unshipped

HARD, SOFT = "hard", "soft"
SCHEDULED, CONFIRMED, CANCELLED = "已排", "已确认", "已取消"
OPEN_FORECAST = "正常"
STARTED_WORK = ("开工", "部分完工")
LINE_KIND = "产线"
LIST_SEPARATORS = ("、", ",", "，", ";", "；")
DEFAULT_LOCALE = "zh-CN"
MAX_TASKS = 200
TEXT_LIMIT = {"zh-CN": 40, "en-US": 60}
GROUPS = ("late_po", "overdue_po", "no_pr", "reserved")

LABELS = {
    "zh-CN": {
        "late_po": "在途晚到", "overdue_po": "采购逾期", "no_pr": "尚未下采购申请", "reserved": "库存被已签约欠货占用",
        "short_materials": "缺料物料", "bom_materials": "BOM 物料", "short": "缺料", "key_materials": "关键物料",
        "material": "物料", "parent": "所属上级件", "need": "需求", "available": "可用", "gap": "缺口",
        "ready": "预计可用", "source": "来源单据", "whole_bill": "整单", "start": "计划开工",
        "covered": "物料齐套", "covered_at": "开工 {start} 物料齐套", "issued": "已开工，物料已按工单领用",
        "short_text": "缺料 {n} 种，关键：{name} {reason}", "conclusion": "缺料 {n} 种，最早 {at} 可齐套",
        "po_due": "在途 {due} 到", "need_pr": "未下采购申请", "overdue": "采购逾期",
        "note": "计划开工 {start} 缺料：{items}{more}；最早 {at} 可齐套。", "note_item": "{name} 缺 {gap}（{reason}）",
        "note_more": "等 {n} 种物料", "note_sep": "；",
        "note_pending": "计划开工 {start} 前须下采购申请：{items}{more}；及时下单最早 {at} 可齐套。",
        "no_start": "无法检查：没有计划开工日", "no_demand": "无法检查：预测单 {bill} 没有未关闭的需求",
        "bad_tasks": "tasks 必须是任务列表", "too_many": "一次最多检查 {n} 条任务", "bad_task": "明细需要一条任务（task）",
    },
    "en-US": {
        "late_po": "On order, arriving late", "overdue_po": "Purchase overdue", "no_pr": "No purchase request yet",
        "reserved": "Stock held by signed backlog",
        "short_materials": "Short materials", "bom_materials": "BOM materials", "short": "Short", "key_materials": "Key materials",
        "material": "Material", "parent": "Parent part", "need": "Needed", "available": "Available", "gap": "Gap",
        "ready": "Expected ready", "source": "Source document", "whole_bill": "Whole bill", "start": "planned start",
        "covered": "Materials kitted", "covered_at": "Kitted for start {start}",
        "issued": "In production; materials issued to work orders",
        "short_text": "{n} short; key: {name} {reason}", "conclusion": "{n} materials short; kitted {at} at the earliest",
        "po_due": "due {due}", "need_pr": "no purchase request", "overdue": "purchase overdue",
        "note": "Short at planned start {start}: {items}{more}; kitted {at} at the earliest.",
        "note_item": "{name} short {gap} ({reason})", "note_more": ", {n} materials in all", "note_sep": "; ",
        "note_pending": "Purchase requests needed before planned start {start}: {items}{more}; kitted {at} at the earliest if ordered now.",
        "no_start": "Not checked: no planned start", "no_demand": "Not checked: forecast {bill} has no open demand",
        "bad_tasks": "tasks must be a list of tasks", "too_many": "at most {n} tasks per call", "bad_task": "the detail needs one task",
    },
}


def _labels(locale: str | None) -> dict[str, str]:
    return LABELS.get(str(locale or ""), LABELS[DEFAULT_LOCALE])


def _d(value: Any) -> Decimal:
    return Decimal(str(value or 0))


def _n(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral_value() else float(round(value, 3))


def _day(value: Any) -> str:
    text = str(value or "").strip()
    if len(text) < 10 or text[4] != "-" or text[7] != "-":
        return ""
    return text[:10]


def _short(day: str, ref: str = DEFAULT_BUSINESS_DATE) -> str:
    """Month/day; the year is added when it is not the business date's year."""
    if not day:
        return ""
    short = f"{int(day[5:7])}/{int(day[8:10])}"
    return short if day[:4] == ref[:4] else f"{day[:4]}/{short}"


def _plus(day: str, days: int) -> str:
    return (date.fromisoformat(day) + timedelta(days=days)).isoformat()


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit - 1] + "…"


def task_fields(task: Mapping[str, Any]) -> dict[str, str]:
    """Forecast number, product (empty = whole bill), line, planned start and status of a task as sent."""
    values = task.get("values") or {}
    return {"key": str(task.get("key") or ""),
            "bill": str(values.get("bill_no") or "").strip(),
            "product": str(values.get("product_code") or "").strip(),
            "line": str(task.get("resource") or values.get("line_code") or "").strip(),
            "start": _day(task.get("start")) or _day(values.get("planned_start")),
            "status": str(values.get("plan_status") or "").strip()}


def check_tasks(tasks: Any, locale: str | None = None) -> list[Mapping[str, Any]]:
    labels = _labels(locale)
    if not isinstance(tasks, list):
        raise ValueError(labels["bad_tasks"])
    if len(tasks) > MAX_TASKS:
        raise ValueError(labels["too_many"].format(n=MAX_TASKS))
    return [t for t in tasks if isinstance(t, Mapping) and t.get("key")]


def demands_of(fields: Mapping[str, str], forecasts: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [{"product": str(r["material_number"]), "qty": r["qty"]} for r in forecasts
            if r.get("billno") == fields["bill"] and r.get("closestatus_title") == OPEN_FORECAST
            and (not fields["product"] or r.get("material_number") == fields["product"])]


def prepare(rows: Mapping[str, Iterable[Mapping[str, Any]]], business_date: str = DEFAULT_BUSINESS_DATE) -> dict[str, Any]:
    """What the allocation needs from the facts, whatever the plans: built once when several sets of plans are
    allocated on the same facts."""
    forecasts = list(rows.get("forecast", ()))
    plan = Plan(rows, business_date=business_date)
    open_lines = [r for r in rows.get("purchase_order", ()) if is_open_po(r)]
    arrivals = sorted((str(r.get("deliverdate") or "")[:10], str(r["material_number"]), _d(r.get("qty")) - _d(r.get("actqty")),
                       str(r.get("billno") or ""), str(r.get("entry_id") or "")) for r in open_lines
                      if str(r.get("deliverdate") or "")[:10] >= business_date)
    overdue = defaultdict(list)
    for r in sorted(open_lines, key=lambda r: str(r.get("deliverdate") or "")):
        if str(r.get("deliverdate") or "")[:10] < business_date:
            overdue[str(r["material_number"])].append((str(r.get("billno") or ""), str(r.get("entry_id") or "")))
    bom_by_product: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for r in rows.get("bom", ()):
        bom_by_product[str(r.get("bom_material_code"))].append(r)
    started = {(str(w.get("sourcebillnumber")), str(w.get("material_number"))) for w in rows.get("work_order", ())
               if w.get("taskstatus_title") in STARTED_WORK}
    return {"forecasts": forecasts, "plan": plan, "arrivals": arrivals, "overdue": overdue,
            "bom_by_product": bom_by_product, "started": started}


def analyse(tasks: list[Mapping[str, Any]], rows: Mapping[str, Iterable[Mapping[str, Any]]], *,
            materials: Mapping[str, Mapping[str, Any]], business_date: str = DEFAULT_BUSINESS_DATE,
            prepared: Mapping[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """Allocate the plans on one pool; per task key: state, the short materials with reason and ready date, and at."""
    facts = prepared or prepare(rows, business_date)
    forecasts, plan, arrivals, overdue = facts["forecasts"], facts["plan"], facts["arrivals"], facts["overdue"]
    bom_by_product, started = facts["bom_by_product"], facts["started"]

    def lead(code: str) -> int:
        value = _d((materials.get(code) or {}).get("purchase_fixedleadtime"))
        return int(value) if value > 0 else 0

    out: dict[str, dict[str, Any]] = {}
    queue = []
    for task in tasks:
        fields = task_fields(task)
        if fields["status"] == CANCELLED:
            out[fields["key"]] = {"fields": fields, "state": "cancelled"}
            continue
        demands = demands_of(fields, forecasts)
        waiting = [d for d in demands if (fields["bill"], d["product"]) not in started]
        if demands and not waiting:
            out[fields["key"]] = {"fields": fields, "state": "issued", "at": fields["start"]}
            continue
        demands = waiting
        if not fields["start"] or not demands:
            out[fields["key"]] = {"fields": fields, "state": "no_start" if not fields["start"] else "no_demand"}
            continue
        queue.append((fields, demands))
    if not queue:
        return out

    pool = plan.pool()
    stock = dict(pool)
    products = {d["product"] for _, ds in queue for d in ds}
    plan.reserve_backlog(pool, products, False)
    backlog_orders: dict[str, list[str]] = defaultdict(list)   # material -> signed orders whose reservation can draw it
    for order in plan.backlog_orders:
        if order.get("product_code") in products and unshipped(order) > 0:
            for r in bom_by_product.get(str(order["product_code"]), []):
                backlog_orders[str(r["material_code"])].append(str(order.get("sales_order_id")))
    queue.sort(key=lambda item: (item[0]["status"] != CONFIRMED, item[0]["start"], item[0]["key"]))
    added = 0
    users: dict[str, list[str]] = defaultdict(list)

    for fields, demands in queue:
        start, key = fields["start"], fields["key"]
        # Plans are taken by status first, so a later plan can start earlier: add each arrival once, when due.
        while added < len(arrivals) and arrivals[added][0] <= start:
            pool[arrivals[added][1]] += arrivals[added][2]
            added += 1
        due_later = [a for a in arrivals[:added] if a[0] > start]
        for a in due_later:
            pool[a[1]] -= a[2]
        before = dict(pool)
        shortages: dict[str, Decimal] = defaultdict(Decimal)
        for demand in demands:
            for code, qty in plan.allocate(pool, demand["product"], demand["qty"], use_finished_goods=False)["shortages"].items():
                shortages[code] += _d(qty)
        used = {code: before[code] - pool[code] for code in before if pool[code] < before[code]}
        for a in due_later:
            pool[a[1]] += a[2]
        for code in used:
            users[code].append(key)
        bom_rows = [r for d in demands for r in bom_by_product.get(d["product"], [])]
        parents: dict[str, str] = {}
        for r in bom_rows:
            parents.setdefault(str(r["material_code"]), str(r.get("parent_material_code") or ""))
        leaves = {str(r["material_code"]) for r in bom_rows if int(_d(r.get("bom_level"))) > 0}
        lines = []
        for code, gap in shortages.items():
            later = [a for a in arrivals if a[1] == code and a[0] > start]
            ready, source, got = "", None, Decimal(0)
            for due, _c, qty, po, entry in later:
                got += qty
                if got >= gap:
                    ready, source = due, (po, entry)
                    break
            taken = used.get(code, Decimal(0))
            if stock.get(code, Decimal(0)) >= gap + taken and backlog_orders.get(code):
                group = "reserved"
            elif later:
                group = "late_po"
            elif overdue.get(code):
                group = "overdue_po"
            else:
                group = "no_pr"
            estimated = not ready
            if estimated:
                ready = _plus(business_date, lead(code))
                source = overdue[code][0] if overdue.get(code) else (later[0][3], later[0][4]) if later else None
            lines.append({"code": code, "parent": parents.get(code, ""), "need": gap + taken, "available": taken,
                          "gap": gap, "ready": ready, "estimated": estimated, "group": group, "po": source,
                          "orders": backlog_orders.get(code, [])[:1] if group == "reserved" else [],
                          "related": [k for k in users.get(code, []) if k != key]})
        at = max((line["ready"] for line in lines), default="")
        for line in lines:
            line["key"] = line["ready"] == at
        out[key] = {"fields": fields, "state": "short" if lines else "covered", "lines": lines, "at": at or start,
                    "bom_materials": len(leaves), "soft": bool(lines) and at <= start,
                    "related": list(dict.fromkeys(k for line in lines for k in line["related"]))}
    return out


def _name(code: str, materials: Mapping[str, Mapping[str, Any]]) -> str:
    name = str((materials.get(code) or {}).get("material_name") or "")
    return f"{name} {code}".strip()


def _key_line(result: Mapping[str, Any]) -> Mapping[str, Any]:
    return max(result["lines"], key=lambda l: (l["ready"], l["gap"], l["code"]))


def _reason(line: Mapping[str, Any], labels: Mapping[str, str]) -> str:
    if not line["estimated"]:
        return labels["po_due"].format(due=_short(line["ready"]))
    return labels["overdue"] if line["group"] == "overdue_po" else labels["need_pr"]


def _identity(task: Mapping[str, Any]) -> str:
    return str((task.get("values") or {}).get("plan_id") or task.get("key") or "")


def overlay(others: Iterable[Mapping[str, Any]], tasks: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """The network's plans with the tasks sent laid over them: same plan ID or key replaces, new ones are added."""
    tasks = list(tasks)
    sent = {_identity(t) for t in tasks} | {str(t.get("key")) for t in tasks}
    return [o for o in others if _identity(o) not in sent and str(o.get("key")) not in sent] + tasks


def assess(others: Iterable[Mapping[str, Any]], tasks: Iterable[Mapping[str, Any]],
           rows: Mapping[str, Iterable[Mapping[str, Any]]], *, materials: Mapping[str, Mapping[str, Any]],
           business_date: str = DEFAULT_BUSINESS_DATE) -> dict[str, dict[str, Any]]:
    """What the check finds for each task, by key, the same in a batch as in one task's detail.

    A task that is one of the plans (``others``: the network's active plans with the scenario's changes) is
    allocated with them. A task that is not a plan, such as the plan a demand would make at its suggested start,
    is checked on its own on top of the plans: plans that only might be made do not take stock from each other."""
    others, tasks = list(others), list(tasks)
    known = {_identity(o) for o in others} | {str(o.get("key")) for o in others}
    planned = [t for t in tasks if _identity(t) in known or str(t.get("key")) in known]
    proposed = [t for t in tasks if not (_identity(t) in known or str(t.get("key")) in known)]
    facts = prepare(rows, business_date)
    plans = overlay(others, planned)
    found = analyse(plans, rows, materials=materials, business_date=business_date, prepared=facts)
    out = {str(t.get("key")): found[str(t.get("key"))] for t in planned if str(t.get("key")) in found}
    for task in proposed:
        key = str(task.get("key"))
        alone = analyse(plans + [task], rows, materials=materials, business_date=business_date, prepared=facts)
        if key in alone:
            out[key] = alone[key]
    return out


def kit_rule(tasks: list[Mapping[str, Any]], rows: Mapping[str, Iterable[Mapping[str, Any]]], *,
             materials: Mapping[str, Mapping[str, Any]], business_date: str = DEFAULT_BUSINESS_DATE,
             locale: str | None = None, others: Iterable[Mapping[str, Any]] = ()) -> list[dict[str, Any]]:
    """One result per task sent: ``{key, pass, severity, text, related, at, counts, detail}``; pass None when not
    applicable. ``others`` are the network's active plans the tasks are checked with."""
    labels, limit = _labels(locale), TEXT_LIMIT.get(str(locale or DEFAULT_LOCALE), 40)
    analysis = assess(others, tasks, rows, materials=materials, business_date=business_date)
    results = []
    for task in tasks:
        key = str(task.get("key") or "")
        if key not in analysis:
            continue
        item = analysis[key]
        if item["state"] == "cancelled":
            results.append({"key": key, "pass": None, "text": "", "related": []})
        elif item["state"] in ("no_start", "no_demand"):
            results.append({"key": key, "pass": False, "severity": HARD, "related": [],
                            "text": _clip(labels[item["state"]].format(bill=item["fields"]["bill"] or "-"), limit)})
        elif item["state"] == "issued":
            results.append({"key": key, "pass": True, "related": [], "at": item["fields"]["start"],
                            "text": _clip(labels["issued"], limit)})
        elif item["state"] == "covered":
            results.append({"key": key, "pass": True, "related": [], "at": item["fields"]["start"],
                            "text": _clip(labels["covered_at"].format(start=_short(item["fields"]["start"])), limit)})
        else:
            lines, top = item["lines"], _key_line(item)
            base = labels["short_text"].format(n=len(lines), name="\0", reason=_reason(top, labels))
            room = max(6, limit - len(base) + 1)
            name = _name(top["code"], materials)
            if len(name) > room:
                name = top["code"] if len(top["code"]) <= room else _clip(top["code"], room)
            counts = [{"label": labels["short_materials"], "value": len(lines)}]
            for group in ("no_pr", "overdue_po", "late_po"):
                value = sum(1 for line in lines if line["group"] == group)
                if value and len(counts) < 4:
                    counts.append({"label": labels[group], "value": value})
            results.append({"key": key, "pass": False, "severity": SOFT if item["soft"] else HARD,
                            "text": _clip(base.replace("\0", name), limit), "related": item["related"],
                            "at": item["at"], "counts": counts, "detail": True})
    return results


def record(item: Mapping[str, Any], materials: Mapping[str, Mapping[str, Any]], locale: str | None = None) -> dict[str, Any]:
    """What a plan records about its kit, from the same analysis as the check: covered (and the start it is
    kitted for) when the check passes; covered once ordered (soft) when only purchase requests still to be
    placed now are missing and they arrive by the start; else short. Both of the latter carry the earliest
    kitted date, the key material and a note naming the materials and why they are missing."""
    labels = _labels(locale)
    start = item["fields"]["start"]
    if item["state"] in ("covered", "issued"):
        return {"kit_status": KIT_COVERED, "kit_date": start, "key_material": "", "shortage_note": "", "shortages": {}}
    lines = sorted(item["lines"], key=lambda l: (not l["key"], -l["gap"], l["code"]))
    items = labels["note_sep"].join(labels["note_item"].format(name=_name(l["code"], materials), gap=_n(l["gap"]),
                                                                reason=_reason(l, labels)) for l in lines[:3])
    more = labels["note_more"].format(n=len(lines)) if len(lines) > 3 else ""
    soft = bool(item.get("soft"))
    return {"kit_status": KIT_PENDING if soft else KIT_SHORT, "kit_date": item["at"], "key_material": _key_line(item)["code"],
            "shortage_note": labels["note_pending" if soft else "note"].format(start=start, items=items, more=more, at=item["at"]),
            "shortages": {l["code"]: _n(l["gap"]) for l in lines}}


def kit_detail(task: Mapping[str, Any], others: list[Mapping[str, Any]], rows: Mapping[str, Iterable[Mapping[str, Any]]], *,
               materials: Mapping[str, Mapping[str, Any]], products: Mapping[str, str] | None = None,
               business_date: str = DEFAULT_BUSINESS_DATE, locale: str | None = None, query: Mapping[str, Any] | None = None,
               kn_id: str = "") -> dict[str, Any]:
    """The short materials of one plan, checked together with the other active plans, as a paged table."""
    labels = _labels(locale)
    if not isinstance(task, Mapping) or not task.get("key"):
        raise ValueError(labels["bad_task"])
    key = str(task["key"])
    item = assess(others, [task], rows, materials=materials, business_date=business_date)[key]
    fields = item["fields"]
    product = fields["product"]
    title = " · ".join([fields["bill"] or "-", (products or {}).get(product) or product if product else labels["whole_bill"],
                        f"{labels['start']} {_short(fields['start'])}"])
    columns = [{"key": k, "label": labels[label], "type": t} for k, label, t in
               (("material", "material", "text"), ("parent", "parent", "text"), ("need", "need", "number"),
                ("available", "available", "number"), ("short", "gap", "number"), ("ready", "ready", "date"),
                ("source", "source", "link"))]
    if item["state"] != "short":
        conclusion = labels["covered"] if item["state"] == "covered" else labels["issued"] if item["state"] == "issued" else \
            labels.get(item["state"], "").format(bill=fields["bill"] or "-")
        return {"title": title, "conclusion": conclusion, "at": item.get("at") or fields["start"],
                "summary": [{"label": labels["bom_materials"], "value": item.get("bom_materials", 0)}],
                "groups": [], "columns": columns, "rows": [], "total": 0}
    lines = item["lines"]
    query = query or {}
    group, search = query.get("group"), str(query.get("search") or "").strip().lower()
    chosen = [l for l in lines if (not group or l["group"] == group) and (not query.get("keyOnly") or l["key"])
              and (not search or search in _name(l["code"], materials).lower())]
    # Latest expected-ready first; the key materials set the earliest start, so they lead.
    chosen.sort(key=lambda l: (l["ready"], l["key"], l["gap"], l["code"]), reverse=True)
    offset, limit = max(0, int(query.get("offset") or 0)), max(1, min(500, int(query.get("limit") or 50)))
    out_rows = []
    for line in chosen[offset:offset + limit]:
        po, entry = line["po"] or ("", "")
        if line["orders"]:
            source, link = line["orders"][0], {"objectType": f"{kn_id}_salesorder", "key": line["orders"][0]}
        elif po:
            source, link = po, {"objectType": f"{kn_id}_po", "key": entry}
        else:
            source, link = "", None
        out_rows.append({"id": line["code"], "group": line["group"], "key": line["key"],
                         "cells": {"material": _name(line["code"], materials),
                                   "parent": _name(line["parent"], materials) if line["parent"] else "",
                                   "need": _n(line["need"]), "available": _n(line["available"]), "short": _n(line["gap"]),
                                   "ready": line["ready"], "source": source},
                         "links": {"source": link} if link else {}})
    return {"title": title, "conclusion": labels["conclusion"].format(n=len(lines), at=_short(item["at"])), "at": item["at"],
            "summary": [{"label": labels["bom_materials"], "value": item["bom_materials"]},
                        {"label": labels["short"], "value": len(lines), "tone": HARD},
                        {"label": labels["key_materials"], "value": sum(1 for l in lines if l["key"]), "tone": HARD}],
            "groups": [{"id": g, "label": labels[g], "count": sum(1 for l in lines if l["group"] == g)}
                       for g in GROUPS if any(l["group"] == g for l in lines)],
            "columns": columns, "rows": out_rows, "total": len(chosen)}


def split_lines(value: Any) -> set[str]:
    text = str(value or "")
    for sep in LIST_SEPARATORS[1:]:
        text = text.replace(sep, LIST_SEPARATORS[0])
    return {item.strip() for item in text.split(LIST_SEPARATORS[0]) if item.strip()}


def line_rule(tasks: list[Mapping[str, Any]], *, forecasts: Iterable[Mapping[str, Any]],
              lines: Mapping[str, Mapping[str, Any]], product_lines: Mapping[str, str]) -> list[dict[str, Any]]:
    """Each product of the plan (every product of the bill for a whole bill) must be in the line's product lines.
    A task without a line is not applicable (pass None), as the rule-tool contract asks."""
    forecasts = list(forecasts)
    out = []
    for task in tasks:
        fields = task_fields(task)
        key = fields["key"]
        if fields["status"] == CANCELLED or not fields["line"]:
            # A cancelled plan, or a task not on a line yet (a demand still to schedule): nothing to check.
            out.append({"key": key, "pass": None, "text": "", "related": []})
            continue
        products = sorted({d["product"] for d in demands_of(fields, forecasts)}) or ([fields["product"]] if fields["product"] else [])
        line = lines.get(fields["line"])
        if not products:
            out.append({"key": key, "pass": False, "severity": HARD, "related": [],
                        "text": f"无法检查产线：预测单 {fields['bill'] or '（空）'} 没有未关闭的需求。"})
        elif line is None:
            out.append({"key": key, "pass": False, "severity": HARD, "related": [],
                        "text": f"没有产线 {fields['line'] or '（未指定）'}。"})
        elif line.get("line_kind") != LINE_KIND:
            out.append({"key": key, "pass": False, "severity": HARD, "related": [],
                        "text": f"{line.get('line_name') or fields['line']} 是工厂，不能直接排产，请排到其下的产线。"})
        else:
            allowed = split_lines(line.get("product_lines"))
            wrong = [(p, product_lines.get(p, "")) for p in products if product_lines.get(p, "") not in allowed]
            name = line.get("line_name") or fields["line"]
            if wrong:
                listed = "；".join(f"{p}（{pl or '产品线未知'}）" for p, pl in wrong)
                out.append({"key": key, "pass": False, "severity": HARD, "related": [],
                            "text": f"{name} 只能生产{'、'.join(sorted(allowed)) or '（未设置）'}，不能生产 {listed}。"})
            else:
                out.append({"key": key, "pass": True, "related": [],
                            "text": f"{name} 可生产{'、'.join(sorted({product_lines[p] for p in products}))}。"})
    return out


__all__ = ["CONFIRMED", "overlay", "record", "analyse", "assess", "prepare", "HARD", "MAX_TASKS", "SCHEDULED", "SOFT", "check_tasks", "demands_of", "kit_detail", "kit_rule",
           "line_rule", "split_lines", "task_fields"]
