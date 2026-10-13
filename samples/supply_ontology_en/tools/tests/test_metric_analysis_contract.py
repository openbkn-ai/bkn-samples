"""Independent CSV oracle and full-series regression coverage for issue #23."""

import copy
import csv
import json
from collections import defaultdict
from decimal import Decimal
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

from power_layer import calendar_month_growth, metric_series_match, verify_metrics

PACK = Path(__file__).resolve().parents[2]
ASSETS = PACK / "tools" / "assets"


def test_query_windows_preserve_complete_business_months():
    payload = json.loads((ASSETS / "metrics-analysis-examples.json").read_text())
    assert payload["business_timezone"] == "Asia/Shanghai"
    cases = {c["id"]: c for c in payload["cases"]}
    zone = ZoneInfo(payload["business_timezone"])
    monthly = cases["signed_monthly"]["body"]["time"]
    assert datetime.fromtimestamp(monthly["start"] / 1000, zone).isoformat() == "2026-03-01T00:00:00+08:00"
    assert datetime.fromtimestamp(monthly["end"] / 1000, zone).isoformat() == "2026-06-30T23:59:59.999000+08:00"
    instant = cases["signed_april_instant"]["body"]
    assert instant["time"] == {"instant": True}
    lower, upper = instant["condition"]["sub_conditions"]
    assert (lower["field"], lower["operation"], upper["field"], upper["operation"]) == ("signing_date", ">=", "signing_date", "<")
    assert datetime.fromtimestamp(lower["value"] / 1000, zone).isoformat() == "2026-04-01T00:00:00+08:00"
    assert datetime.fromtimestamp(upper["value"] / 1000, zone).isoformat() == "2026-05-01T00:00:00+08:00"
    growth = cases["signed_month_growth"]
    assert "body" not in growth
    assert growth["calculation"] == "calendar_month_growth"
    for query in growth["queries"]:
        lower, upper = query["body"]["condition"]["sub_conditions"]
        start = datetime.fromtimestamp(lower["value"] / 1000, zone)
        end = datetime.fromtimestamp(upper["value"] / 1000, zone)
        assert start.strftime("%Y-%m") == query["period"]
        assert start.day == end.day == 1
        assert lower["operation"] == ">=" and upper["operation"] == "<"


def test_temporal_definition_and_periods_match_existing_csv():
    definitions = json.loads((ASSETS / "metrics-create.json").read_text())["entries"]
    metric = next(m for m in definitions if m["name"] == 'Signing Events')
    assert metric["time_dimension"] == {"property": "signing_date", "default_range_policy": "none"}
    network = json.loads((PACK / "kn" / "supply_ontology_en.json").read_text())
    # Check the actual mapped object property rather than assuming a date-like name.
    objects = network.get("object_types") or network.get("objectTypes")
    if objects is None:
        objects = network["entries"][0]["object_types"]
    sales = next(o for o in objects if o["id"] == metric["scope_ref"])
    date = next(p for p in sales["data_properties"] if p["name"] == "signing_date")
    assert date["type"] == date["mapped_field"]["type"] == "date"
    monthly = defaultdict(Decimal)
    with (PACK / "data" / "sales_order.csv").open() as stream:
        for row in csv.DictReader(stream):
            monthly[row["signing_date"][:7]] += Decimal(row["signing_quantity"])
    cases = {c["id"]: c for c in json.loads((ASSETS / "metrics-analysis-examples.json").read_text())["cases"]}
    expected = cases["signed_monthly"]["expected_series"][0]
    assert expected["periods"] == sorted(monthly)
    assert expected["values"] == [monthly[p] for p in expected["periods"]]
    growth = cases["signed_month_growth"]["expected_series"][0]
    months = expected["periods"]
    assert growth["growth_values"] == [monthly[months[i]] - monthly[months[i - 1]] for i in range(1, 4)]


def test_capability_matrix_covers_every_metric_without_inventing_snapshot_time():
    metrics = json.loads((ASSETS / "metrics-create.json").read_text())["entries"]
    capabilities = json.loads((ASSETS / "metrics-capabilities.json").read_text())["metrics"]
    assert {m["name"] for m in metrics} == {c["metric_name"] for c in capabilities}
    for capability in capabilities:
        if not capability["time_property"]:
            assert "trend" not in capability["supported_modes"]
            assert "sameperiod" not in capability["supported_modes"]
            assert not capability["period_filter_supported"]


def test_series_verification_rejects_wrong_later_bucket_period_and_extra_groups():
    expected = [{"labels": {"status": "open"}, "periods": ["2026-03", "2026-04"], "values": [6083, 5319]}]
    actual = [{"labels": {"status": "open"}, "time_strs": ["2026-03-01", "2026-04-01"], "values": [6083, 5319]}]
    assert metric_series_match(actual, expected)
    wrong = copy.deepcopy(actual)
    wrong[0]["values"][1] = 5320
    assert not metric_series_match(wrong, expected)
    wrong = copy.deepcopy(actual)
    wrong[0]["time_strs"][1] = "2026-05-01"
    assert not metric_series_match(wrong, expected)
    assert not metric_series_match(actual + actual, expected)
    assert not metric_series_match(actual, expected + expected)


