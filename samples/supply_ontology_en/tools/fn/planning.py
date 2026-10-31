"""Supply planning calculations Cypher cannot express: layered BOM netting on a shared pool.

Rules follow the sample PRD (docs/PRD.en-US.md, business rules 4–9):

- Supply is ``Available`` stock in the warehouse scope. With ``need_by``, open purchase lines due from
  the business date to that date (inclusive) are added. Overdue lines count only when
  ``chase_overdue_po``.
- A demand uses finished goods first; the rest is expanded level by level. Each level uses
  its component's supply before expanding only the net shortage; what cannot be expanded
  further is a material shortage. All demands draw from one pool.
- Substitutes are off unless enabled: one candidate per position, own usage, the candidate
  covering most of the parent's need wins, ties go to the main part, then BOM order.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from decimal import Decimal
from typing import Any

from .errors import CannotCompute
from .warehouse import resolve_warehouse_scope

DEFAULT_BUSINESS_DATE = "2026-08-25"
_MAX_BUILD = 10_000_000


def _d(value: Any) -> Decimal:
    return Decimal(str(value or 0))


def _number(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral_value() else float(round(value, 6))


def _main(row: Mapping[str, Any]) -> bool:
    return int(_d(row.get("alt_priority"))) == 0 and str(row.get("alt_part") or "") != "√"


def is_open_po(row: Mapping[str, Any]) -> bool:
    return (row.get("rowclosestatus_title") == "Open" and row.get("rowterminatestatus_title") == "Open"
            and _d(row.get("qty")) - _d(row.get("actqty")) > 0)


def unshipped(row: Mapping[str, Any]) -> int:
    return int(_d(row.get("signing_quantity")) - _d(row.get("shipping_quantity")))


class Plan:
    """Facts for a set of products: BOM trees, stock, in-transit and signed backlog."""

    def __init__(self, rows: Mapping[str, Iterable[Mapping[str, Any]]], *, warehouse_scope: Any = "all",
                 need_by: str | None = None, chase_overdue_po: bool = False,
                 business_date: str = DEFAULT_BUSINESS_DATE):
        warehouses = set(resolve_warehouse_scope(warehouse_scope))
        self.business_date = business_date
        self.stock: dict[str, Decimal] = defaultdict(Decimal)
        for row in rows.get("inventory", ()):
            if row.get("stock_status") == "Available" and (not warehouses or row.get("warehouse") in warehouses):
                self.stock[str(row["material_code"])] += _d(row.get("available_inventory_qty"))
        self.in_transit: dict[str, Decimal] = defaultdict(Decimal)
        for row in rows.get("purchase_order", ()):
            due = str(row.get("deliverdate") or "")
            on_time = need_by is not None and business_date <= due <= need_by
            if is_open_po(row) and (on_time or (chase_overdue_po and due < business_date)):
                self.in_transit[str(row["material_number"])] += _d(row.get("qty")) - _d(row.get("actqty"))
        self.backlog_orders = sorted((r for r in rows.get("sales_order", ()) if unshipped(r) > 0),
                                     key=lambda r: (str(r.get("promised_delivery_date")), str(r.get("sales_order_id"))))
        self.templates: dict[tuple[str, int, str], list[Mapping[str, Any]]] = {}
        by_root: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for row in rows.get("bom", ()):
            by_root[str(row["bom_material_code"])].append(row)
        for root, tree in by_root.items():
            tree.sort(key=lambda r: int(_d(r.get("seq_no"))))
            occurrences = Counter((int(_d(r.get("bom_level"))), str(r["material_code"])) for r in tree)
            groups: dict[tuple[int, str], list[Mapping[str, Any]]] = defaultdict(list)
            for row in tree:
                level = int(_d(row.get("bom_level")))
                if level > 0:
                    groups[level, str(row["parent_material_code"])].append(row)
            # A parent that appears n times carries its child sequence n times; expand it once per need.
            for (level, parent), children in groups.items():
                self.templates[root, level - 1, parent] = children[:len(children) // max(1, occurrences[level - 1, parent])]

    def pool(self) -> dict[str, Decimal]:
        pool = defaultdict(Decimal, self.stock)
        for code, qty in self.in_transit.items():
            pool[code] += qty
        return pool

    def _positions(self, product: str, level: int, parent: str, substitutes: bool):
        rows = self.templates.get((product, level, parent), [])
        for row in rows:
            if not _main(row):
                continue
            group = str(row.get("alt_group_no") or "0")
            yield [r for r in rows if str(r.get("alt_group_no") or "0") == group] if substitutes and group != "0" else [row]

    def allocate(self, pool: dict[str, Decimal], product: str, qty: Any, *, substitutes: bool = False,
                 use_finished_goods: bool = True) -> dict[str, Any]:
        if (product, 0, product) not in self.templates:
            raise CannotCompute(f"Product {product} has no BOM; nothing to calculate")
        qty = _d(qty)
        shortages: dict[str, Decimal] = defaultdict(Decimal)
        finished = min(qty, max(Decimal(0), pool[product])) if use_finished_goods else Decimal(0)
        pool[product] -= finished

        def expand(parent: str, count: Decimal, level: int) -> None:
            for candidates in self._positions(product, level, parent, substitutes):
                row = max(candidates, key=lambda r: (min(count, max(Decimal(0), pool[str(r["material_code"])]) / _d(r["standard_usage"])),
                                                     _main(r), -int(_d(r.get("seq_no")))))
                code = str(row["material_code"])
                required = count * _d(row["standard_usage"])
                used = min(required, max(Decimal(0), pool[code]))
                pool[code] -= used
                if required > used:
                    if any(True for _ in self._positions(product, level + 1, code, substitutes)):
                        expand(code, required - used, level + 1)
                    else:
                        shortages[code] += required - used

        if qty > finished:
            expand(product, qty - finished, 0)
        return {"product": product, "qty": _number(qty), "finished_goods_used": _number(finished),
                "manufacture_qty": _number(qty - finished), "covered": not shortages,
                "shortages": {code: _number(v) for code, v in sorted(shortages.items())}}

    def reserve_backlog(self, pool: dict[str, Decimal], products: set[str], substitutes: bool) -> list[str]:
        reserved = []
        for order in self.backlog_orders:
            if order.get("product_code") in products:
                self.allocate(pool, str(order["product_code"]), unshipped(order), substitutes=substitutes)
                reserved.append(str(order["sales_order_id"]))
        return reserved

    def buildable(self, product: str, substitutes: bool) -> int:
        def ok(n: int) -> bool:
            return self.allocate(self.pool(), product, n, substitutes=substitutes, use_finished_goods=False)["covered"]
        low, high = 0, 1
        while ok(high):
            low, high = high, high * 2
            if high > _MAX_BUILD:
                raise CannotCompute(f"Product {product} has no build limit; check its BOM")
        while low + 1 < high:
            mid = (low + high) // 2
            low, high = (mid, high) if ok(mid) else (low, mid)
        return low


def _basis(plan: Plan, need_by: str | None, chase_overdue_po: bool, substitutes: bool, warehouse_scope: Any) -> dict[str, Any]:
    return {"business_date": plan.business_date, "warehouse_scope": warehouse_scope,
            "in_transit": ("overdue open purchase lines counted as chased back; " if chase_overdue_po else "overdue open purchase lines not counted; ")
                          + (f"open purchase lines due {plan.business_date} to {need_by} counted" if need_by else "open purchase lines not counted"),
            "substitutes": "alternates allowed" if substitutes else "no alternates"}


def build_capacity(rows: Mapping[str, Iterable[Mapping[str, Any]]], product: str, *, substitute_enabled: bool = False,
                   warehouse_scope: Any = "all", need_by: str | None = None, chase_overdue_po: bool = False,
                   business_date: str = DEFAULT_BUSINESS_DATE) -> dict[str, Any]:
    """Finished goods, the most supply can still build, signed backlog and available-to-promise."""
    plan = Plan(rows, warehouse_scope=warehouse_scope, need_by=need_by, chase_overdue_po=chase_overdue_po,
                business_date=business_date)
    buildable = plan.buildable(product, substitute_enabled)
    finished = plan.stock[product]
    backlog = sum(unshipped(r) for r in plan.backlog_orders if r.get("product_code") == product)
    blocked = plan.allocate(plan.pool(), product, buildable + 1, substitutes=substitute_enabled, use_finished_goods=False)
    return {"product": product, "finished_goods_qty": _number(finished), "buildable_qty": buildable,
            "signed_backlog_qty": backlog,
            "available_to_promise": _number(max(Decimal(0), finished + buildable - backlog)),
            "limiting_materials": blocked["shortages"],
            "basis": _basis(plan, need_by, chase_overdue_po, substitute_enabled, warehouse_scope)}


def demand_coverage(rows: Mapping[str, Iterable[Mapping[str, Any]]], demands: list[Mapping[str, Any]], *,
                    substitute_enabled: bool = False, warehouse_scope: Any = "all", need_by: str | None = None,
                    chase_overdue_po: bool = False, reserve_signed_backlog: bool = False,
                    use_finished_goods: bool = True, business_date: str = DEFAULT_BUSINESS_DATE) -> dict[str, Any]:
    """Evaluate demands in order on one shared pool, optionally after the products' signed backlog."""
    if not demands:
        raise CannotCompute("At least one demand is required")
    plan = Plan(rows, warehouse_scope=warehouse_scope, need_by=need_by, chase_overdue_po=chase_overdue_po,
                business_date=business_date)
    pool = plan.pool()
    products = {str(d["product"]) for d in demands}
    reserved = plan.reserve_backlog(pool, products, substitute_enabled) if reserve_signed_backlog else []
    results = [plan.allocate(pool, str(d["product"]), d["qty"], substitutes=substitute_enabled,
                             use_finished_goods=use_finished_goods) for d in demands]
    return {"all_covered": all(r["covered"] for r in results), "demands": results,
            "reserved_backlog_orders": reserved,
            "basis": _basis(plan, need_by, chase_overdue_po, substitute_enabled, warehouse_scope)}
