from __future__ import annotations

from .bom import is_substitute_row, product_bom_rows
from .errors import CannotCompute
from .inventory import available_qty
from .snapshot import Snapshot, _f, _i
from .warehouse import resolve_warehouse_scope


def substitute_status(
    snap: Snapshot,
    product: str | None = None,
    *,
    material_code: str | None = None,
    warehouse_scope: str | list[str] | None = "all",
    substitute_enabled: bool | None = None,
) -> dict:
    product = (product or "").strip()
    material_code = (material_code or "").strip()
    if bool(product) == bool(material_code):
        raise CannotCompute('Alternate status requires exactly one of product or material_code')
    rows = product_bom_rows(snap, product) if product else list(snap.bom)
    if product and not rows:
        raise CannotCompute(f"""No BOM: {product}""")
    def group_key(row: dict) -> tuple[str, str, str]:
        return (
            (row.get("bom_material_code") or "").strip(),
            (row.get("parent_material_code") or "").strip(),
            str(row.get("alt_group_no") or "").strip(),
        )

    if material_code:
        match_keys = {
            group_key(row) for row in rows
            if (row.get("material_code") or "").strip() == material_code
            and group_key(row)[2]
        }
        if not match_keys:
            raise CannotCompute(f"""Material has no alternate group: {material_code}""")
    else:
        match_keys = {group_key(row) for row in rows if is_substitute_row(row)}
    # Inventory status describes facts for every member even if using alternates
    # is disabled. Strategy flags never remove candidate inventory facts.
    groups: dict[tuple[str, str, str], list[dict]] = {}
    for row in rows:
        key = group_key(row)
        if key in match_keys:
            groups.setdefault(key, []).append(row)
    members = []
    for key, items in sorted(groups.items()):
        members.append(
            {
                "group_key": "|".join(key),
                "product_code": key[0],
                "parent_material_code": key[1],
                "alt_group_no": key[2],
                "members": [
                    {
                        "material_code": (r.get("material_code") or "").strip(),
                        "material_name": (r.get("material_name") or "").strip(),
                        "alt_priority": _i(r.get("alt_priority"), 0),
                        "is_substitute": is_substitute_row(r),
                        "standard_usage": _f(r.get("standard_usage"), 0.0),
                        "parent_material_code": (r.get("parent_material_code") or "").strip(),
                        "available_qty": available_qty(
                            snap,
                            (r.get("material_code") or "").strip(),
                            warehouse_scope,
                        ),
                    }
                    for r in items
                ],
            }
        )
    enabled = "unknown" if substitute_enabled is None else bool(substitute_enabled)
    return {
        "product_code": product or None,
        "material_code": material_code or None,
        "has_alt_groups": bool(groups),
        "group_count": len(groups),
        "groups": members,
        "substitute_enabled": enabled,
        "warehouse_scope": warehouse_scope if not isinstance(warehouse_scope, list) else "custom",
        "warehouse_filter": resolve_warehouse_scope(warehouse_scope),
        "member_caliber": "complete_group_including_main_and_substitutes",
    }
