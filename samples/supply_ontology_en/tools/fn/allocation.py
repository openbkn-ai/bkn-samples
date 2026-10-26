"""Request-local, position-level inventory allocation; no PO is consumed."""
from __future__ import annotations

import math
from collections import Counter, defaultdict

from .bom import product_bom_rows, is_main_row, is_substitute_row
from .errors import CannotCompute
from .inventory import available_qty
from .warehouse import resolve_warehouse_scope


def finite_quantity(value, label: str, *, positive=False) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise CannotCompute(f"""Invalid {label}""") from exc
    if not math.isfinite(number) or number < 0 or (positive and number == 0):
        raise CannotCompute(f"""{label} must be a finite {'positive' if positive else 'nonnegative'} number""")
    return number


def _main(row):
    return finite_quantity(row.get("alt_priority", 0), 'alternate priority') == 0


def _substitute(row):
    return is_substitute_row(row)


def _template_rows(rows):
    # The export repeats a physical parent subtree for each occurrence of that
    # parent in the expanded BOM. Divide identical row multiplicities only by
    # a demonstrated parent-occurrence count, retaining repeated ordinary
    # positions when the parent itself appears just once.
    incoming = Counter((int(finite_quantity(r.get("bom_level", 0), 'BOM Level')), str(r.get("material_code") or "").strip()) for r in rows)
    buckets = defaultdict(list)
    for row in rows:
        level = int(finite_quantity(row.get("bom_level", 0), 'BOM Level'))
        parent = str(row.get("parent_material_code") or "").strip()
        buckets[(level, parent)].append(row)
    keep = set()
    for (level, parent), bucket in buckets.items():
        count = incoming.get((level - 1, parent), 1)
        def key(row):
            return (str(row.get("material_code") or "").strip(), row.get("standard_usage"),
                    str(row.get("alt_group_no") or ""), row.get("alt_priority", 0), str(row.get("alt_method") or ""))
        frequencies = Counter(key(row) for row in bucket)
        if count > 1 and any(n % count for n in frequencies.values()):
            raise CannotCompute(f"""{parent} repeated parent subtrees differ; cannot create a BOM template""")
        quota = {k: n // count for k, n in frequencies.items()}
        for row in bucket:
            signature = key(row)
            if quota[signature] > 0:
                keep.add(id(row))
                quota[signature] -= 1
    return [row for row in rows if id(row) in keep]

def _positions(snap, product: str, include_substitute: bool) -> dict[str, list[list[dict]]]:
    rows = _template_rows(product_bom_rows(snap, product))
    positions = defaultdict(list)
    groups = {}
    alternatives = []
    for row in rows:
        level = finite_quantity(row.get("bom_level", 0), 'BOM Level')
        if level == 0:
            continue
        parent = str(row.get("parent_material_code") or "").strip() or product
        code = str(row.get("material_code") or "").strip()
        if not code:
            raise CannotCompute('BOM has no material code')
        finite_quantity(row.get("standard_usage"), f"""{code} BOM usage ratio""", positive=True)
        group = str(row.get("alt_group_no") or "").strip()
        if group == "0":
            group = ""
        if _main(row):
            position = [row]
            positions[parent].append(position)
            if group:
                if (parent, group) in groups:
                    raise CannotCompute(f"""{parent} alternate group {group} has multiple main-component positions""")
                groups[(parent, group)] = position
        elif include_substitute and _substitute(row):
            alternatives.append((parent, group, row))
    for parent, group, row in alternatives:
        if not group or (parent, group) not in groups:
            raise CannotCompute(f"""{parent} alternate has no valid main-component position""")
        groups[(parent, group)].append(row)
    if not positions.get(product):
        raise CannotCompute(f"""{product} has no calculable BOM""")
    # Validate the entire reachable candidate graph, even when inventory would
    # hide a malformed branch in this particular demand.
    done = set()
    def validate(code, path):
        if code in path:
            raise CannotCompute(f"""BOM cycle: {code}""")
        if code in done:
            return
        for position in positions.get(code, []):
            for row in position:
                validate(str(row["material_code"]).strip(), path | {code})
        done.add(code)
    validate(product, set())
    return dict(positions)


def children_by_parent_position(snap, product: str, *, include_substitute: bool) -> dict[str, list[dict]]:
    return {parent: [row for position in positions for row in position]
            for parent, positions in _positions(snap, product, include_substitute).items()}


def _stock(snap, code, scope, pool):
    if code not in pool:
        warehouses = resolve_warehouse_scope(scope)
        for row in snap.inv_by_material.get(code, []):
            if warehouses and row.get("warehouse") not in warehouses:
                continue
            status = str(row.get("stock_status") or "").strip()
            if status and status != 'Available':
                continue
            finite_quantity(row.get("available_inventory_qty", 0), f"""{code} available stock""")
        pool[code] = finite_quantity(available_qty(snap, code, scope), f"""{code} available stock""")
    return finite_quantity(pool[code], f"""{code} remaining stock""")


def choose_candidate(snap, rows: list[dict], required: float, scope, *, enabled: bool, pool=None) -> tuple[dict, float, float]:
    """required is parent units; candidate usage determines material demand."""
    if not rows:
        raise CannotCompute("empty BOM position")
    pool = {} if pool is None else pool
    candidates = [row for row in rows if _main(row) or (enabled and _substitute(row))]
    if not candidates:
        raise CannotCompute("BOM position has no eligible candidate")
    ranked = []
    for index, row in enumerate(candidates):
        code = str(row["material_code"]).strip()
        usage = finite_quantity(row.get("standard_usage"), f"""{code} BOM usage ratio""", positive=True)
        avail = _stock(snap, code, scope, pool)
        ranked.append((min(required, avail / usage), _main(row), -index, row, avail, usage))
    _, _, _, chosen, avail, usage = max(ranked, key=lambda item: item[:3])
    return chosen, avail, max(0.0, required * usage - avail)


def net_requirements(snap, product: str, demand_qty: float, *, scope="all", substitute_enabled=False,
                     include_finished_goods=False, finished_goods_scope=None, pool=None) -> dict:
    """Consume one shared pool, expand component units only for residual stock.

    pool can be supplied across demands, so finished goods, components and
    leaves cannot be reused. All fields describe the pool before this position.
    """
    demand = finite_quantity(demand_qty, 'Required Quantity')
    positions = _positions(snap, product, substitute_enabled)
    pool = {} if pool is None else pool
    fg_scope = scope if finished_goods_scope is None else finished_goods_scope
    fg = _stock(snap, product, fg_scope, pool) if include_finished_goods else 0.0
    fg_used = min(fg, demand)
    if include_finished_goods:
        pool[product] = fg - fg_used
    root_net = demand - fg_used
    lines = []
    def walk(parent, parent_qty, level):
        for position in positions.get(parent, []):
            chosen, avail, shortage = choose_candidate(snap, position, parent_qty, scope,
                                                       enabled=substitute_enabled, pool=pool)
            code = str(chosen["material_code"]).strip()
            usage = float(chosen["standard_usage"])
            gross = parent_qty * usage
            if not math.isfinite(gross):
                raise CannotCompute('BOM demand multiplication exceeds the finite range')
            allocated = min(avail, gross)
            pool[code] = avail - allocated
            leaf = not positions.get(code)
            lines.append({"material_code": code, "main_material_code": str(position[0]["material_code"]).strip(),
                          "parent_material_code": parent, "material_name": str(chosen.get("material_name") or ""),
                          "bom_level": level, "gross_requirement": gross, "available_qty": avail,
                          "allocated_qty": allocated, "net_requirement": shortage,
                          "usage_per_unit": usage, "is_leaf": leaf,
                          "source": "main" if _main(chosen) else "substitute"})
            if shortage > 0 and not leaf:
                walk(code, shortage, level + 1)
    if root_net > 0:
        walk(product, root_net, 1)
    return {"finished_goods_qty": fg, "finished_goods_allocated_qty": fg_used,
            "root_net_demand": root_net, "lines": lines, "remaining": pool,
            "feasible": all(line["net_requirement"] <= 1e-9 for line in lines if line["is_leaf"])}
