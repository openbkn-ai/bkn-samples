from __future__ import annotations

from collections import defaultdict

from .errors import CannotCompute
from .snapshot import Snapshot, _f, _i


def is_main_row(row: dict) -> bool:
    priority = _i(row.get("alt_priority"), 0)
    method = (row.get("alt_method") or "").strip()
    return priority == 0 and method != "替代"


def is_substitute_row(row: dict) -> bool:
    method = (row.get("alt_method") or "").strip()
    priority = _i(row.get("alt_priority"), 0)
    return method == "替代" or priority > 0


def product_bom_rows(snap: Snapshot, product: str) -> list[dict]:
    return list(snap.bom_by_product.get((product or "").strip(), []))


def filter_bom_rows(
    rows: list[dict],
    *,
    include_substitute: bool = False,
    depth: int | None = None,
    include_root: bool = False,
) -> list[dict]:
    out = []
    for row in rows:
        level = _i(row.get("bom_level"), 0)
        if not include_root and level == 0:
            continue
        if not include_substitute and not is_main_row(row):
            continue
        if depth is not None and level > depth:
            continue
        if depth is not None and level == 0:
            continue
        out.append(row)
    return out


def _line_payload(row: dict) -> dict:
    return {
        "material_code": (row.get("material_code") or "").strip(),
        "material_name": (row.get("material_name") or "").strip(),
        "standard_usage": _f(row.get("standard_usage"), 1.0),
        "bom_level": _i(row.get("bom_level"), 0),
        "parent_material_code": (row.get("parent_material_code") or "").strip(),
        "alt_group_no": str(row.get("alt_group_no") or "").strip(),
        "alt_priority": _i(row.get("alt_priority"), 0),
        "alt_method": (row.get("alt_method") or "").strip(),
        "is_substitute": is_substitute_row(row),
        "bom_version": (row.get("bom_version") or "").strip(),
    }


def bom_list(
    snap: Snapshot,
    product: str,
    *,
    depth: int | None = 1,
    include_substitute: bool = False,
    report_grain: str = "summary",
    page_size: int = 100,
    offset: int = 0,
) -> dict:
    product = (product or "").strip()
    if not product:
        raise CannotCompute("缺少产品编码")
    if report_grain not in {"summary", "full"}:
        raise CannotCompute("report_grain 只能为 summary 或 full")
    if isinstance(page_size, bool) or not isinstance(page_size, int) or not 1 <= page_size <= 500:
        raise CannotCompute("page_size 必须是 1 到 500 的整数")
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise CannotCompute("offset 必须是非负整数")
    rows = product_bom_rows(snap, product)
    if not rows:
        raise CannotCompute(f"无 BOM：{product}")

    mains = filter_bom_rows(rows, include_substitute=False, depth=None)
    scoped = filter_bom_rows(
        rows, include_substitute=include_substitute, depth=depth
    )
    l1_main = [
        r for r in mains if _i(r.get("bom_level"), 0) == 1
    ]
    levels = [_i(r.get("bom_level"), 0) for r in rows]
    result = {
        "product_code": product,
        "include_substitute": include_substitute,
        "depth": depth,
        "line_count": len(mains) if not include_substitute else len(
            filter_bom_rows(rows, include_substitute=True, depth=None)
        ),
        "unique_child_count": len(
            {
                (r.get("material_code") or "").strip()
                for r in (mains if not include_substitute else filter_bom_rows(rows, include_substitute=True, depth=None))
            }
        ),
        "max_level": max(levels) if levels else 0,
        "l1_main_count": len(l1_main),
        "rows_incl_root": len(rows),
        "caliber": "main_only" if not include_substitute else "include_substitute",
        "report_grain": report_grain,
        "l1_lines": [_line_payload(r) for r in l1_main],
    }
    if report_grain == "full":
        page = scoped[offset : offset + page_size]
        next_offset = offset + len(page)
        result.update(
            {
                "lines": [_line_payload(r) for r in page],
                "offset": offset,
                "page_size": page_size,
                "next_offset": next_offset if next_offset < len(scoped) else None,
                "scoped_line_count": len(scoped),
            }
        )
    return result


