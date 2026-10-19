from __future__ import annotations

from .errors import CannotCompute
from .snapshot import Snapshot, _f


def leadtime_days(snap: Snapshot, material_code: str) -> int:
    code = (material_code or "").strip()
    if not code:
        raise CannotCompute("缺少料号")
    row = snap.materials.get(code)
    if not row:
        raise CannotCompute(f"无物料主数据：{code}")
    attr = (row.get("materialattr") or "").strip()
    purchase = _f(row.get("purchase_fixedleadtime"), 0.0)
    product = _f(row.get("product_fixedleadtime"), 0.0)
    if attr in ("外购", "委外"):
        return int(purchase)
    return int(product)
