from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PACK = Path(__file__).resolve().parents[2]
DATA = PACK / "data"


def _f(val, default: float = 0.0) -> float:
    try:
        if val is None or str(val).strip() == "":
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def _i(val, default: int = 0) -> int:
    return int(_f(val, float(default)))


@dataclass
class Snapshot:
    bom: list[dict] = field(default_factory=list)
    inventory: list[dict] = field(default_factory=list)
    po: list[dict] = field(default_factory=list)
    pr: list[dict] = field(default_factory=list)
    mrp: list[dict] = field(default_factory=list)
    forecast: list[dict] = field(default_factory=list)
    materials: dict[str, dict] = field(default_factory=dict)
    forecast_by_id: dict[str, dict] = field(default_factory=dict)
    bom_by_product: dict[str, list[dict]] = field(default_factory=dict)
    inv_by_material: dict[str, list[dict]] = field(default_factory=dict)
    po_by_material: dict[str, list[dict]] = field(default_factory=dict)
    pr_by_material: dict[str, list[dict]] = field(default_factory=dict)
    mrp_by_material: dict[str, list[dict]] = field(default_factory=dict)


def _read_csv(name: str, data_dir: Path | None = None) -> list[dict]:
    base = Path(data_dir) if data_dir is not None else DATA
    with (base / name).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _copy_rows(
    rows_by_dataset: Mapping[str, Iterable[Mapping[str, Any]] | None],
    *names: str,
) -> list[dict]:
    for name in names:
        dataset_rows = rows_by_dataset.get(name)
        if dataset_rows:
            return [dict(row) for row in dataset_rows]
    return []


def _index_by(rows: list[dict], key: str, *, skip_blank: bool = False) -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = {}
    for row in rows:
        code = (row.get(key) or "").strip()
        if skip_blank and not code:
            continue
        index.setdefault(code, []).append(row)
    return index


def build_snapshot(
    rows_by_dataset: Mapping[str, Iterable[Mapping[str, Any]] | None] | None = None,
) -> Snapshot:
    'Build a snapshot from shallow copies of logical dataset rows, without mutating inputs. Supported datasets: material, bom, inventory, purchase_order (po), purchase_request (pr), mrp and forecast. Other datasets are ignored.'
    rows = rows_by_dataset or {}
    snap = Snapshot()
    snap.bom = _copy_rows(rows, "bom")
    snap.inventory = _copy_rows(rows, "inventory")
    snap.po = _copy_rows(rows, "purchase_order", "po")
    snap.pr = _copy_rows(rows, "purchase_request", "pr")
    snap.mrp = _copy_rows(rows, "mrp")
    snap.forecast = _copy_rows(rows, "forecast")
    for row in _copy_rows(rows, "material", "materials"):
        code = (row.get("material_code") or "").strip()
        if code:
            snap.materials[code] = row
    for row in snap.forecast:
        forecast_id = str(row.get("id") or "").strip()
        if not forecast_id:
            forecast_id = str(row.get("forecast_id") or "").strip()
        if not forecast_id:
            continue
        if forecast_id in snap.forecast_by_id:
            raise ValueError(f"""Duplicate forecast ID: {forecast_id}""")
        snap.forecast_by_id[forecast_id] = row
    snap.bom_by_product = _index_by(snap.bom, "bom_material_code", skip_blank=True)
    snap.inv_by_material = _index_by(snap.inventory, "material_code")
    snap.po_by_material = _index_by(snap.po, "material_number")
    snap.pr_by_material = _index_by(snap.pr, "material_number")
    snap.mrp_by_material = _index_by(snap.mrp, "materialplanid_number")
    return snap


def load_csv_snapshot(data_dir: Path | None = None) -> Snapshot:
    'CSV supports offline unit tests and gold regression only; no runtime CSV fallback.'
    base = Path(data_dir) if data_dir is not None else DATA
    return build_snapshot(
        {
            "material": _read_csv("erp_material.csv", base),
            "bom": _read_csv("erp_material_bom.csv", base),
            "inventory": _read_csv("erp_real_time_inventory.csv", base),
            "purchase_order": _read_csv("erp_purchase_order.csv", base),
            "purchase_request": _read_csv("erp_purchase_request.csv", base),
            "mrp": _read_csv("erp_mrp_plan_order.csv", base),
            "forecast": _read_csv("erp_mds_forecast.csv", base),
        }
    )
