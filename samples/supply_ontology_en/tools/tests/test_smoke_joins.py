"""Tests for smoke_test: join hit rates and orchestration with mocked CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from sqlalchemy import create_engine

from load_sample_data import load_all
from smoke_test import (
    compute_join_hit_rate,
    join_hit_rate,
    parse_query_rows,
    run_join_checks,
    run_smoke,
)

PACK = Path(__file__).resolve().parents[2]
SAMPLE = PACK / "data"
MAP = PACK / "tools" / "mapping" / "object_table_map.yaml"


def test_join_hit_rate_all_match():
    left = ["a", "b", "c", None, ""]
    right = ["c", "b", "a", "x"]
    rate, hits, total = join_hit_rate(left, right)
    assert total == 3
    assert hits == 3
    assert rate == 1.0


def test_join_hit_rate_partial():
    left = ["a", "b", "c"]
    right = ["a", "x"]
    rate, hits, total = join_hit_rate(left, right)
    assert total == 3
    assert hits == 1
    assert rate == pytest.approx(1 / 3)


def test_join_hit_rate_distinct_left_keys():
    """Duplicate left keys count once toward the denominator."""
    left = ["a", "a", "b"]
    right = ["a"]
    rate, hits, total = join_hit_rate(left, right)
    assert total == 2
    assert hits == 1
    assert rate == 0.5


def test_join_hit_rate_empty_left():
    rate, hits, total = join_hit_rate([], ["a"])
    assert total == 0
    assert hits == 0
    assert rate == 0.0


def test_parse_query_rows_list_and_dict():
    assert parse_query_rows([{"id": 1}, {"id": 2}]) == 2
    assert parse_query_rows({"items": [{"id": 1}]}) == 1
    assert parse_query_rows({"datas": [{"id": 1}, {"id": 2}]}) == 2
    assert parse_query_rows({"total": 5}) == 5


def test_compute_join_hit_rate_sqlite(tmp_path):
    mapping = yaml.safe_load(MAP.read_text(encoding="utf-8"))
    mapping["load_order"] = [
        "erp_material",
        "hd_product_view",
        "sales_order",
    ]
    engine = create_engine(f"sqlite:///{tmp_path / 't.db'}")
    cfg = {
        "database": {"engine": "sqlite"},
        "load": {"sample_dir": str(SAMPLE), "mode": "recreate", "on_error": "stop"},
    }
    load_all(engine, cfg, mapping)

    check = {
        "name": "so_to_product",
        "left_table": "sales_order",
        "left_key": "product_code",
        "right_table": "hd_product_view",
        "right_key": "material_code",
        "expect_hit_rate": 1.0,
    }
    result = compute_join_hit_rate(engine, check, "sqlite")
    assert result["hit_rate"] == 1.0
    assert result["passed"] is True
    assert result["left_key_count"] > 0


def test_run_join_checks_all_pass(tmp_path):
    mapping = yaml.safe_load(MAP.read_text(encoding="utf-8"))
    mapping["load_order"] = [
        "erp_material",
        "hd_product_view",
        "sales_order",
        "erp_material_bom",
    ]
    mapping["join_checks"] = [
        {
            "name": "so_to_product",
            "left_table": "sales_order",
            "left_key": "product_code",
            "right_table": "hd_product_view",
            "right_key": "material_code",
            "expect_hit_rate": 1.0,
        },
    ]
    engine = create_engine(f"sqlite:///{tmp_path / 't2.db'}")
    cfg = {
        "database": {"engine": "sqlite"},
        "load": {"sample_dir": str(SAMPLE), "mode": "recreate", "on_error": "stop"},
    }
    load_all(engine, cfg, mapping)

    results = run_join_checks(engine, mapping, "sqlite")
    assert len(results) == 1
    assert results[0]["passed"] is True


def _fake_smoke_run_cmd(*, kn_name: str = 'Supply Chain EN'):
    def fake_run_cmd(args: list[str]) -> str:
        if args[:4] == ["openbkn", "--json", "bkn", "get"]:
            return json.dumps({"id": args[-1], "name": kn_name})

        if args[:5] == ["openbkn", "--json", "bkn", "object-type", "query"]:
            return json.dumps({"items": [{"id": "row-1"}]})

        raise AssertionError(f"unexpected CLI args: {args}")

    return fake_run_cmd


def test_run_smoke_passes_with_mock_cli(tmp_path):
    mapping = yaml.safe_load(MAP.read_text(encoding="utf-8"))
    mapping["load_order"] = ["erp_material", "hd_product_view", "sales_order"]
    mapping["join_checks"] = [
        {
            "name": "so_to_product",
            "left_table": "sales_order",
            "left_key": "product_code",
            "right_table": "hd_product_view",
            "right_key": "material_code",
            "expect_hit_rate": 1.0,
        },
    ]
    engine = create_engine(f"sqlite:///{tmp_path / 't3.db'}")
    cfg = {
        "database": {"engine": "sqlite"},
        "load": {"sample_dir": str(SAMPLE), "mode": "recreate", "on_error": "stop"},
    }
    load_all(engine, cfg, mapping)

    config = {
        "openbkn": {
            "kn_id": "supply_ontology_en",
            "kn_name": 'Supply Chain EN',
        },
        "database": {"engine": "sqlite", "database": str(tmp_path / "t3.db")},
    }
    report_path = tmp_path / "smoke_report.json"

    passed, report = run_smoke(
        config,
        mapping,
        engine=engine,
        run_cmd=_fake_smoke_run_cmd(),
        report_path=report_path,
    )

    assert passed is True
    assert report["passed"] is True
    assert report["kn_check"]["passed"] is True
    assert all(row["passed"] for row in report["object_type_checks"])
    assert all(row["passed"] for row in report["join_checks"])
    assert report_path.is_file()


def test_run_smoke_fails_on_kn_name_mismatch(tmp_path):
    mapping = yaml.safe_load(MAP.read_text(encoding="utf-8"))
    mapping["join_checks"] = []
    engine = create_engine("sqlite:///:memory:")
    config = {
        "openbkn": {"kn_id": "supply_ontology_en", "kn_name": "expected-name"},
        "database": {"engine": "sqlite", "database": ":memory:"},
    }

    passed, report = run_smoke(
        config,
        mapping,
        engine=engine,
        run_cmd=_fake_smoke_run_cmd(kn_name="wrong-name"),
        report_path=tmp_path / "fail.json",
    )

    assert passed is False
    assert report["kn_check"]["passed"] is False
