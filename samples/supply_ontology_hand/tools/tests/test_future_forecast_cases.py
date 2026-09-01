import csv
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
EXPECTED_CASES = {
    "0000023181-FUTURE": ("U00-000080", 3000.0, date(2026, 10, 31)),
    "0000023181-SHORT": ("U00-000080", 6000.0, date(2026, 11, 30)),
    "0000023181-CONTENTION": ("U00-000080", 500.0, date(2026, 12, 31)),
}


def read_forecasts(sample_name):
    path = REPO_ROOT / "samples" / sample_name / "data" / "erp_mds_forecast.csv"
    with path.open(newline="") as handle:
        return {row["id"]: row for row in csv.DictReader(handle)}


def test_future_forecast_cases_exist_in_the_released_chinese_sample():
    forecasts = read_forecasts("supply_ontology_hand")
    for forecast_id, (product, quantity, due_date) in EXPECTED_CASES.items():
        row = forecasts[forecast_id]
        assert row["material_number"] == product
        assert float(row["qty"]) == quantity
        assert date.fromisoformat(row["enddate"]) == due_date
        assert due_date > date(2026, 8, 15)


def test_historical_regression_case_is_retained():
    row = read_forecasts("supply_ontology_hand")["0000023181"]
    assert row["material_number"] == "U00-000080"
    assert row["enddate"] == "2026-05-31"
