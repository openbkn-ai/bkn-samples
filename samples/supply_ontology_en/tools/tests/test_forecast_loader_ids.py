"""Regression coverage for issue #27: business identifiers and early failure."""

import pytest

from fn.errors import CannotCompute
from managed_execution import load_bkn_rows


@pytest.mark.parametrize("requested,stored,expected_queries", [
    ("0000023181", "0000023181", ["0000023181"]),
    ("0000023181", 23181, ["0000023181", "23181"]),
    ("0000023181-FUTURE", "0000023181-FUTURE", ["0000023181-FUTURE"]),
])
def test_exact_business_id_precedes_legacy_fallback(requested, stored, expected_queries):
    calls = []

    def query(**kwargs):
        calls.append(kwargs)
        if kwargs["ot_id"].endswith("_forecast") and kwargs["condition"]["value"] == str(stored):
            return {"datas": [{"id": stored, "material_number": "U00-000080"}]}
        return {"datas": []}

    rows = load_bkn_rows("backward_plan", query, {"forecast_id": requested, "substitute_enabled": False})
    assert rows["forecast"][0]["id"] == stored
    assert [c["condition"]["value"] for c in calls if c["ot_id"].endswith("_forecast")] == expected_queries
    bom = next(c for c in calls if c["ot_id"].endswith("_bom"))
    assert bom["condition"]["value"] == "U00-000080"


@pytest.mark.parametrize("product", [None, "U00-000080"])
def test_unknown_forecast_stops_before_any_other_dataset(product):
    calls = []

    def query(**kwargs):
        calls.append(kwargs)
        return {"datas": []}

    with pytest.raises(CannotCompute, match='Forecast not found'):
        load_bkn_rows("backward_plan", query, {"forecast_id": "0000023181", "product": product, "substitute_enabled": False})
    assert all(c["ot_id"].endswith("_forecast") for c in calls)


@pytest.mark.parametrize("forecast_rows,error", [
    ([{"id": "0000023181"}], 'has no product code'),
    ([{"id": "0000023181", "material_number": "OTHER"}], 'differs from the requested product'),
    ([{"id": "0000023181", "material_number": "U00-000080"}] * 2, 'Ambiguous forecast ID'),
])
def test_invalid_forecast_does_not_scan_other_datasets(forecast_rows, error):
    calls = []

    def query(**kwargs):
        calls.append(kwargs)
        return {"datas": forecast_rows}

    with pytest.raises(CannotCompute, match=error):
        load_bkn_rows("backward_plan", query, {"forecast_id": "0000023181", "product": "U00-000080", "substitute_enabled": False})
    assert len(calls) == 1


def test_exact_padded_id_wins_when_unpadded_business_record_also_exists():
    calls = []

    def query(**kwargs):
        calls.append(kwargs)
        if kwargs["ot_id"].endswith("_forecast"):
            assert kwargs["condition"]["value"] == "0000023181"
            return {"datas": [{"id": "0000023181", "material_number": "U00-000080"}]}
        return {"datas": []}

    load_bkn_rows("backward_plan", query, {"forecast_id": "0000023181", "substitute_enabled": False})
    assert len([c for c in calls if c["ot_id"].endswith("_forecast")]) == 1
