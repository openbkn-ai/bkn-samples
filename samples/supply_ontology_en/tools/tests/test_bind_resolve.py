"""Tests for bind_kn_resources: resource matching and run_bind orchestration."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bind_kn_resources import (
    _object_type_from_get,
    _sanitize_ot_for_bind_update,
    match_resource_id,
    run_bind,
)

MAP = Path(__file__).resolve().parents[1] / "mapping" / "object_table_map.yaml"


def test_match_resource_by_table_name():
    resources = [
        {"id": "r1", "name": "erp_material", "table_name": "erp_material"},
        {"id": "r2", "name": "other", "table_name": "x"},
    ]
    assert match_resource_id(resources, "erp_material") == "r1"


def test_match_resource_by_schema_qualified_name():
    resources = [
        {"id": "r4", "name": "public.erp_material", "source_identifier": "public.erp_material"},
    ]
    assert match_resource_id(resources, "erp_material") == "r4"


def test_match_resource_by_name_when_table_name_differs():
    resources = [
        {"id": "r3", "name": "public.hd_product_view", "table_name": "public.hd_product_view"},
    ]
    assert match_resource_id(resources, "hd_product_view") == "r3"


def test_match_missing():
    assert match_resource_id([], "erp_material") is None


def test_object_type_from_get_unwraps_entries():
    payload = {
        "entries": [
            {"id": "supply_ontology_en_material", "name": 'Material', "data_properties": []},
        ],
    }
    ot = _object_type_from_get(payload, "supply_ontology_en_material")
    assert ot["name"] == 'Material'
    assert ot["id"] == "supply_ontology_en_material"


def test_sanitize_ot_for_bind_update_clears_vector_model_id():
    ot = {
        "id": "x",
        "name": "n",
        "data_properties": [
            {
                "name": "material_name",
                "index_config": {
                    "vector_config": {"enabled": True, "model_id": "2031550503858606080"},
                },
            },
        ],
    }
    cleaned = _sanitize_ot_for_bind_update(ot)
    vector = cleaned["data_properties"][0]["index_config"]["vector_config"]
    assert vector["model_id"] == ""
    assert vector["enabled"] is False


def _fake_run_cmd_factory(*, record_updates: list[dict]):
    """Build run_cmd that simulates openbkn CLI without touching the network."""

    catalog_resources = [
        {"id": "res-material", "name": "erp_material", "table_name": "erp_material"},
        {"id": "res-product", "name": "hd_product_view", "table_name": "hd_product_view"},
    ]

    def fake_run_cmd(args: list[str]) -> str:
        if args[:4] == ["openbkn", "--json", "resource", "find"]:
            table = args[args.index("--name") + 1]
            matched = [r for r in catalog_resources if r["name"] == table or r["table_name"] == table]
            return json.dumps(matched)

        if args[:4] == ["openbkn", "--json", "resource", "list"]:
            return json.dumps(catalog_resources)

        if args[:5] == ["openbkn", "--json", "bkn", "object-type", "get"]:
            ot_id = args[-1]
            return json.dumps(
                {
                    "entries": [
                        {
                            "id": ot_id,
                            "name": ot_id,
                            "primary_keys": ["material_code"],
                            "data_properties": [
                                {
                                    "name": "material_code",
                                    "index_config": {
                                        "vector_config": {
                                            "enabled": True,
                                            "model_id": "2031550503858606080",
                                        },
                                    },
                                },
                            ],
                        },
                    ],
                }
            )

        if args[:5] == ["openbkn", "--json", "bkn", "object-type", "update"]:
            body_path = args[args.index("--body-file") + 1]
            record_updates.append(json.loads(Path(body_path).read_text(encoding="utf-8")))
            return json.dumps({"ok": True})

        raise AssertionError(f"unexpected CLI args: {args}")

    return fake_run_cmd


def test_run_bind_dry_run_skips_update():
    config = {
        "openbkn": {"kn_id": "supply_ontology_en"},
        "vega": {"catalog_id": "cat-1"},
    }
    mapping = {
        "objects": [
            {
                "object_type_id": "supply_ontology_en_material",
                "table": "erp_material",
                "bind": True,
            },
            {
                "object_type_id": "supply_ontology_en_mon_task",
                "table": "",
                "bind": False,
            },
        ],
    }
    updates: list[dict] = []
    report = run_bind(
        config,
        mapping,
        dry_run=True,
        run_cmd=_fake_run_cmd_factory(record_updates=updates),
    )

    assert updates == []
    assert len(report["bound"]) == 1
    assert report["bound"][0] == {
        "object_type_id": "supply_ontology_en_material",
        "table": "erp_material",
        "resource_id": "res-material",
    }
    assert report["skipped"] == [
        {"object_type_id": "supply_ontology_en_mon_task", "reason": "bind:false"},
    ]
    assert report["dry_run"] is True


def test_run_bind_applies_data_source_update():
    config = {
        "openbkn": {"kn_id": "supply_ontology_en"},
        "vega": {"catalog_id": "cat-1"},
    }
    mapping = {
        "objects": [
            {
                "object_type_id": "supply_ontology_en_product",
                "table": "hd_product_view",
                "bind": True,
            },
        ],
    }
    updates: list[dict] = []
    report = run_bind(
        config,
        mapping,
        dry_run=False,
        run_cmd=_fake_run_cmd_factory(record_updates=updates),
    )

    assert len(updates) == 1
    assert updates[0]["name"] == "supply_ontology_en_product"
    assert updates[0]["data_source"] == {"type": "resource", "id": "res-product"}
    vector = updates[0]["data_properties"][0]["index_config"]["vector_config"]
    assert vector["model_id"] == ""
    assert vector["enabled"] is False
    assert report["bound"][0]["resource_id"] == "res-product"


def test_run_bind_missing_resource_raises():
    config = {
        "openbkn": {"kn_id": "supply_ontology_en"},
        "vega": {"catalog_id": "cat-1"},
    }
    mapping = {
        "objects": [
            {
                "object_type_id": "supply_ontology_en_material",
                "table": "nonexistent_table",
                "bind": True,
            },
        ],
    }

    def empty_run_cmd(args: list[str]) -> str:
        if "resource" in args or "catalog" in args:
            return json.dumps([])
        raise AssertionError(args)

    with pytest.raises(RuntimeError, match="nonexistent_table"):
        run_bind(config, mapping, run_cmd=empty_run_cmd)