def material_where_used(
    snap: Snapshot,
    material_code: str,
    *,
    report_grain: str = "summary",
    include_substitute: bool = True,
) -> dict:
    """Return finished products affected by one material through their BOMs."""
    material_code = (material_code or "").strip()
    if not material_code:
        raise CannotCompute("缺少物料编码")
    if report_grain not in {"summary", "full"}:
        raise CannotCompute("report_grain 只能为 summary 或 full")

    # Impact analysis includes alternate branches by default: a material that
    # appears as a qualified substitute still affects a product's supply risk.
    rows = list(snap.bom) if include_substitute else [
        row for row in snap.bom if is_main_row(row)
    ]
    parents_by_child: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        child = (row.get("material_code") or "").strip()
        if child:
            parents_by_child[child].append(row)

    # A component can first be assembled into an intermediate material and then
    # flow into further products.  Traverse parent links to report every final
    # product affected by the original material, not merely its direct parents.
    hits: dict[str, list[dict]] = defaultdict(list)
    visited = {material_code}
    pending = [material_code]
    while pending:
        child = pending.pop()
        for row in parents_by_child.get(child, []):
            product_code = (row.get("bom_material_code") or "").strip()
            if product_code:
                hits[product_code].append(_line_payload(row))
            parent = (row.get("parent_material_code") or "").strip()
            if parent and parent not in visited:
                visited.add(parent)
                pending.append(parent)
    if not hits:
        raise CannotCompute(f"物料未被任何产品 BOM 使用：{material_code}")

    product_codes = sorted(hits)
    result = {
        "material_code": material_code,
        "affected_product_count": len(product_codes),
        "product_codes": product_codes,
        "include_substitute": include_substitute,
        "caliber": (
            "bom_root_products_including_substitute"
            if include_substitute
            else "main_bom_root_products"
        ),
        "report_grain": report_grain,
    }
    if report_grain == "full":
        result["paths"] = [
            {"product_code": product, "bom_lines": hits[product]}
            for product in product_codes
        ]
    return result


def unique_child_codes(
    snap: Snapshot, product: str, *, include_substitute: bool = False
) -> set[str]:
    rows = product_bom_rows(snap, product)
    if not rows:
        raise CannotCompute(f"无 BOM：{product}")
    scoped = filter_bom_rows(rows, include_substitute=include_substitute, depth=None)
    return {(r.get("material_code") or "").strip() for r in scoped if (r.get("material_code") or "").strip()}


def bom_shared_list(
    snap: Snapshot,
    products: list[str],
    *,
    include_substitute: bool = False,
    depth: int | None = None,
) -> dict:
    codes = [(p or "").strip() for p in (products or []) if (p or "").strip()]
    if len(codes) < 2:
        raise CannotCompute("产品 BOM 共用清单至少需要 2 个产品")
    sets: list[set[str]] = []
    per_product: dict[str, dict[str, list[dict]]] = {}
    for product in codes:
        rows = product_bom_rows(snap, product)
        if not rows:
            raise CannotCompute(f"无 BOM：{product}")
        scoped = filter_bom_rows(
            rows, include_substitute=include_substitute, depth=depth
        )
        by_child: dict[str, list[dict]] = defaultdict(list)
        for row in scoped:
            child = (row.get("material_code") or "").strip()
            if child:
                by_child[child].append(_line_payload(row))
        per_product[product] = dict(by_child)
        sets.append(set(by_child))
    shared = set.intersection(*sets) if sets else set()
    shared_codes = sorted(shared)
    details = []
    for child in shared_codes:
        details.append(
            {
                "material_code": child,
                "on_products": {
                    product: per_product[product][child] for product in codes
                },
            }
        )
    return {
        "products": codes,
        "include_substitute": include_substitute,
        "depth": depth,
        "shared_codes": shared_codes,
        "shared_count": len(shared_codes),
        "details": details,
        "caliber": "structure_intersect_only",
    }


