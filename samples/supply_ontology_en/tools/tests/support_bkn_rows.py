"""Rows returned by the mocked managed OpenBKN reader in native-function tests."""

from __future__ import annotations

import csv

from fn.snapshot import DATA, load_csv_snapshot


def forecast_rows_from_csv() -> list[dict]:
    with (DATA / "erp_mds_forecast.csv").open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def bkn_rows() -> dict[str, list[dict]]:
    snapshot = load_csv_snapshot()
    return {
        "bom": snapshot.bom,
        "inventory": snapshot.inventory,
        "purchase_order": snapshot.po,
        "purchase_request": snapshot.pr,
        "mrp": snapshot.mrp,
        "material": list(snapshot.materials.values()),
        "forecast": forecast_rows_from_csv(),
    }
