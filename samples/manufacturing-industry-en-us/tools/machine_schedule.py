"""Machine-scheduling rules of the manufacturing sample: the network's business rules as rule functions.

Pure calculation on the sample's tables (no I/O); ``schedule_runtime`` reads the tables and calls it.
The same code serves the zh-CN and en-US samples: data values of either language are read through
``CODES``, and the text is written in the locale asked for.

Rule-tool contract (Workshop schedule Gantt, design §5.4):

- check: ``{tasks: [{key, start, end, resource, values}], scenario: {edits}}`` → ``{results: [{key, pass,
  severity, text, related, at?, counts?, detail?}]}``; ``pass`` None when the rule does not apply.
- detail: ``{mode: "detail", task, scenario, locale, query: {group, keyOnly, search, offset, limit}}`` →
  one paged table ``{title, conclusion, at?, summary, groups, columns, rows, total}``.

A task is an operation (``manufacturing_operations``): key = operation_id, resource = machine. Its
day span comes from the planned-date fields it carries, else from ``start``/``end``, else from the
stored plan. Only operations not started yet are checked; completed and running ones only take part
as neighbours (same machine, same work centre, same material).
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

BUSINESS_DATE = "2027-02-28"
ZONE = timezone(timedelta(hours=8))   # both plants are in China; Workshop sends instants
HARD, SOFT = "hard", "soft"
MAX_TASKS = 200
PAGE, MAX_PAGE = 50, 200
RULES = ("work_order_kit", "machine_capability", "operator_shift", "changeover")
START_FIELD, END_FIELD, MACHINE_FIELD = "planned_start_date", "planned_end_date", "planned_machine_id"
MWO_FIELDS = ("planned_start_date", "planned_end_date")

# Displayed values of both sample languages -> code.
CODES = {
    "已完成": "completed", "进行中": "in_progress", "未开始": "not_started", "已计划": "planned",
    "已阻塞": "blocked", "已下达": "released", "生产中": "in_production",
    "合格": "qualified", "暂停": "suspended", "培训中": "in_training",
    "在职": "active", "离职": "left", "已安排": "assigned",
    "已冻结": "frozen", "草稿": "draft", "已停用": "obsolete",
    "原料库": "raw_material", "待检区": "quality_hold", "成品库": "finished_goods",
    "已接受": "accepted", "待检": "pending_inspection", "已拒收": "rejected",
    "已收货": "received", "已确认": "confirmed", "部分收货": "partially_received",
    "可用": "available", "维修中": "under_repair",
}


class CannotCheck(ValueError):
    """The request cannot be answered; the caller marks the tasks not checked."""


def code(value: Any) -> str:
    text = str(value if value is not None else "").strip()
    return CODES.get(text, text)


def num(value: Any) -> Decimal:
    try:
        result = Decimal(str(value if value not in (None, "") else 0))
    except (InvalidOperation, ValueError):
        raise CannotCheck(f"not a number: {value!r}") from None
    if not result.is_finite():
        raise CannotCheck(f"not a number: {value!r}")
    return result


def show(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral_value() else float(round(value, 3))


_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def day(value: Any, *, end: bool = False) -> str:
    """A calendar day ``YYYY-MM-DD`` of a date or an instant; '' when empty.

    A bare date is the day itself. An instant (Workshop sends UTC instants of the page's zone) is
    read on the plants' clock; an end instant is exclusive, so the end of day 03-02 arrives as
    03-03 00:00 and means 03-02.
    """
    if value in (None, ""):
        return ""
    if isinstance(value, datetime):
        moment = value
    elif isinstance(value, date):
        return value.isoformat()
    else:
        text = str(value).strip()
        if _DATE.match(text):
            date.fromisoformat(text)
            return text
        if re.match(r"^\d{4}-\d{2}-\d{2}[T ]00:00:00(\.0+)?$", text):  # a date column read without zone
            return text[:10]
        try:
            moment = datetime.fromisoformat(text.replace("Z", "+00:00").replace(" ", "T", 1))
        except ValueError:
            raise CannotCheck(f"not a date: {value!r}") from None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ZONE)
    moment = moment.astimezone(ZONE)
    if end:
        moment -= timedelta(microseconds=1)
    return moment.date().isoformat()


def plus(text: str, days: int) -> str:
    return (date.fromisoformat(text) + timedelta(days=days)).isoformat()


def short(text: str) -> str:
    return f"{int(text[5:7])}/{text[8:10]}" if text else ""


def overlap(a: tuple[str, str], b: tuple[str, str]) -> bool:
    return a[0] <= b[1] and b[0] <= a[1]


# --- words -------------------------------------------------------------------------------------
WORDS = {
    "zh": {
        "rule.work_order_kit": "工单齐套", "rule.machine_capability": "设备能力", "rule.operator_shift": "人员资质与班次",
        "rule.changeover": "换型提示",
        "na.done": "工序已完成", "na.running": "工序已开工", "na.unknown": "不是工序", "na.not_first": "齐套按工单首道未完成工序检查",
        "kit.ok": "开工 {day} 物料齐套", "kit.bom": "BOM {bom} 为{status}，未冻结", "kit.short": "缺料 {n} 种，关键：{name} 缺 {qty}",
        "kit.at": "，最早 {day} 齐套", "kit.never": "，现有在途补不齐", "kit.nostart": "没有计划开工日",
        "count.short": "缺料物料", "count.overdue": "采购逾期", "count.no_pr": "尚未下采购申请", "count.inspection": "质检未放行",
        "count.reserved": "库存被占用",
        "g.late_po": "在途晚到", "g.overdue_po": "采购逾期", "g.no_pr": "尚未下采购申请", "g.reserved": "库存被占用",
        "g.inspection": "质检未放行", "g.ok": "齐套",
        "c.material": "物料", "c.required": "需求", "c.issued": "已发料", "c.need": "待发", "c.available": "可用", "c.short": "缺口",
        "c.ready": "预计可用", "c.source": "来源单据",
        "s.materials": "BOM 物料", "s.short": "缺料", "s.key": "关键物料", "s.bom": "BOM 版本",
        "kit.title": "{order} · {product} · 计划开工 {day}",
        "cap.ok": "{machine} {cap}能力合格", "cap.bad": "{machine} {cap}能力为{status}", "cap.none": "{machine} 没有{cap}能力",
        "cap.nomachine": "没有指定机台", "cap.unknown": "没有机台 {machine}",
        "cap.title": "{op} · {name} · 需要{cap}",
        "g.qualified": "能力合格", "g.suspended": "能力不合格", "g.no_capability": "无此能力",
        "c.machine": "机台", "c.work_center": "工作中心", "c.capability": "能力状态", "c.machine_status": "设备状态",
        "s.machines": "具备该能力的机台", "s.qualified": "能力合格",
        "op.ok": "{day} 当周{wc}有 {n} 名合格操作员", "op.none": "{day} 当周{wc}没有{cap}合格的操作员",
        "op.noshift": "{day} 当周{site}没有排班", "op.few": "{day} 当周{cap}合格 {n} 人，同时段 {m} 道工序",
        "op.title": "{op} · {wc} · 开工 {day}",
        "g.eligible": "可上岗", "g.expired": "资质过期", "g.unqualified": "资质未合格", "g.not_assigned": "本周未排到此工作中心",
        "g.left": "已离职",
        "c.operator": "操作员", "c.qualification": "资质", "c.valid_to": "有效期至", "c.week": "本周班次",
        "s.eligible": "可上岗", "s.parallel": "同时段工序",
        "chg.ok": "与前一道同为{setup}，无需换型", "chg.first": "机台上没有前一道工序", "chg.change": "换型：前一道 {prev} 为{a}，本道为{b}",
        "detail.na": "不适用：{why}", "none": "无",
    },
    "en": {
        "rule.work_order_kit": "Work order kit", "rule.machine_capability": "Machine capability",
        "rule.operator_shift": "Operator qualification and shift", "rule.changeover": "Changeover",
        "na.done": "operation completed", "na.running": "operation already started", "na.unknown": "not an operation",
        "na.not_first": "the kit is checked on the work order's first open operation",
        "kit.ok": "Material complete for start {day}", "kit.bom": "BOM {bom} is {status}, not frozen",
        "kit.short": "Short of {n} material(s), key: {name} short {qty}", "kit.at": "; complete from {day}",
        "kit.never": "; incoming orders do not cover it", "kit.nostart": "no planned start",
        "count.short": "Materials short", "count.overdue": "Purchase overdue", "count.no_pr": "No purchase request yet",
        "count.inspection": "Awaiting inspection", "count.reserved": "Stock taken",
        "g.late_po": "Arrives late", "g.overdue_po": "Purchase overdue", "g.no_pr": "No purchase request yet",
        "g.reserved": "Stock taken by others", "g.inspection": "Awaiting inspection", "g.ok": "Complete",
        "c.material": "Material", "c.required": "Required", "c.issued": "Issued", "c.need": "To issue", "c.available": "Available",
        "c.short": "Short", "c.ready": "Available from", "c.source": "Source document",
        "s.materials": "BOM materials", "s.short": "Short", "s.key": "Key materials", "s.bom": "BOM revision",
        "kit.title": "{order} · {product} · planned start {day}",
        "cap.ok": "{machine}: {cap} qualified", "cap.bad": "{machine}: {cap} is {status}", "cap.none": "{machine} has no {cap} capability",
        "cap.nomachine": "No machine assigned", "cap.unknown": "No machine {machine}",
        "cap.title": "{op} · {name} · needs {cap}",
        "g.qualified": "Qualified", "g.suspended": "Not qualified", "g.no_capability": "No such capability",
        "c.machine": "Machine", "c.work_center": "Work centre", "c.capability": "Capability status", "c.machine_status": "Machine status",
        "s.machines": "Machines with the capability", "s.qualified": "Qualified",
        "op.ok": "Week of {day}: {n} qualified operators at {wc}", "op.none": "Week of {day}: no operator qualified for {cap} at {wc}",
        "op.noshift": "Week of {day}: no shift at {site}", "op.few": "Week of {day}: {n} qualified for {cap}, {m} operations at once",
        "op.title": "{op} · {wc} · start {day}",
        "g.eligible": "Can work", "g.expired": "Qualification expired", "g.unqualified": "Not qualified yet",
        "g.not_assigned": "Not rostered here this week", "g.left": "Left",
        "c.operator": "Operator", "c.qualification": "Qualification", "c.valid_to": "Valid to", "c.week": "This week's shift",
        "s.eligible": "Can work", "s.parallel": "Operations at once",
        "chg.ok": "Same setup as the previous operation ({setup})", "chg.first": "No earlier operation on the machine",
        "chg.change": "Changeover: previous {prev} is {a}, this one {b}",
        "detail.na": "Not applicable: {why}", "none": "none",
    },
}


def lang_of(locale: Any, default: str) -> str:
    text = str(locale or "").lower()
    return "zh" if text.startswith("zh") else ("en" if text.startswith("en") else default)


# --- facts -------------------------------------------------------------------------------------
class Facts:
    """The sample's tables, indexed, with the scenario's edits applied to the plan."""

    def __init__(self, tables: Mapping[str, Iterable[Mapping[str, Any]]], *, language: str,
                 business_date: str = BUSINESS_DATE):
        t = {name: [dict(r) for r in rows] for name, rows in tables.items()}
        self.tables, self.language, self.business_date = t, language, business_date
        self.ops = {r["operation_id"]: r for r in t.get("manufacturing_operations", [])}
        self.steps = {r["operation_id"]: r for r in t.get("process_steps", [])}
        self.orders = {r["production_order_id"]: r for r in t.get("production_orders", [])}
        self.machines = {r["machine_id"]: r for r in t.get("production_machines", [])}
        self.caps = {r["capability_id"]: r for r in t.get("equipment_capabilities", [])}
        self.centres = {r["work_center_id"]: r for r in t.get("work_centers", [])}
        self.products = {r["product_id"]: r for r in t.get("products", [])}
        self.sites = {r["site_id"]: r for r in t.get("manufacturing_sites", [])}
        self.operators = {r["operator_id"]: r for r in t.get("operators", [])}
        self.plan = {key: (str(r.get(MACHINE_FIELD) or ""), day(r.get(START_FIELD)), day(r.get(END_FIELD)))
                     for key, r in self.ops.items()}

    def words(self, lang: str) -> dict[str, str]:
        return WORDS[lang]

    def apply_edits(self, scenario: Any) -> None:
        """Scenario edits that set an operation's planned fields move it in the plan."""
        edits = (scenario or {}).get("edits") if isinstance(scenario, Mapping) else None
        for edit in edits or []:
            if not isinstance(edit, Mapping) or str(edit.get("key") or "") not in self.ops:
                continue
            params = edit.get("params") if isinstance(edit.get("params"), Mapping) else {}
            self.move(str(edit["key"]), params.get(MACHINE_FIELD), params.get(START_FIELD), params.get(END_FIELD))

    def move(self, key: str, machine: Any = None, start: Any = None, end: Any = None, *, end_instant: bool = False) -> None:
        old = self.plan[key]
        self.plan[key] = (str(machine).strip() if machine not in (None, "") else old[0],
                          day(start) if start not in (None, "") else old[1],
                          day(end, end=end_instant) if end not in (None, "") else old[2])

    def task_op(self, task: Mapping[str, Any]) -> str:
        key = str(task.get("key") or "")
        values = task.get("values") if isinstance(task.get("values"), Mapping) else {}
        if key in self.ops:
            return key
        other = str(values.get("operation_id") or "")
        return other if other in self.ops else ""

    def take(self, task: Mapping[str, Any]) -> str:
        """Put a task's position into the plan; returns its operation ID ('' if not an operation)."""
        op = self.task_op(task)
        if not op:
            return ""
        values = task.get("values") if isinstance(task.get("values"), Mapping) else {}
        start = values.get(START_FIELD) if values.get(START_FIELD) not in (None, "") else task.get("start")
        if values.get(END_FIELD) not in (None, ""):
            end, instant = values.get(END_FIELD), False
        else:
            end, instant = task.get("end"), bool(task.get("end")) and not _DATE.match(str(task.get("end")).strip())
        machine = task.get("resource") if task.get("resource") not in (None, "") else values.get(MACHINE_FIELD)
        self.move(op, machine, start, end, end_instant=instant)
        machine, s, e = self.plan[op]
        if s and not e:
            self.plan[op] = (machine, s, plus(s, int(num(self.ops[op].get("standard_duration_days") or 1)) - 1))
        elif s and e < s:
            raise CannotCheck(f"{op}: end {e} is before start {s}")
        return op

    def state(self, op: str) -> str:
        return code(self.ops[op].get("status"))

    def open_ops(self) -> list[str]:
        return sorted(k for k in self.ops if self.state(k) != "completed")

    def name(self, kind: str, key: str) -> str:
        if kind == "machine":
            return str(self.machines.get(key, {}).get("machine_name") or key)
        if kind == "cap":
            return str(self.caps.get(key, {}).get("capability_name") or key)
        if kind == "wc":
            return str(self.centres.get(key, {}).get("work_center_name") or key)
        if kind == "product":
            return str(self.products.get(key, {}).get("product_name") or key)
        if kind == "operator":
            return str(self.operators.get(key, {}).get("operator_name") or key)
        if kind == "site":
            return str(self.sites.get(key, {}).get("site_name") or key)
        return key


def not_applicable(facts: Facts, op: str, kit: bool = False) -> str | None:
    """Why an operation is not checked, as a word key; None when it is."""
    if not op:
        return "na.unknown"
    state = facts.state(op)
    if state == "completed":
        return "na.done"
    if state == "in_progress":
        return "na.running"
    return None


def result(key: str, passed: bool | None, text: str = "", *, severity: str | None = None, related: Iterable[str] = (),
           at: str = "", counts: list[dict[str, Any]] | None = None, detail: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {"key": key, "pass": passed, "text": text, "related": list(dict.fromkeys(r for r in related if r != key))}
    if passed is False:
        out["severity"] = severity or HARD
    if at:
        out["at"] = at
    if counts:
        out["counts"] = counts[:4]
    if detail:
        out["detail"] = True
    return out


# --- work order kit ------------------------------------------------------------------------------
class Kit:
    """Material of every open work order, allocated in the order of its first open operation's start."""

    def __init__(self, facts: Facts):
        self.f = f = facts
        t = f.tables
        by_order = defaultdict(list)
        for op in f.ops.values():
            by_order[op["production_order_id"]].append(op)
        self.first: dict[str, str] = {}
        for order, ops in by_order.items():
            if code(f.orders.get(order, {}).get("status")) == "completed":
                continue
            open_ops = sorted((o for o in ops if code(o.get("status")) != "completed"), key=lambda o: int(num(o.get("sequence_number"))))
            if open_ops:
                self.first[order] = open_ops[0]["operation_id"]
        self.need: dict[str, dict[str, Decimal]] = defaultdict(dict)
        self.required: dict[str, dict[str, Decimal]] = defaultdict(dict)
        self.issued: dict[str, dict[str, Decimal]] = defaultdict(dict)
        for req in t.get("production_order_material_requirements", []):
            order = req["production_order_id"]
            if order not in self.first:
                continue
            material = req["product_id"]
            required, issued = num(req.get("required_quantity")), num(req.get("issued_quantity"))
            self.required[order][material] = self.required[order].get(material, Decimal(0)) + required
            self.issued[order][material] = self.issued[order].get(material, Decimal(0)) + issued
            self.need[order][material] = max(self.required[order][material] - self.issued[order][material], Decimal(0))
        versions = {v["bom_version_id"]: v for v in t.get("product_bom_versions", [])}
        self.bom = {o: versions.get(f.orders[o].get("bom_version_id"), {}) for o in self.first}
        hold = {l["inventory_location_id"] for l in t.get("inventory_locations", []) if code(l.get("location_type")) == "quality_hold"}
        self.stock: dict[str, Decimal] = defaultdict(Decimal)
        self.held: dict[str, Decimal] = defaultdict(Decimal)
        for b in t.get("inventory_balances", []):
            if b["inventory_location_id"] in hold:
                self.held[b["product_id"]] += num(b.get("on_hand_quantity"))
            else:
                self.stock[b["product_id"]] += max(num(b.get("on_hand_quantity")) - num(b.get("allocated_quantity")), Decimal(0))
        pos = {p["purchase_order_id"]: p for p in t.get("purchase_orders", [])}
        received: dict[str, Decimal] = defaultdict(Decimal)
        for g in t.get("goods_receipts", []):
            if code(g.get("inspection_status")) != "rejected":
                received[g["purchase_order_line_id"]] += num(g.get("received_quantity"))
        self.arrivals: list[tuple[str, str, Decimal, str]] = []   # (expected day, material, open qty, purchase order)
        self.overdue: dict[str, list[str]] = defaultdict(list)
        for line in t.get("purchase_order_lines", []):
            po = pos.get(line["purchase_order_id"], {})
            left = num(line.get("ordered_quantity")) - received[line["purchase_order_line_id"]]
            if left <= 0 or code(po.get("status")) == "received":
                continue
            expected = day(po.get("expected_receipt_date"))
            if expected and expected < f.business_date:
                self.overdue[line["product_id"]].append(line["purchase_order_id"])
            else:
                self.arrivals.append((expected, line["product_id"], left, line["purchase_order_id"]))
        self.arrivals.sort()

    def frozen(self, order: str) -> bool:
        return code(self.bom[order].get("status")) == "frozen"

    def run(self) -> dict[str, dict[str, Any]]:
        """Allocate; per open work order its start day, queue position and per-material outcome."""
        f = self.f
        queue = sorted(self.first, key=lambda o: (f.plan[self.first[o]][1] or "9999", o))
        pool = defaultdict(Decimal, self.stock)
        added = 0
        out = {}
        for position, order in enumerate(queue):
            start = f.plan[self.first[order]][1]
            while added < len(self.arrivals) and start and self.arrivals[added][0] <= start:
                pool[self.arrivals[added][1]] += self.arrivals[added][2]
                added += 1
            before = dict(pool)
            materials = {}
            for material, need in sorted(self.need[order].items()):
                take = min(pool[material], need)
                if self.frozen(order):
                    pool[material] -= take
                materials[material] = {"need": need, "available": take, "short": need - take,
                                       "alone": min(self.stock[material] + sum(a[2] for a in self.arrivals if a[1] == material and a[0] <= (start or "")), need)}
            out[order] = {"order": order, "op": self.first[order], "start": start, "position": position,
                          "before": before, "materials": materials, "added": added}
        for order, item in out.items():
            item["at"], item["ready"] = self.earliest(item)
        return out

    def earliest(self, item: Mapping[str, Any]) -> tuple[str, dict[str, str]]:
        """The first day later incoming orders cover every shortage, on the stock this order saw; '' if never."""
        ready: dict[str, str] = {}
        at = item["start"]
        for material, m in item["materials"].items():
            if m["short"] <= 0:
                continue
            left, when = m["short"], ""
            for expected, mat, qty, _po in self.arrivals[item["added"]:]:
                if mat == material:
                    left -= qty
                    if left <= 0:
                        when = expected
                        break
            ready[material] = when
            at = max(at, when) if when and at else (when or at)
            if not when:
                at = ""
        if any(not w for w in ready.values()):
            at = ""
        return at, ready


def _order_label(f: Facts, order: str) -> str:
    return f.name("product", str(f.orders.get(order, {}).get("product_id") or ""))


def _qty(f: Facts, material: str, value: Decimal) -> str:
    unit = str(f.products.get(material, {}).get("base_unit") or "")
    return f"{show(value)}{(' ' + unit) if unit and f.language == 'en' else unit}"


def kit_outcome(f: Facts, kit_run: Mapping[str, Mapping[str, Any]], kit: Kit, order: str, lang: str) -> dict[str, Any]:
    W = WORDS[lang]
    item = kit_run[order]
    shorts = {m: v for m, v in item["materials"].items() if v["short"] > 0}
    bom_ok = kit.frozen(order)
    groups = {m: material_group(kit, item, m) for m in item["materials"]}
    parts = []
    if not bom_ok:
        bom = kit.bom[order]
        parts.append(W["kit.bom"].format(bom=bom.get("bom_version_id") or "?", status=bom.get("status") or "?"))
    if shorts:
        key = max(shorts, key=lambda m: ((item["ready"].get(m) or "9999"), shorts[m]["short"], m))
        parts.append(W["kit.short"].format(n=len(shorts), name=f.name("product", key), qty=_qty(f, key, shorts[key]["short"])))
        parts[-1] += W["kit.at"].format(day=short(item["at"])) if item["at"] else W["kit.never"]
    counts = []
    if shorts:
        counts.append({"label": W["count.short"], "value": len(shorts)})
        for g, label in (("overdue_po", "count.overdue"), ("no_pr", "count.no_pr"), ("reserved", "count.reserved"), ("inspection", "count.inspection")):
            n = sum(1 for m in shorts if groups[m] == g)
            if n:
                counts.append({"label": W[label], "value": n})
    passed = bom_ok and not shorts
    text = W["kit.ok"].format(day=short(item["start"])) if passed else ("；" if lang == "zh" else "; ").join(parts)
    return {"pass": passed, "text": text, "at": "" if passed or not bom_ok else item["at"], "counts": counts, "groups": groups}


def material_group(kit: Kit, item: Mapping[str, Any], material: str) -> str:
    m = item["materials"][material]
    if m["short"] <= 0:
        return "ok"
    if m["alone"] >= m["need"]:
        return "reserved"
    if item["ready"].get(material):
        return "late_po"
    if kit.overdue.get(material):
        return "overdue_po"
    if kit.held.get(material, 0) > 0:
        return "inspection"
    return "no_pr"


def check_kit(f: Facts, tasks: list[Mapping[str, Any]], lang: str) -> list[dict[str, Any]]:
    kit = Kit(f)
    runs = kit.run()
    carriers = {item["op"]: order for order, item in runs.items()}
    sharing: dict[str, set[str]] = defaultdict(set)
    for order in runs:
        for material, need in kit.need[order].items():
            if need > 0:
                sharing[material].add(order)
    out = []
    for task in tasks:
        key, op = str(task["key"]), f.task_op(task)
        why = not_applicable(f, op)
        if why or op not in carriers:
            out.append(result(key, None, WORDS[lang]["detail.na"].format(why=WORDS[lang][why or "na.not_first"])))
            continue
        order = carriers[op]
        item = runs[order]
        if not item["start"]:
            out.append(result(key, False, WORDS[lang]["kit.nostart"]))
            continue
        outcome = kit_outcome(f, runs, kit, order, lang)
        related = sorted({runs[o]["op"] for m, need in kit.need[order].items() if need > 0 for o in sharing[m] if o != order},
                         key=lambda o: (f.plan[o][1], o))
        out.append(result(key, outcome["pass"], outcome["text"], related=related, at=outcome["at"],
                          counts=outcome["counts"], detail=True))
    return out


def detail_kit(f: Facts, op: str, lang: str) -> dict[str, Any]:
    W = WORDS[lang]
    kit = Kit(f)
    runs = kit.run()
    order = next((o for o, item in runs.items() if item["op"] == op), None)
    if order is None:
        return {}
    item = runs[order]
    outcome = kit_outcome(f, runs, kit, order, lang)
    rows = []
    for material, m in item["materials"].items():
        group = outcome["groups"][material]
        incoming = [a for a in kit.arrivals if a[1] == material]
        source = (kit.overdue.get(material) or [None])[0] if group == "overdue_po" else \
            next((a[3] for a in incoming if a[0] == item["ready"].get(material)), None) or \
            next((a[3] for a in incoming if a[0] <= item["start"]), None)
        ready = "" if m["short"] > 0 and not item["ready"].get(material) else (item["ready"].get(material) or item["start"])
        row = {"id": material, "group": group, "key": bool(m["short"] > 0 and (not item["at"] or item["ready"].get(material) == item["at"])),
               "cells": {"material": f"{f.name('product', material)} {material}", "required": show(kit.required[order][material]),
                         "issued": show(kit.issued[order][material]), "need": show(m["need"]), "available": show(m["available"]),
                         "short": show(m["short"]), "ready": ready, "source": source or ""},
               "links": {"material": {"objectType": "products", "key": material}}}
        if source:
            row["links"]["source"] = {"objectType": "purchase_orders", "key": source}
        rows.append(row)
    for material in kit.required[order]:
        if material not in item["materials"]:
            rows.append({"id": material, "group": "ok", "key": False,
                         "cells": {"material": f"{f.name('product', material)} {material}", "required": show(kit.required[order][material]),
                                   "issued": show(kit.issued[order][material]), "need": 0, "available": 0, "short": 0, "ready": "", "source": ""},
                         "links": {"material": {"objectType": "products", "key": material}}})
    rows.sort(key=lambda r: (r["cells"]["short"] <= 0, r["cells"]["ready"] != "" if r["cells"]["short"] > 0 else True,
                             _neg(r["cells"]["ready"]), -r["cells"]["short"], r["id"]))
    shorts = [r for r in rows if r["cells"]["short"] > 0]
    summary = [{"label": W["s.materials"], "value": len(rows)},
               {"label": W["s.short"], "value": len(shorts), **({"tone": HARD} if shorts else {})},
               {"label": W["s.key"], "value": sum(1 for r in rows if r["key"]), **({"tone": HARD} if shorts else {})}]
    if not kit.frozen(order):
        summary.append({"label": W["s.bom"], "value": str(kit.bom[order].get("bom_version_id") or ""), "tone": HARD})
    return {"title": W["kit.title"].format(order=order, product=_order_label(f, order), day=short(item["start"])),
            "conclusion": outcome["text"], "at": outcome["at"], "summary": summary,
            "groups": _groups(rows, ("late_po", "overdue_po", "no_pr", "reserved", "inspection", "ok"), W),
            "columns": [{"key": "material", "label": W["c.material"], "type": "text"},
                        {"key": "required", "label": W["c.required"], "type": "number"},
                        {"key": "issued", "label": W["c.issued"], "type": "number"},
                        {"key": "need", "label": W["c.need"], "type": "number"},
                        {"key": "available", "label": W["c.available"], "type": "number"},
                        {"key": "short", "label": W["c.short"], "type": "number"},
                        {"key": "ready", "label": W["c.ready"], "type": "date"},
                        {"key": "source", "label": W["c.source"], "type": "link"}],
            "rows": rows}


def _neg(text: str) -> str:
    """Sort key putting later days first."""
    return "".join(chr(0x10FFFF - ord(c)) for c in text) if text else ""


def _groups(rows: list[Mapping[str, Any]], order: Iterable[str], W: Mapping[str, str]) -> list[dict[str, Any]]:
    counts = defaultdict(int)
    for r in rows:
        counts[r["group"]] += 1
    return [{"id": g, "label": W["g." + g], "count": counts[g]} for g in order if counts[g]]


# --- machine capability ----------------------------------------------------------------------------
def _capability(f: Facts, machine: str, cap: str) -> str:
    """'qualified', another status code, or '' when the machine has no assignment for the capability."""
    rows = [a for a in f.tables.get("machine_capability_assignments", []) if a["machine_id"] == machine and a["capability_id"] == cap]
    if not rows:
        return ""
    statuses = {code(a.get("qualification_status")) for a in rows}
    return "qualified" if "qualified" in statuses else sorted(statuses)[0]


def _status_text(f: Facts, machine: str, cap: str) -> str:
    rows = [a for a in f.tables.get("machine_capability_assignments", []) if a["machine_id"] == machine and a["capability_id"] == cap]
    return str(rows[0].get("qualification_status") or "") if rows else ""


def check_capability(f: Facts, tasks: list[Mapping[str, Any]], lang: str) -> list[dict[str, Any]]:
    W = WORDS[lang]
    out = []
    for task in tasks:
        key, op = str(task["key"]), f.task_op(task)
        why = not_applicable(f, op)
        if why:
            out.append(result(key, None, W["detail.na"].format(why=W[why])))
            continue
        machine = f.plan[op][0]
        cap = str(f.steps.get(op, {}).get("required_capability_id") or "")
        if not machine:
            out.append(result(key, False, W["cap.nomachine"], detail=True))
        elif machine not in f.machines:
            out.append(result(key, False, W["cap.unknown"].format(machine=machine), detail=True))
        else:
            status = _capability(f, machine, cap)
            names = dict(machine=f.name("machine", machine), cap=f.name("cap", cap))
            if status == "qualified":
                out.append(result(key, True, W["cap.ok"].format(**names), detail=True))
            elif status:
                out.append(result(key, False, W["cap.bad"].format(status=_status_text(f, machine, cap), **names), detail=True))
            else:
                out.append(result(key, False, W["cap.none"].format(**names), detail=True))
    return out


def detail_capability(f: Facts, op: str, lang: str) -> dict[str, Any]:
    W = WORDS[lang]
    machine = f.plan[op][0]
    cap = str(f.steps.get(op, {}).get("required_capability_id") or "")
    verdict = check_capability(f, [{"key": op}], lang)[0]
    candidates = {a["machine_id"] for a in f.tables.get("machine_capability_assignments", []) if a["capability_id"] == cap}
    if machine:
        candidates.add(machine)
    rows = []
    for m in sorted(candidates):
        status = _capability(f, m, cap)
        info = f.machines.get(m, {})
        rows.append({"id": m, "group": "qualified" if status == "qualified" else ("suspended" if status else "no_capability"),
                     "key": m == machine,
                     "cells": {"machine": f"{f.name('machine', m)} {m}", "work_center": f.name("wc", str(info.get("work_center_id") or "")),
                               "capability": _status_text(f, m, cap) or W["none"], "machine_status": str(info.get("status") or "")},
                     "links": {"machine": {"objectType": "production_machines", "key": m}}})
    rows.sort(key=lambda r: (not r["key"], r["group"] != "qualified", r["id"]))
    return {"title": W["cap.title"].format(op=op, name=f.ops[op].get("operation_name") or "", cap=f.name("cap", cap)),
            "conclusion": verdict["text"], "summary": [
                {"label": W["s.machines"], "value": sum(1 for r in rows if r["group"] != "no_capability")},
                {"label": W["s.qualified"], "value": sum(1 for r in rows if r["group"] == "qualified")}],
            "groups": _groups(rows, ("qualified", "suspended", "no_capability"), W),
            "columns": [{"key": "machine", "label": W["c.machine"], "type": "text"},
                        {"key": "work_center", "label": W["c.work_center"], "type": "text"},
                        {"key": "capability", "label": W["c.capability"], "type": "text"},
                        {"key": "machine_status", "label": W["c.machine_status"], "type": "text"}],
            "rows": rows}


# --- operator qualification and shift ----------------------------------------------------------------
def _roster(f: Facts, op: str) -> dict[str, Any]:
    _machine, start, end = f.plan[op]
    wc = str(f.ops[op].get("work_center_id") or "")
    site = str(f.centres.get(wc, {}).get("site_id") or "")
    cap = str(f.steps.get(op, {}).get("required_capability_id") or "")
    shifts = [s for s in f.tables.get("shifts", []) if s["site_id"] == site and day(s.get("starts_date")) <= start <= day(s.get("ends_date"))]
    shift_ids = {s["shift_id"] for s in shifts}
    week = min((day(s.get("starts_date")) for s in shifts), default=start)
    assigned: dict[str, set[str]] = defaultdict(set)   # operator -> work centres this week
    for a in f.tables.get("operator_shift_assignments", []):
        if a["shift_id"] in shift_ids and code(a.get("assignment_status")) == "assigned":
            assigned[a["operator_id"]].add(a["work_center_id"])
    quals = defaultdict(list)
    for q in f.tables.get("operator_qualifications", []):
        if q["capability_id"] == cap:
            quals[q["operator_id"]].append(q)
    people = {}
    for person in sorted(set(quals) | {p for p, wcs in assigned.items() if wc in wcs}):
        qual = max(quals.get(person, []), key=lambda q: (code(q.get("qualification_status")) == "qualified", day(q.get("valid_to"))), default=None)
        valid_to = day(qual.get("valid_to")) if qual else ""
        if code(f.operators.get(person, {}).get("employment_status")) == "left":
            group = "left"
        elif not qual or code(qual.get("qualification_status")) != "qualified":
            group = "unqualified"
        elif valid_to < start:
            group = "expired"
        elif wc not in assigned.get(person, set()):
            group = "not_assigned"
        else:
            group = "eligible"
        people[person] = {"group": group, "qual": qual, "valid_to": valid_to, "week": sorted(assigned.get(person, set()))}
    # Operations at the work centre on the busiest day of this one's span, besides itself.
    others = [o for o in f.ops if o != op and f.state(o) != "completed" and str(f.ops[o].get("work_center_id")) == wc and f.plan[o][1]]
    parallel: list[str] = []
    d = start
    while d and d <= (end or start):
        busy = sorted(o for o in others if overlap((d, d), (f.plan[o][1], f.plan[o][2] or f.plan[o][1])))
        if len(busy) > len(parallel):
            parallel = busy
        d = plus(d, 1)
    return {"wc": wc, "site": site, "cap": cap, "start": start, "week": week, "shifts": shifts, "people": people,
            "eligible": [p for p, v in people.items() if v["group"] == "eligible"], "parallel": parallel}


def _operator_verdict(f: Facts, op: str, lang: str) -> tuple[bool, str, str, list[str], dict[str, Any]]:
    W = WORDS[lang]
    r = _roster(f, op)
    names = dict(day=short(r["week"]), wc=f.name("wc", r["wc"]), cap=f.name("cap", r["cap"]), site=f.name("site", r["site"]))
    if not r["shifts"]:
        return False, HARD, W["op.noshift"].format(**names), [], r
    if not r["eligible"]:
        return False, HARD, W["op.none"].format(**names), [], r
    if len(r["eligible"]) < 1 + len(r["parallel"]):
        return False, SOFT, W["op.few"].format(n=len(r["eligible"]), m=1 + len(r["parallel"]), **names), r["parallel"], r
    return True, "", W["op.ok"].format(n=len(r["eligible"]), **names), r["parallel"], r


def check_operator(f: Facts, tasks: list[Mapping[str, Any]], lang: str) -> list[dict[str, Any]]:
    W = WORDS[lang]
    out = []
    for task in tasks:
        key, op = str(task["key"]), f.task_op(task)
        why = not_applicable(f, op)
        if why:
            out.append(result(key, None, W["detail.na"].format(why=W[why])))
            continue
        if not f.plan[op][1]:
            out.append(result(key, False, W["kit.nostart"]))
            continue
        passed, severity, text, related, r = _operator_verdict(f, op, lang)
        counts = [{"label": W["s.eligible"], "value": len(r["eligible"])}, {"label": W["s.parallel"], "value": 1 + len(r["parallel"])}]
        out.append(result(key, passed, text, severity=severity, related=related, counts=counts, detail=True))
    return out


def detail_operator(f: Facts, op: str, lang: str) -> dict[str, Any]:
    W = WORDS[lang]
    passed, severity, text, related, r = _operator_verdict(f, op, lang)
    rows = []
    for person, v in r["people"].items():
        qual = v["qual"] or {}
        rows.append({"id": person, "group": v["group"], "key": v["group"] == "eligible",
                     "cells": {"operator": f"{f.name('operator', person)} {person}",
                               "qualification": str(qual.get("qualification_status") or W["none"]), "valid_to": v["valid_to"],
                               "week": "、".join(f.name("wc", w) for w in v["week"]) if lang == "zh" else ", ".join(f.name("wc", w) for w in v["week"])},
                     "links": {"operator": {"objectType": "operators", "key": person}}})
    order = ("eligible", "not_assigned", "expired", "unqualified", "left")
    rows.sort(key=lambda x: (order.index(x["group"]), x["id"]))
    summary = [{"label": W["s.eligible"], "value": len(r["eligible"]), **({"tone": severity} if not passed else {})},
               {"label": W["s.parallel"], "value": 1 + len(r["parallel"])}]
    sep = "、" if lang == "zh" else ", "
    conclusion = text + (("（" + sep.join(related) + "）") if related and lang == "zh" else ((" (" + sep.join(related) + ")") if related else ""))
    return {"title": W["op.title"].format(op=op, wc=f.name("wc", r["wc"]), day=short(r["start"])), "conclusion": conclusion,
            "summary": summary, "groups": _groups(rows, order, W),
            "columns": [{"key": "operator", "label": W["c.operator"], "type": "text"},
                        {"key": "qualification", "label": W["c.qualification"], "type": "text"},
                        {"key": "valid_to", "label": W["c.valid_to"], "type": "date"},
                        {"key": "week", "label": W["c.week"], "type": "text"}],
            "rows": rows}


# --- changeover ------------------------------------------------------------------------------------
def check_changeover(f: Facts, tasks: list[Mapping[str, Any]], lang: str) -> list[dict[str, Any]]:
    W = WORDS[lang]
    lines: dict[str, list[str]] = defaultdict(list)
    for o, (machine, start, _end) in f.plan.items():
        if machine and start:
            lines[machine].append(o)
    for ops in lines.values():
        ops.sort(key=lambda o: (f.plan[o][1], f.plan[o][2], o))
    out = []
    for task in tasks:
        key, op = str(task["key"]), f.task_op(task)
        why = not_applicable(f, op)
        if why:
            out.append(result(key, None, W["detail.na"].format(why=W[why])))
            continue
        line = lines.get(f.plan[op][0], [])
        if op not in line:
            out.append(result(key, None, W["cap.nomachine"]))
            continue
        at = line.index(op)
        prev = line[at - 1] if at else ""
        after = line[at + 1] if at + 1 < len(line) else ""
        setup = lambda o: str(f.steps.get(o, {}).get("setup_class") or "")
        if not prev:
            out.append(result(key, True, W["chg.first"], related=[after] if after else []))
        elif setup(prev) == setup(op):
            out.append(result(key, True, W["chg.ok"].format(setup=setup(op)), related=[x for x in (prev, after) if x]))
        else:
            out.append(result(key, False, W["chg.change"].format(prev=prev, a=setup(prev), b=setup(op)), severity=SOFT,
                              related=[x for x in (prev, after) if x]))
    return out


CHECKS = {"work_order_kit": check_kit, "machine_capability": check_capability, "operator_shift": check_operator,
          "changeover": check_changeover}
DETAILS = {"work_order_kit": detail_kit, "machine_capability": detail_capability, "operator_shift": detail_operator}
# Tables each rule reads.
NEEDS = {
    "base": ("manufacturing_operations", "process_steps", "production_orders"),
    "work_order_kit": ("production_order_material_requirements", "product_bom_versions", "inventory_balances", "inventory_locations",
                       "purchase_order_lines", "purchase_orders", "goods_receipts", "products"),
    "machine_capability": ("production_machines", "machine_capability_assignments", "equipment_capabilities", "work_centers"),
    "operator_shift": ("work_centers", "manufacturing_sites", "shifts", "operator_shift_assignments", "operator_qualifications",
                       "operators", "equipment_capabilities"),
    "changeover": (),
}


def tables_for(rule: str) -> tuple[str, ...]:
    if rule not in CHECKS:
        raise CannotCheck(f"unknown rule {rule!r}")
    return tuple(dict.fromkeys(NEEDS["base"] + NEEDS[rule]))


def check(rule: str, tables: Mapping[str, Iterable[Mapping[str, Any]]], tasks: Any, scenario: Any = None, *,
          language: str, locale: Any = None) -> dict[str, Any]:
    """Batch check: one result per task sent; an empty list checks every open operation."""
    tables_for(rule)
    if tasks is None:
        tasks = []
    if not isinstance(tasks, list):
        raise CannotCheck("tasks must be a list")
    if len(tasks) > MAX_TASKS:
        raise CannotCheck(f"at most {MAX_TASKS} tasks per call")
    f = Facts(tables, language=language)
    f.apply_edits(scenario)
    sent = []
    for task in tasks:
        if isinstance(task, str):
            task = {"key": task}
        if not isinstance(task, Mapping) or task.get("key") in (None, ""):
            continue
        f.take(task)
        sent.append(task)
    if not tasks:
        sent = [{"key": o} for o in f.open_ops() if f.state(o) == "not_started"]
    return {"results": CHECKS[rule](f, sent, lang_of(locale, language))}


def detail(rule: str, tables: Mapping[str, Iterable[Mapping[str, Any]]], task: Any, scenario: Any = None, *,
           language: str, locale: Any = None, query: Any = None) -> dict[str, Any]:
    """One task's paged table: rows sorted by the function, filtered by group, key-only and search."""
    tables_for(rule)
    lang = lang_of(locale, language)
    W = WORDS[lang]
    if isinstance(task, str):
        task = {"key": task}
    if not isinstance(task, Mapping) or task.get("key") in (None, ""):
        raise CannotCheck("detail needs one task with a key")
    f = Facts(tables, language=language)
    f.apply_edits(scenario)
    op = f.take(task)
    why = not_applicable(f, op)
    body: dict[str, Any] = {}
    if not why and rule in DETAILS:
        body = DETAILS[rule](f, op, lang)
        if not body and rule == "work_order_kit":
            why = "na.not_first"
    if why or not body:
        return {"title": str(task.get("key")), "conclusion": W["detail.na"].format(why=W[why or "na.unknown"]),
                "summary": [], "groups": [], "columns": [], "rows": [], "total": 0}
    q = query if isinstance(query, Mapping) else {}
    rows = body["rows"]
    if q.get("group"):
        rows = [r for r in rows if r["group"] == q["group"]]
    if q.get("keyOnly"):
        rows = [r for r in rows if r["key"]]
    if q.get("search"):
        needle = str(q["search"]).lower()
        rows = [r for r in rows if needle in r["id"].lower() or any(needle in str(v).lower() for v in r["cells"].values())]
    try:
        offset = max(int(q.get("offset") or 0), 0)
        limit = min(max(int(q.get("limit") or PAGE), 1), MAX_PAGE)
    except (TypeError, ValueError):
        raise CannotCheck("offset and limit must be integers") from None
    body = {k: v for k, v in body.items() if v not in ("", None)}
    body["total"] = len(rows)
    body["rows"] = rows[offset:offset + limit]
    return body


# --- writes ------------------------------------------------------------------------------------------
def adjust_operation(f: Facts, params: Mapping[str, Any]) -> dict[str, Any]:
    """The operation row after moving it: planned machine (same work centre), start and end days."""
    op = str(params.get("operation_id") or "").strip()
    if op not in f.ops:
        raise CannotCheck(f"no operation {op!r}")
    row = dict(f.ops[op])
    if f.state(op) == "completed":
        raise CannotCheck(f"{op} is completed; its schedule is its execution record")
    machine = str(params.get(MACHINE_FIELD) or row.get(MACHINE_FIELD) or "").strip()
    if machine not in f.machines:
        raise CannotCheck(f"no machine {machine!r}")
    if f.machines[machine].get("work_center_id") != row.get("work_center_id"):
        raise CannotCheck(f"{machine} is not in work centre {row.get('work_center_id')}")
    start = day(params.get(START_FIELD)) or day(row.get(START_FIELD))
    if not start:
        raise CannotCheck("planned_start_date is required")
    end = day(params.get(END_FIELD)) or (plus(start, int(num(row.get("standard_duration_days") or 1)) - 1)
                                          if params.get(START_FIELD) else day(row.get(END_FIELD)))
    if end < start:
        raise CannotCheck("planned_end_date is before planned_start_date")
    previous = {k: row.get(k) for k in (MACHINE_FIELD, START_FIELD, END_FIELD)}
    row.update({MACHINE_FIELD: machine, START_FIELD: start, END_FIELD: end})
    return {"row": row, "previous": previous}


def adjust_maintenance(rows: Iterable[Mapping[str, Any]], params: Mapping[str, Any]) -> dict[str, Any]:
    """The maintenance work order after moving its planned days; planned_date (the due day) is kept."""
    key = str(params.get("maintenance_work_order_id") or "").strip()
    found = next((dict(r) for r in rows if str(r.get("maintenance_work_order_id")) == key), None)
    if found is None:
        raise CannotCheck(f"no maintenance work order {key!r}")
    if code(found.get("status")) == "completed":
        raise CannotCheck(f"{key} is completed")
    start = day(params.get("planned_start_date")) or day(found.get("planned_start_date"))
    end = day(params.get("planned_end_date")) or (start if params.get("planned_start_date") else day(found.get("planned_end_date")))
    if not start or end < start:
        raise CannotCheck("planned_end_date is before planned_start_date")
    previous = {k: found.get(k) for k in MWO_FIELDS}
    found.update(planned_start_date=start, planned_end_date=end)
    return {"row": found, "previous": previous}


__all__ = ["BUSINESS_DATE", "CannotCheck", "Facts", "MAX_TASKS", "RULES", "adjust_maintenance", "adjust_operation", "check",
           "day", "detail", "tables_for"]