def children_by_parent(
    snap: Snapshot, product: str, *, include_substitute: bool = False
) -> dict[str, list[dict]]:
    rows = filter_bom_rows(
        product_bom_rows(snap, product),
        include_substitute=include_substitute,
        depth=None,
    )
    tree: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        parent = (row.get("parent_material_code") or "").strip() or product
        tree[parent].append(row)
    return dict(tree)


def explode_leaf_usage(
    snap: Snapshot,
    product: str,
    *,
    include_substitute: bool = False,
) -> dict[str, dict]:
    """Leaf material_code → cumulative usage per 1 finished unit (main tree)."""
    product = (product or "").strip()
    if not product:
        raise CannotCompute("缺少产品编码")
    rows = product_bom_rows(snap, product)
    if not rows:
        raise CannotCompute(f"无 BOM：{product}")
    tree = children_by_parent(snap, product, include_substitute=False)
    usage: dict[str, float] = defaultdict(float)
    meta: dict[str, dict] = {}

    def walk(parent: str, cum: float, ancestors: tuple[str, ...], l1: str) -> None:
        kids = tree.get(parent) or []
        if not kids:
            if parent != product:
                usage[parent] += cum
            return
        for row in kids:
            child = (row.get("material_code") or "").strip()
            if not child or child in ancestors:
                continue
            std = _f(row.get("standard_usage"), 0.0)
            level = _i(row.get("bom_level"), 0)
            child_l1 = child if level == 1 else l1
            meta.setdefault(
                child,
                {
                    "material_name": (row.get("material_name") or "").strip(),
                    "parent_material_code": parent,
                    "alt_group_no": str(row.get("alt_group_no") or "").strip(),
                    "standard_usage": std,
                    "bom_level": level,
                    "l1_parent": child_l1,
                },
            )
            walk(child, cum * std, ancestors + (child,), child_l1)

    walk(product, 1.0, (product,), "")
    out = {}
    for code, qty in usage.items():
        info = meta.get(code, {})
        out[code] = {
            "material_code": code,
            "material_name": info.get("material_name", ""),
            "usage_per_unit": qty,
            "standard_usage": float(info.get("standard_usage") or 0.0),
            "parent_material_code": info.get("parent_material_code", ""),
            "alt_group_no": info.get("alt_group_no", ""),
            "bom_level": info.get("bom_level", 0),
            "l1_parent": info.get("l1_parent", ""),
        }
    if include_substitute:
        groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for row in rows:
            if not is_substitute_row(row):
                continue
            parent = (row.get("parent_material_code") or "").strip()
            group = str(row.get("alt_group_no") or "").strip()
            groups[(parent, group)].append(row)
        for code, item in out.items():
            alts = groups.get((item["parent_material_code"], item["alt_group_no"]), [])
            main_std = float(item.get("standard_usage") or 0.0)
            item["substitutes"] = []
            for r in alts:
                alt_code = (r.get("material_code") or "").strip()
                if not alt_code:
                    continue
                alt_std = _f(r.get("standard_usage"), 0.0)
                if main_std > 0 and alt_std > 0:
                    alt_usage = item["usage_per_unit"] * (alt_std / main_std)
                else:
                    alt_usage = item["usage_per_unit"]
                item["substitutes"].append(
                    {
                        "material_code": alt_code,
                        "material_name": (r.get("material_name") or "").strip(),
                        "usage_per_unit": alt_usage,
                        "alt_priority": _i(r.get("alt_priority"), 0),
                    }
                )
    else:
        for item in out.values():
            item["substitutes"] = []
    return out
