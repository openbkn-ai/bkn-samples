"""Validate frozen local inputs; this is not an online Agent evaluation."""

import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path


BASE = Path(__file__).resolve().parent


def main():
    manifest = json.loads((BASE / "manifest.json").read_text(encoding="utf-8"))
    for item in [manifest["question_set"], manifest["answer_set"], *manifest["data_files"]]:
        path = BASE / item["path"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != item["sha256"]:
            raise ValueError(f"Frozen input changed: {item['path']}")
        if "rows" in item:
            with path.open(newline="", encoding="utf-8-sig") as handle:
                found = sum(1 for _ in csv.DictReader(handle))
            if found != item["rows"]:
                raise ValueError(f"Row count changed: {item['path']}")
    with (BASE / "../../../data/erp_mds_forecast.csv").open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("Forecast IDs must be unique")
    opened = [row for row in rows if row["closestatus_title"] != "已关闭"]
    closed = [row for row in rows if row["closestatus_title"] == "已关闭"]
    product = [row for row in opened if row["material_number"] == "U00-000080"]
    found = {
        "total_count": len(rows),
        "open_count": len(opened),
        "closed_count": len(closed),
        "total_qty": str(sum(Decimal(row["qty"]) for row in rows)),
        "open_qty": str(sum(Decimal(row["qty"]) for row in opened)),
        "closed_qty": str(sum(Decimal(row["qty"]) for row in closed)),
        "U00_open_count": len(product),
        "U00_open_qty": str(sum(Decimal(row["qty"]) for row in product)),
    }
    if found != manifest["expected_forecast_aggregates"]:
        raise ValueError("Forecast aggregates differ from the frozen baseline")
    print(f"{manifest['baseline_id']}: local input integrity passed; online score is recorded separately")


if __name__ == "__main__":
    main()
