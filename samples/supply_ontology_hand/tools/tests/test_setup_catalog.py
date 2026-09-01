"""Tests for setup_catalog step-4 automation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from setup_catalog import (
    _single_catalog,
    build_connector_config,
    expected_tables,
    run_catalog_setup,
    verify_tables,
    write_catalog_id_to_config,
)

MAP = Path(__file__).resolve().parents[1] / "mapping" / "object_table_map.yaml"


def test_catalog_get_unwraps_current_entries_envelope():
    assert _single_catalog({"entries": [{"id": "cat-1", "enabled": True}]}, "cat-1") == {
        "id": "cat-1",
        "enabled": True,
    }


def test_build_connector_config_uses_catalog_host_override():
    cfg = {
        "database": {
            "engine": "postgres",
            "host": "127.0.0.1",
            "port": 5432,
            "database": "supply_demo_hand",
            "user": "leecky",
            "password": "",
            "schema": "public",
        },
        "vega": {"catalog_host": "host.docker.internal"},
    }
    conn = build_connector_config(cfg)
    assert conn["host"] == "host.docker.internal"
    assert conn["database"] == "supply_demo_hand"
    assert conn["schemas"] == ["public"]
    assert conn["password"] == ""
    assert "options" not in conn


def test_build_connector_config_forwards_explicit_options_only():
    cfg = {
        "database": {
            "host": "127.0.0.1",
            "port": 5432,
            "database": "supply_demo_hand",
            "user": "leecky",
        },
        "vega": {"connector_options": {"sslmode": "disable"}},
    }

    conn = build_connector_config(cfg)

    assert conn["options"] == {"sslmode": "disable"}


def test_build_connector_config_mysql_engine_name():
    cfg = {
        "database": {
            "engine": "mysql",
            "host": "127.0.0.1",
            "port": 3306,
            "database": "supply_demo_hand",
            "user": "root",
            "password": "secret",
        },
        "vega": {},
    }
    conn = build_connector_config(cfg)
    assert conn["password"] == "secret"
    assert conn["schemas"] == ["public"]


def test_expected_tables_count():
    import yaml

    mapping = yaml.safe_load(MAP.read_text(encoding="utf-8"))
    assert len(expected_tables(mapping)) == 12


def test_run_catalog_setup_create_enable_discover():
    calls: list[list[str]] = []

    def fake_run_cmd(args: list[str]) -> str:
        calls.append(args)
        if args[:5] == ["openbkn", "--json", "vega", "catalog", "list"]:
            return json.dumps({"entries": []})
        if args[:5] == ["openbkn", "--json", "vega", "catalog", "create"]:
            return json.dumps({"id": "cat-new", "name": "supply-demo-hand", "enabled": False})
        if args[:5] == ["openbkn", "--json", "vega", "catalog", "enable"]:
            return json.dumps({"id": "cat-new", "enabled": True})
        if args[:5] == ["openbkn", "--json", "vega", "catalog", "test-connection"]:
            return json.dumps({"ok": True})
        if args[:5] == ["openbkn", "--json", "vega", "catalog", "discover"]:
            return json.dumps({"id": "task-1"})
        if args[:5] == ["openbkn", "--json", "vega", "discover-task", "get"]:
            return json.dumps({"id": "task-1", "status": "completed"})
        if args[:5] == ["openbkn", "--json", "vega", "catalog", "resources"]:
            import yaml

            mapping = yaml.safe_load(MAP.read_text(encoding="utf-8"))
            resources = [{"name": t, "table_name": t} for t in mapping["load_order"]]
            return json.dumps({"entries": resources})
        raise AssertionError(f"unexpected command: {args}")

    import yaml

    mapping = yaml.safe_load(MAP.read_text(encoding="utf-8"))
    config = {
        "database": {
            "engine": "postgres",
            "host": "127.0.0.1",
            "port": 5432,
            "database": "supply_demo_hand",
            "user": "leecky",
            "password": "",
            "schema": "public",
        },
        "vega": {"catalog_name": "supply-demo-hand"},
    }

    report = run_catalog_setup(config, mapping, run_cmd=fake_run_cmd)
    assert report["catalog_id"] == "cat-new"
    assert report["verification"]["ok"] is True
    assert any(step.get("action") == "create" for step in report["steps"])
    assert any(step.get("action") == "discover" for step in report["steps"])


def test_write_catalog_id_to_config(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "vega:\n  catalog_id: \"\"\n  catalog_name: demo\n",
        encoding="utf-8",
    )
    write_catalog_id_to_config(cfg, "cat-123")
    text = cfg.read_text(encoding="utf-8")
    assert "catalog_id: 'cat-123'" in text or 'catalog_id: "cat-123"' in text or "catalog_id: cat-123" in text


def test_verify_tables_missing():
    def fake_run_cmd(args: list[str]) -> str:
        return json.dumps({"entries": [{"name": "erp_material", "table_name": "erp_material"}]})

    import yaml

    mapping = yaml.safe_load(MAP.read_text(encoding="utf-8"))
    result = verify_tables("cat-1", mapping, run_cmd=fake_run_cmd)
    assert result["ok"] is False
    assert "erp_material" not in result["missing"]
    assert len(result["missing"]) == 11
