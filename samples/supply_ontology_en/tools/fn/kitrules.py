"""Schedule rule checks for kit-schedule plans: are materials kitted at the planned start, can the line build it.

Kit check, on one shared pool for all the plans sent:

- the signed backlog of the plans' products is reserved first, in promised-date order (same netting
  as ``demand_coverage``);
- plans then draw in planned-start order (ties by key); a plan uses available stock plus open
  purchase lines due from the business date to its start, without finished goods (it is a
  production plan); overdue lines are not supply;
- a plan short at its start is told the earliest date it could start: the open-purchase arrival
  that closes its gap, or else the business date plus the purchase lead time of the materials that
  nothing on order covers ("no purchase request yet").

A confirmed plan is released to production: its materials are already issued, so it passes and
draws nothing. Severity: starting before that date is hard; when the plan is covered only by materials not yet on
order and the estimate falls on or before its start, it is soft (place the purchase request).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from .planning import DEFAULT_BUSINESS_DATE, Plan, is_open_po

HARD, SOFT = "hard", "soft"
CANCELLED, CONFIRMED = "Cancelled", "Confirmed"
OPEN_FORECAST = "Open"
LINE_KIND = "Line"
LIST_SEPARATORS = (",", ";")
MAX_TASKS = 200


def _d(value: Any) -> Decimal:
    return Decimal(str(value or 0))


def _n(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral_value() else float(round(value, 3))


def _day(value: Any) -> str:
    text = str(value or "").strip()
    if len(text) < 10 or text[4] != "-" or text[7] != "-":
        return ""
    return text[:10]


def _short(day: str) -> str:
    return f"{int(day[5:7])}/{int(day[8:10])}" if day else ""


def _plus(day: str, days: int) -> str:
    return (date.fromisoformat(day) + timedelta(days=days)).isoformat()


def task_fields(task: Mapping[str, Any]) -> dict[str, str]:
    """Forecast number, product (empty = whole bill), line, planned start and status of a task as sent."""
    values = task.get("values") or {}
    return {"key": str(task.get("key") or ""),
            "bill": str(values.get("bill_no") or "").strip(),
            "product": str(values.get("product_code") or "").strip(),
            "line": str(task.get("resource") or values.get("line_code") or "").strip(),
            "start": _day(task.get("start")) or _day(values.get("planned_start")),
            "status": str(values.get("plan_status") or "").strip()}


def check_tasks(tasks: Any) -> list[Mapping[str, Any]]:
    if not isinstance(tasks, list):
        raise ValueError("tasks must be a list of tasks")
    if len(tasks) > MAX_TASKS:
        raise ValueError(f"at most {MAX_TASKS} tasks per call")
    return [t for t in tasks if isinstance(t, Mapping) and t.get("key")]


def demands_of(fields: Mapping[str, str], forecasts: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [{"product": str(r["material_number"]), "qty": r["qty"]} for r in forecasts
            if r.get("billno") == fields["bill"] and r.get("closestatus_title") == OPEN_FORECAST
            and (not fields["product"] or r.get("material_number") == fields["product"])]


def kit_rule(tasks: list[Mapping[str, Any]], rows: Mapping[str, Iterable[Mapping[str, Any]]], *,
             materials: Mapping[str, Mapping[str, Any]], business_date: str = DEFAULT_BUSINESS_DATE) -> list[dict[str, Any]]:
    """One result per task: ``{key, pass, severity, text, related}``; ``pass`` None when not applicable."""
    forecasts = list(rows.get("forecast", ()))
    plan = Plan(rows, business_date=business_date)
    arrivals = sorted(((str(r.get("deliverdate") or "")[:10], str(r["material_number"]), _d(r.get("qty")) - _d(r.get("actqty")),
                        str(r.get("billno") or "")) for r in rows.get("purchase_order", ())
                       if is_open_po(r) and str(r.get("deliverdate") or "")[:10] >= business_date))
    names = {code: str(m.get("material_name") or "") for code, m in materials.items()}

    def lead(code: str) -> int:
        value = _d((materials.get(code) or {}).get("purchase_fixedleadtime"))
        return int(value) if value > 0 else 0

    results: dict[str, dict[str, Any]] = {}
    queue = []
    for task in tasks:
        fields = task_fields(task)
        if fields["status"] == CANCELLED:
            results[fields["key"]] = {"key": fields["key"], "pass": None, "text": "", "related": []}
            continue
        if fields["status"] == CONFIRMED:
            # Released to production: its materials are issued and no longer in stock.
            results[fields["key"]] = {"key": fields["key"], "pass": True, "text": "Released to production; its materials are issued to the work orders.", "related": []}
            continue
        demands = demands_of(fields, forecasts)
        if not fields["bill"] or not fields["start"] or not demands:
            why = "no planned start" if not fields["start"] else f"forecast {fields['bill'] or '(empty)'} has no open demand"
            results[fields["key"]] = {"key": fields["key"], "pass": False, "severity": HARD,
                                      "text": f"Kit not checked: {why}.", "related": []}
            continue
        queue.append((fields, demands))
    if not queue:
        return [results[str(t.get("key"))] for t in tasks if str(t.get("key")) in results]

    pool = plan.pool()
    plan.reserve_backlog(pool, {d["product"] for _, ds in queue for d in ds}, False)
    queue.sort(key=lambda item: (item[0]["start"], item[0]["key"]))
    added = 0
    users: dict[str, list[str]] = defaultdict(list)   # material -> plans that drew it, in order
    arrival_users: dict[tuple, list[str]] = defaultdict(list)

    def allocate(on: dict[str, Decimal], demands: list[dict[str, Any]]) -> dict[str, Decimal]:
        shortages: dict[str, Decimal] = defaultdict(Decimal)
        for demand in demands:
            for code, qty in plan.allocate(on, demand["product"], demand["qty"], use_finished_goods=False)["shortages"].items():
                shortages[code] += _d(qty)
        return shortages

    for fields, demands in queue:
        start, key = fields["start"], fields["key"]
        while added < len(arrivals) and arrivals[added][0] <= start:
            due, code, qty, _po = arrivals[added]
            pool[code] += qty
            added += 1
        before = dict(pool)
        shortages = allocate(pool, demands)
        for code, left in pool.items():
            if left < before.get(code, Decimal(0)):
                users[code].append(key)
        for item in arrivals[:added]:
            if pool[item[1]] < before.get(item[1], Decimal(0)):
                arrival_users[item].append(key)
        if not shortages:
            results[key] = {"key": key, "pass": True, "text": f"Materials are kitted for the planned start {start}.", "related": []}
            continue
        # Earliest start: add the later open-purchase arrivals of this plan's materials day by day on the
        # pool this plan saw; what they never cover needs a new order, estimated by purchase lead time.
        bom = {str(r["material_code"]) for r in plan_rows(rows, demands)}
        later = defaultdict(list)
        for item in arrivals[added:]:
            if item[1] in bom:
                later[item[0]].append(item)
        earliest, remaining, trial = "", dict(shortages), defaultdict(Decimal, before)
        for due in sorted(later):
            for _due, code, qty, _po in later[due]:
                trial[code] += qty
            left = allocate(defaultdict(Decimal, trial), demands)
            if not left:
                earliest = due
                break
            remaining = left
        estimate = ""
        if not earliest:
            estimate = max(_plus(business_date, lead(code)) for code in remaining)
            earliest = max([estimate, *(due for due, items in later.items() if any(i[1] in shortages for i in items))])
        ranked = sorted(shortages.items(), key=lambda kv: (-kv[1], kv[0]))
        parts = []
        for code, qty in ranked[:3]:
            label = f"{names.get(code) or ''} {code}".strip()
            incoming = [a for a in arrivals if a[1] == code]
            if incoming:
                due, _c, got, po = next((a for a in incoming if a[0] > start), incoming[-1])
                taken = [k for (d, c, q, p), ks in arrival_users.items() if c == code for k in ks if k != key]
                note = f"open PO {po} brings {_n(got)} on {_short(due)}" + (f", arrivals before the start already went to {', '.join(dict.fromkeys(taken))}" if taken else "")
            else:
                note = f"no purchase request yet; at the {lead(code)}-day purchase lead time it arrives about {_short(_plus(business_date, lead(code)))}"
            parts.append(f"{label} short {_n(qty)} ({note})")
        more = f", {len(ranked)} materials in all" if len(ranked) > 3 else ""
        related = list(dict.fromkeys(k for code in shortages for k in users.get(code, []) if k != key))
        soft = bool(estimate) and estimate <= start
        tail = (f"Earliest start {earliest}" if earliest else "Open purchases cannot close the gap") + \
               ("; place the purchase request now" if estimate else "")
        results[key] = {"key": key, "pass": False, "severity": SOFT if soft else HARD,
                        "text": f"Short at planned start {start}: {'; '.join(parts)}{more}. {tail}.", "related": related}
    return [results[str(t.get("key"))] for t in tasks if str(t.get("key")) in results]


def plan_rows(rows: Mapping[str, Iterable[Mapping[str, Any]]], demands: list[dict[str, Any]]) -> list[Mapping[str, Any]]:
    products = {d["product"] for d in demands}
    return [r for r in rows.get("bom", ()) if r.get("bom_material_code") in products]


def split_lines(value: Any) -> set[str]:
    text = str(value or "")
    for sep in LIST_SEPARATORS[1:]:
        text = text.replace(sep, LIST_SEPARATORS[0])
    return {item.strip() for item in text.split(LIST_SEPARATORS[0]) if item.strip()}


def line_rule(tasks: list[Mapping[str, Any]], *, forecasts: Iterable[Mapping[str, Any]],
              lines: Mapping[str, Mapping[str, Any]], product_lines: Mapping[str, str]) -> list[dict[str, Any]]:
    """Each product of the plan (every product of the bill for a whole bill) must be in the line's product lines."""
    forecasts = list(forecasts)
    out = []
    for task in tasks:
        fields = task_fields(task)
        key = fields["key"]
        if fields["status"] == CANCELLED:
            out.append({"key": key, "pass": None, "text": "", "related": []})
            continue
        products = sorted({d["product"] for d in demands_of(fields, forecasts)}) or ([fields["product"]] if fields["product"] else [])
        line = lines.get(fields["line"])
        if not products:
            out.append({"key": key, "pass": False, "severity": HARD, "related": [],
                        "text": f"Line not checked: forecast {fields['bill'] or '(empty)'} has no open demand."})
        elif line is None:
            out.append({"key": key, "pass": False, "severity": HARD, "related": [],
                        "text": f"No production line {fields['line'] or '(none given)'}."})
        elif line.get("line_kind") != LINE_KIND:
            out.append({"key": key, "pass": False, "severity": HARD, "related": [],
                        "text": f"{line.get('line_name') or fields['line']} is a plant and cannot be scheduled; use one of its lines."})
        else:
            allowed = split_lines(line.get("product_lines"))
            wrong = [(p, product_lines.get(p, "")) for p in products if product_lines.get(p, "") not in allowed]
            name = line.get("line_name") or fields["line"]
            if wrong:
                listed = "; ".join(f"{p} ({pl or 'unknown product line'})" for p, pl in wrong)
                out.append({"key": key, "pass": False, "severity": HARD, "related": [],
                            "text": f"{name} builds only {', '.join(sorted(allowed)) or '(not set)'} and cannot build {listed}."})
            else:
                out.append({"key": key, "pass": True, "related": [],
                            "text": f"{name} builds {', '.join(sorted({product_lines[p] for p in products}))}."})
    return out


__all__ = ["HARD", "MAX_TASKS", "SOFT", "check_tasks", "kit_rule", "line_rule", "split_lines", "task_fields"]
