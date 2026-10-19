from __future__ import annotations

from .bom import is_substitute_row, product_bom_rows
from .errors import CannotCompute
from .inventory import available_qty
from .snapshot import Snapshot, _i


def substitute_status(
    snap: Snapshot,
    product: str | None = None,
    *,
    material_code: str | None = None,
    warehouse_scope: str | list[str] | None = "production_available",
    substitute_enabled: bool | None = None,
) -> dict:
    product = (product or "").strip()
    material_code = (material_code or "").strip()
    if bool(product) == bool(material_code):
        raise CannotCompute("替代料状态必须且只能传入产品编码或物料编码之一")
    rows = product_bom_rows(snap, product) if product else list(snap.bom)
    if product and not rows:
        raise CannotCompute(f"无 BOM：{product}")
    groups: dict[str, list[dict]] = {}
    if material_code:
        matched = [
            row for row in rows
            if (row.get("material_code") or "").strip() == material_code
            and str(row.get("alt_group_no") or "").strip()
        ]
        if not matched:
            raise CannotCompute(f"物料未配置替代组：{material_code}")
        match_keys = {
            (
                (row.get("bom_material_code") or "").strip(),
                (row.get("parent_material_code") or "").strip(),
                str(row.get("alt_group_no") or "").strip(),
            )
            for row in matched
        }
        for row in rows:
            key = (
                (row.get("bom_material_code") or "").strip(),
                (row.get("parent_material_code") or "").strip(),
                str(row.get("alt_group_no") or "").strip(),
            )
            if key in match_keys:
                groups.setdefault("|".join(key), []).append(row)
    else:
        for row in rows:
            if not is_substitute_row(row):
                continue
            gid = str(row.get("alt_group_no") or "").strip()
            groups.setdefault(gid, []).append(row)
    members = []
    for gid, items in sorted(groups.items(), key=lambda kv: kv[0]):
        members.append(
            {
                "alt_group_no": gid,
                "members": [
                    {
                        "material_code": (r.get("material_code") or "").strip(),
                        "material_name": (r.get("material_name") or "").strip(),
                        "alt_priority": _i(r.get("alt_priority"), 0),
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
    }
