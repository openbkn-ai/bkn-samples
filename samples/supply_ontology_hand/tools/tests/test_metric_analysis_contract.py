"""Independent CSV oracle for V1 query semantics and complete calendar months."""
import copy
import csv
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from power_layer import metric_series_match, verify_metrics

PACK = Path(__file__).resolve().parents[2]
ASSETS = PACK / "tools/assets"
DEFINITIONS = json.loads((ASSETS / "metrics-create.json").read_text())["entries"]
CASES = {c["id"]: c for c in json.loads((ASSETS / "metrics-analysis-examples.json").read_text())["cases"]}


def metric_for(case):
    metric = copy.deepcopy(next(m for m in DEFINITIONS if m["name"] == case["metric_name"]))
    metric["id"] = "metric"
    metric["lifecycle"]["status"] = "published"
    return metric


def runner(case, totals):
    metric = metric_for(case)
    values = iter(totals)
    def run(args):
        if args[4] == "list": return json.dumps({"entries": [{"definition": metric}]})
        assert args[args.index("--metric-version") + 1] == "1"
        body = json.loads(args[-1])
        assert "condition" not in body and "instant" not in body.get("time", {})
        return json.dumps({"model": {"metric_id": "metric", "version": 1}, "status": "ok",
                           "entries": [{"value": next(values), "status": "ok"}]})
    return run


def test_complete_consecutive_months_use_standard_typed_filter():
    zone = ZoneInfo("Asia/Shanghai")
    previous = None
    for query in CASES["signed_month_growth"]["queries"]:
        lower, upper = query["body"]["filter"]["children"]
        assert lower["comparison_operator"] == "gte" and upper["comparison_operator"] == "lt"
        assert lower["left"]["property_ref"]["property_name"] == "signing_date"
        start = datetime.fromisoformat(lower["right"][0]["value"]).replace(tzinfo=zone)
        end = datetime.fromisoformat(upper["right"][0]["value"]).replace(tzinfo=zone)
        assert start.strftime("%Y-%m") == query["period"]
        assert start.day == end.day == 1
        assert previous is None or start == previous
        previous = end


def test_monthly_and_growth_gold_match_independent_locked_csv():
    monthly = defaultdict(Decimal)
    with (PACK / "data/sales_order.csv").open() as stream:
        for row in csv.DictReader(stream): monthly[row["signing_date"][:7]] += Decimal(row["signing_quantity"])
    expected = CASES["signed_monthly"]["expected_series"][0]
    assert expected["periods"] == sorted(monthly)
    assert expected["values"] == [monthly[p] for p in expected["periods"]]
    months = expected["periods"]
    assert CASES["signed_month_growth"]["expected_series"][0]["growth_values"] == [monthly[b]-monthly[a] for a,b in zip(months, months[1:])]


def test_temporal_metric_references_actual_date_property():
    metric = metric_for(CASES["signed_month_growth"])
    ref = metric["query_capabilities"]["time_dimensions"][0]
    network = json.loads((PACK / "kn" / (PACK.name + ".json")).read_text())
    objects = network.get("object_types") or network.get("objectTypes") or network["entries"][0]["object_types"]
    owner = next(o for o in objects if o["id"] == ref["object_type_id"])
    date = next(p for p in owner["data_properties"] if p["name"] == ref["property_name"])
    assert date["type"] == date["mapped_field"]["type"] == "date"


def test_calendar_queries_verify_every_month_and_baseline_before_arithmetic():
    case = CASES["signed_month_growth"]
    result = verify_metrics("network", [case], run_cmd=runner(case,[6083,5319,4565,4429]), business_timezone="Asia/Shanghai")
    assert not result["failed"]
    assert len(result["passed"][0]["queries"]) == 4
    assert result["passed"][0]["actual"][0]["growth_values"] == [-764,-754,-136]
    # Equal errors preserve all differences, but must fail source totals.
    assert verify_metrics("network", [case], run_cmd=runner(case,[6084,5320,4566,4430]), business_timezone="Asia/Shanghai")["failed"]
    shortened = copy.deepcopy(case)
    shortened["queries"][2]["body"]["filter"]["children"][1]["right"][0]["value"] = "2026-05-31"
    assert verify_metrics("network", [shortened], run_cmd=runner(case,[6083,5319,4517,4429]), business_timezone="Asia/Shanghai")["failed"]


def test_monthly_series_retains_all_four_periods():
    case = CASES["signed_monthly"]
    report = verify_metrics("network", [case], run_cmd=runner(case,[6083,5319,4565,4429]), business_timezone="Asia/Shanghai")
    assert report["passed"][0]["actual"][0]["time_strs"] == ["2026-03","2026-04","2026-05","2026-06"]


def test_series_rejects_later_wrong_bucket_extra_groups_and_bad_timezone():
    expected=[{"labels":{},"periods":["2026-03","2026-04"],"values":[6083,5319]}]
    actual=[{"labels":{},"time_strs":["2026-03-01","2026-04-01"],"values":[6083,5319]}]
    assert metric_series_match(actual,expected)
    actual[0]["values"][1]=5320
    assert not metric_series_match(actual,expected)
    assert not metric_series_match(actual+actual,expected)
    assert not metric_series_match(actual,expected,"Missing/Zone")


def test_grouped_proportion_gold_has_complete_independent_csv_denominator():
    counts=defaultdict(int)
    with (PACK / "data/erp_material.csv").open() as stream:
        for row in csv.DictReader(stream): counts[row["materialattr"]]+=1
    for group in CASES["material_attr_proportion"]["expected_series"]:
        count=counts[next(iter(group["labels"].values()))]
        assert group["values"] == [count]
        assert group["proportions"] == [count/sum(counts.values())*100]


def test_proportion_uses_actual_native_group_values_and_rejects_missing_group():
    case=CASES["material_attr_proportion"]
    metric=metric_for(case)
    entries=[{"dimensions":g["labels"],"value":g["values"][0],"status":"ok"} for g in case["expected_series"]]
    def run(args):
        if args[4]=="list":return json.dumps({"entries":[{"definition":metric}]})
        return json.dumps({"model":{"metric_id":"metric","version":1},"entries":entries,"status":"ok"})
    assert verify_metrics("network",[case],run_cmd=run)["passed"]
    entries.pop()
    assert verify_metrics("network",[case],run_cmd=run)["failed"]
