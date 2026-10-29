"""Request-local, position-level allocation; optional finite unclosed-PO pool."""
from __future__ import annotations

import math
from collections import Counter, defaultdict

from .bom import product_bom_rows
from .errors import CannotCompute
from .inventory import in_transit_qty
from .warehouse import resolve_warehouse_scope


def finite_quantity(value, label: str, *, positive=False) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise CannotCompute(f"{label} 无效") from exc
    if not math.isfinite(number) or number < 0 or (positive and number == 0):
        raise CannotCompute(f"{label} 必须是有限{'正' if positive else '非负'}数")
    return number


def _main(row):
    return finite_quantity(row.get("alt_priority", 0), "替代优先级") == 0


def _substitute(row):
    return not _main(row)


def _template_rows(rows, product, include_substitute):
    # Validate only the graph reachable under this request's branch policy.
    # Keep physical incoming counts from the complete export so repeated
    # subtree copies are still divided by all exported parent occurrences.
    edges = defaultdict(set)
    for row in rows:
        if finite_quantity(row.get("bom_level", 0), "BOM 层级") > 0 and (include_substitute or _main(row)):
            parent = str(row.get("parent_material_code") or "").strip() or product
            edges[parent].add(str(row.get("material_code") or "").strip())
    reachable, pending = set(), [product]
    while pending:
        code = pending.pop()
        if code in reachable:
            continue
        reachable.add(code)
        pending.extend(edges.get(code, ()))
    # The export repeats a physical parent subtree for each occurrence of that
    # parent in the expanded BOM. Divide identical row multiplicities only by
    # a demonstrated parent-occurrence count, retaining repeated ordinary
    # positions when the parent itself appears just once.
    incoming = Counter((int(finite_quantity(r.get("bom_level", 0), "BOM 层级")), str(r.get("material_code") or "").strip()) for r in rows)
    buckets = defaultdict(list)
    for row in rows:
        level = int(finite_quantity(row.get("bom_level", 0), "BOM 层级"))
        parent = str(row.get("parent_material_code") or "").strip()
        buckets[(level, parent)].append(row)
    keep = set()
    for (level, parent), bucket in buckets.items():
        if level > 0 and (parent or product) not in reachable:
            continue
        count = incoming.get((level - 1, parent), 1)
        def key(row):
            return (str(row.get("material_code") or "").strip(), row.get("standard_usage"),
                    str(row.get("alt_group_no") or ""), row.get("alt_priority", 0))
        frequencies = Counter(key(row) for row in bucket)
        if count > 1 and any(n % count for n in frequencies.values()):
            raise CannotCompute(f"{parent} 重复父件子树不一致，不能建立 BOM 模板")
        quota = {k: n // count for k, n in frequencies.items()}
        for row in bucket:
            signature = key(row)
            if quota[signature] > 0:
                keep.add(id(row))
                quota[signature] -= 1
    return [row for row in rows if id(row) in keep]

def _positions(snap, product: str, include_substitute: bool) -> dict[str, list[list[dict]]]:
    rows = _template_rows(product_bom_rows(snap, product), product, include_substitute)
    positions = defaultdict(list)
    groups = {}
    alternatives = []
    for row in rows:
        level = finite_quantity(row.get("bom_level", 0), "BOM 层级")
        if level == 0:
            continue
        parent = str(row.get("parent_material_code") or "").strip() or product
        code = str(row.get("material_code") or "").strip()
        if not code:
            raise CannotCompute("BOM 缺少物料编码")
        finite_quantity(row.get("standard_usage"), f"{code} BOM 单耗", positive=True)
        group = str(row.get("alt_group_no") or "").strip()
        if group == "0":
            group = ""
        if _main(row):
            position = [row]
            positions[parent].append(position)
            if group:
                if (parent, group) in groups:
                    raise CannotCompute(f"{parent} 替代组 {group} 存在多个主料位置")
                groups[(parent, group)] = position
        elif include_substitute and _substitute(row):
            alternatives.append((parent, group, row))
    for parent, group, row in alternatives:
        if not group or (parent, group) not in groups:
            raise CannotCompute(f"{parent} 替代料缺少有效主料位置")
        groups[(parent, group)].append(row)
    if not positions.get(product):
        raise CannotCompute(f"{product} 缺少可计算的 BOM")
    # Validate the entire reachable candidate graph, even when inventory would
    # hide a malformed branch in this particular demand.
    done = set()
    def validate(code, path):
        if code in path:
            raise CannotCompute(f"BOM 存在循环：{code}")
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
        total = 0.0
        for row in snap.inv_by_material.get(code, []):
            if warehouses and row.get("warehouse") not in warehouses:
                continue
            status = str(row.get("stock_status") or "").strip()
            if status and status != "可用":
                continue
            total += finite_quantity(row.get("available_inventory_qty", 0), f"{code} 可用库存")
        pool[code] = finite_quantity(total, f"{code} 可用库存")
    return finite_quantity(pool[code], f"{code} 剩余库存")


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
        usage = finite_quantity(row.get("standard_usage"), f"{code} BOM 单耗", positive=True)
        avail = _stock(snap, code, scope, pool)
        ranked.append((min(required, avail / usage), _main(row), -index, row, avail, usage))
    _, _, _, chosen, avail, usage = max(ranked, key=lambda item: item[:3])
    return chosen, avail, max(0.0, required * usage - avail)


def net_requirements(snap, product: str, demand_qty: float, *, scope="production_available", substitute_enabled=False,
                     include_finished_goods=False, finished_goods_scope=None, pool=None,
                     include_in_transit=False, transit_pool=None, expand_covered_branches=False, max_nodes=None) -> dict:
    """Consume one shared pool, expand component units only for residual stock.

    pool can be supplied across demands, so finished goods, components and
    leaves cannot be reused. All fields describe the pool before this position.
    """
    demand = finite_quantity(demand_qty, "需求数量")
    transit_pool = {} if transit_pool is None else transit_pool
    positions = _positions(snap, product, substitute_enabled)
    pool = {} if pool is None else pool
    fg_scope = scope if finished_goods_scope is None else finished_goods_scope
    fg = _stock(snap, product, fg_scope, pool) if include_finished_goods else 0.0
    fg_used = min(fg, demand)
    if include_finished_goods:
        pool[product] = fg - fg_used
    root_net = demand - fg_used
    lines = []
    def walk(parent, parent_qty, level, parent_index=None, cumulative_usage=1.0):
        for position in positions.get(parent, []):
            # Candidate ranking includes the same finite PO pool used below.
            eligible = [r for r in position if _main(r) or substitute_enabled]
            ranked = []
            for index, row in enumerate(eligible):
                candidate = str(row["material_code"]).strip()
                stock = _stock(snap, candidate, scope, pool)
                if candidate not in transit_pool:
                    transit_pool[candidate] = in_transit_qty(snap, candidate) if include_in_transit else 0.0
                supply = stock + transit_pool[candidate]
                usage = finite_quantity(row.get("standard_usage"), f"{candidate} BOM 单耗", positive=True)
                ranked.append((min(parent_qty, supply / usage), _main(row), -index, row))
            chosen = max(ranked, key=lambda item: item[:3])[3]
            code = str(chosen["material_code"]).strip()
            avail = _stock(snap, code, scope, pool)
            transit = transit_pool[code]
            usage = float(chosen["standard_usage"])
            gross = parent_qty * usage
            if not math.isfinite(gross):
                raise CannotCompute("BOM 需求乘积超出有限范围")
            allocated = min(avail, gross)
            po_allocated = min(transit, gross - allocated)
            shortage = max(0.0, gross - allocated - po_allocated)
            pool[code] = avail - allocated
            transit_pool[code] = transit - po_allocated
            leaf = not positions.get(code)
            lines.append({"material_code": code, "main_material_code": str(position[0]["material_code"]).strip(),
                          "parent_material_code": parent, "material_name": str(chosen.get("material_name") or ""),
                          "bom_level": level, "gross_requirement": gross, "available_qty": avail,
                          "allocated_qty": allocated + po_allocated, "inventory_allocated_qty": allocated,
                          "in_transit_qty": transit, "po_allocated_qty": po_allocated, "net_requirement": shortage,
                          "usage_per_unit": usage, "cumulative_usage": cumulative_usage * usage,
                          "parent_index": parent_index, "is_leaf": leaf,
                          "source": "main" if _main(chosen) else "substitute"})
            if max_nodes is not None and len(lines) + 1 > max_nodes:
                raise CannotCompute(f"倒排树节点超过上限 {max_nodes}，请缩小范围后重算")
            if not leaf and (shortage > 0 or expand_covered_branches):
                walk(code, shortage, level + 1, len(lines) - 1, cumulative_usage * usage)
    if root_net > 0 or expand_covered_branches:
        walk(product, root_net, 1)
    return {"finished_goods_qty": fg, "finished_goods_allocated_qty": fg_used,
            "root_net_demand": root_net, "lines": lines, "remaining": pool,
            "feasible": all(line["net_requirement"] <= 1e-9 for line in lines if line["is_leaf"])}
