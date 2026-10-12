from __future__ import annotations

from .errors import CannotCompute
from .snapshot import Snapshot, _f


def leadtime_days(snap: Snapshot, material_code: str) -> int:
    return leadtime_details(snap, material_code)["leadtime_days"]


def leadtime_details(snap: Snapshot, material_code: str) -> dict:
    code = (material_code or "").strip()
    if not code:
        raise CannotCompute("缺少料号")
    row = snap.materials.get(code)
    if not row:
        raise CannotCompute(f"无物料主数据：{code}")
    attr = (row.get("materialattr") or "").strip()
    purchase = attr in ("外购", "委外")
    field = "purchase_fixedleadtime" if purchase else "product_fixedleadtime"
    return {
        "material_code": code,
        "leadtime_days": int(_f(row.get(field), 0.0)),
        "caliber": "purchase" if purchase else "production",
        "material_attribute": attr or None,
        "source_field": field,
        "unit": "day",
        "selection_rule": "外购/委外取采购固定提前期；其他属性取生产固定提前期",
        "attribute_missing": not bool(attr),
    }