def test_series_order_does_not_change_grouped_proportion_validation():
    expected = [{"labels": {"attr": "A"}, "values": [3], "proportions": [75]},
                {"labels": {"attr": "B"}, "values": [1], "proportions": [25]}]
    assert metric_series_match(list(reversed(expected)), expected)
    wrong = copy.deepcopy(expected)
    wrong[0]["proportions"] = [74]
    assert not metric_series_match(wrong, expected)


def test_month_bucket_is_compared_in_declared_business_timezone():
    expected = [{"labels": {}, "periods": ["2026-04"], "values": [5319]}]
    actual = [{"labels": {}, "times": [1774972800000], "values": [5319]}]
    assert not metric_series_match(actual, expected)
    assert metric_series_match(actual, expected, "Asia/Shanghai")
    actual[0]["time_strs"] = ["2026-03-31T16:00:00Z"]
    assert metric_series_match(actual, expected, "Asia/Shanghai")
    assert not metric_series_match(actual, expected, "Missing/Timezone")


def test_metric_verifier_forwards_business_timezone_to_bucket_check():
    def run(command):
        if "list" in command:
            return json.dumps({"entries": [{"id": "metric", "name": "sales"}]})
        return json.dumps({"datas": [{"labels": {}, "times": [1774972800000], "values": [5319]}]})
    case = {"id": "april", "metric_name": "sales", "expected_series": [
        {"labels": {}, "periods": ["2026-04"], "values": [5319]}]}
    assert verify_metrics("network", [case], run_cmd=run)["failed"]
    assert verify_metrics("network", [case], run_cmd=run, business_timezone="Asia/Shanghai")["passed"]


def test_verify_metrics_checks_series_instead_of_only_the_first_value():
    def run(command):
        if "list" in command:
            return json.dumps({"entries": [{"id": "metric", "name": "sales"}]})
        return json.dumps({"datas": [{"labels": {}, "time_strs": ["2026-03-01", "2026-04-01"],
                                      "values": [6083, 5320]}]})

    case = {"id": "monthly", "metric_name": "sales", "expected_series": [
        {"labels": {}, "periods": ["2026-03", "2026-04"], "values": [6083, 5319]}]}
    report = verify_metrics("network", [case], run_cmd=run)
    assert not report["passed"]
    assert report["failed"][0]["id"] == "monthly"


def test_grouped_proportion_gold_uses_independent_csv_denominators():
    cases = {c["id"]: c for c in json.loads((ASSETS / "metrics-analysis-examples.json").read_text())["cases"]}
    attrs = defaultdict(int)
    with (PACK / "data" / "erp_material.csv").open() as stream:
        for row in csv.DictReader(stream):
            attrs[row["materialattr"]] += 1
    for group in cases["material_attr_proportion"]["expected_series"]:
        count = attrs[group["labels"]["materialattr"]]
        assert group["values"] == [count]
        assert group["proportions"] == [count / sum(attrs.values()) * 100]
    statuses = defaultdict(Decimal)
    with (PACK / "data" / "sales_order.csv").open() as stream:
        for row in csv.DictReader(stream):
            if row["signing_date"].startswith("2026-04"):
                statuses[row["order_status"]] += Decimal(row["signing_quantity"])
    for group in cases["signed_month_status_proportion"]["expected_series"]:
        quantity = statuses[group["labels"]["order_status"]]
        assert group["values"] == [quantity]
        assert group["proportions"] == [float(quantity / sum(statuses.values()) * 100)]


def test_calendar_month_acceptance_queries_each_complete_month_and_verifies_baseline():
    case = next(c for c in json.loads((ASSETS / "metrics-analysis-examples.json").read_text())["cases"]
                if c["id"] == "signed_month_growth")
    def runner(totals):
        values = iter(totals)
        def run(command):
            if "list" in command:
                return json.dumps({"entries": [{"id": "metric", "name": case["metric_name"]}]})
            body = json.loads(command[-1])
            assert body["time"] == {"instant": True} and "metrics" not in body
            return json.dumps({"datas": [{"labels": {}, "values": [next(values)]}]})
        return run
    good = verify_metrics("network", [case], run_cmd=runner([6083, 5319, 4565, 4429]), business_timezone="Asia/Shanghai")
    assert len(good["passed"][0]["queries"]) == 4
    assert good["passed"][0]["actual"][0]["growth_values"] == [-764, -754, -136]
    # Equal errors in all months preserve differences but must still fail monthly evidence.
    bad = verify_metrics("network", [case], run_cmd=runner([6084, 5320, 4566, 4430]), business_timezone="Asia/Shanghai")
    assert bad["failed"]
    may30 = copy.deepcopy(case)
    may30["queries"][2]["body"]["condition"]["sub_conditions"][1]["value"] -= 86400000
    assert verify_metrics("network", [may30], run_cmd=runner([6083, 5319, 4517, 4429]), business_timezone="Asia/Shanghai")["failed"]


def test_calendar_month_acceptance_rejects_missing_or_ambiguous_totals():
    case = next(c for c in json.loads((ASSETS / "metrics-analysis-examples.json").read_text())["cases"]
                if c["id"] == "signed_month_growth")
    for datas in [[], [{"values": [None]}], [{"values": [1, 2]}], [{"values": [True]}],
                  [{"values": [1]}, {"values": [2]}]]:
        def run(command):
            if "list" in command:
                return json.dumps({"entries": [{"id": "metric", "name": case["metric_name"]}]})
            return json.dumps({"datas": datas})
        assert verify_metrics("network", [case], run_cmd=run, business_timezone="Asia/Shanghai")["failed"]
