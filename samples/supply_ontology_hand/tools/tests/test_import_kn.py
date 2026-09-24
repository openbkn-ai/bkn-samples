"""Tests for import_kn step-2 script."""

from __future__ import annotations

import json
from pathlib import Path

import import_kn as import_kn_module
from import_kn import import_kn

KN = Path(__file__).resolve().parents[2] / "kn" / "supply_ontology_hand.json"


def test_import_kn_dry_run():
    report = import_kn(KN, dry_run=True)
    assert report["kn_id"] == "supply_ontology_hand"
    assert report["kn_name"] == "供应链本体知识网络-手工版"
    assert report["action"] == "would_import"


def test_kn_json_has_required_fields():
    payload = json.loads(KN.read_text(encoding="utf-8"))
    assert payload["id"] == "supply_ontology_hand"
    assert len(payload["id"]) <= 32
    assert isinstance(payload.get("object_types"), list)
    assert len(payload["object_types"]) > 0


def test_import_retries_without_index_config_when_platform_rejects_it(tmp_path, monkeypatch):
    payload = {
        "id": "test_network",
        "name": "Test network",
        "object_types": [
            {
                "data_properties": [
                    {
                        "name": "material_name",
                        "index_config": {"vector_config": {"enabled": True}},
                    },
                ],
            },
        ],
    }
    json_path = tmp_path / "kn.json"
    json_path.write_text(json.dumps(payload), encoding="utf-8")
    posted_bodies = []
    get_calls = 0

    def fake_run_cmd(args):
        nonlocal get_calls
        if args[2] == "call":
            posted_bodies.append(json.loads(args[-1]))
            if len(posted_bodies) == 1:
                raise RuntimeError("数据属性 material_name 不再支持 index_config")
            return json.dumps({"ok": True})
        if args[2:4] == ["bkn", "get"]:
            get_calls += 1
            if get_calls == 1:
                raise RuntimeError("not found")
            return json.dumps({"id": "test_network", "name": "Test network"})
        raise AssertionError(args)

    monkeypatch.setattr(import_kn_module, "run_cmd", fake_run_cmd)

    report = import_kn_module.import_kn(json_path)

    assert report["index_config_stripped"] is True
    assert len(posted_bodies) == 2
    assert "index_config" in posted_bodies[0]["object_types"][0]["data_properties"][0]
    assert "index_config" not in posted_bodies[1]["object_types"][0]["data_properties"][0]
    assert "index_config" in json.loads(json_path.read_text(encoding="utf-8"))["object_types"][0]["data_properties"][0]


def test_import_auto_embedding_strips_stale_vector_config_when_no_default_exists(tmp_path, monkeypatch):
    payload = {
        "id": "test_network",
        "name": "Test network",
        "object_types": [
            {
                "data_properties": [
                    {
                        "name": "material_name",
                        "index_config": {"vector_config": {"enabled": True, "model_id": "stale"}},
                    },
                ],
            },
        ],
    }
    json_path = tmp_path / "kn.json"
    json_path.write_text(json.dumps(payload), encoding="utf-8")
    posted_bodies = []
    get_calls = 0

    def fake_run_cmd(args):
        nonlocal get_calls
        if args[2:5] == ["model", "small", "get-default"]:
            return json.dumps({})
        if args[2] == "call":
            posted_bodies.append(json.loads(args[-1]))
            return json.dumps({"ok": True})
        if args[2:4] == ["bkn", "get"]:
            get_calls += 1
            if get_calls == 1:
                raise RuntimeError("not found")
            return json.dumps({"id": "test_network", "name": "Test network"})
        raise AssertionError(args)

    monkeypatch.setattr(import_kn_module, "run_cmd", fake_run_cmd)

    report = import_kn_module.import_kn(json_path, embedding_mode="auto")

    assert report["embedding_mode"] == "keyword"
    assert "index_config" not in posted_bodies[0]["object_types"][0]["data_properties"][0]


def test_import_skips_an_existing_matching_knowledge_network(tmp_path, monkeypatch):
    json_path = tmp_path / "kn.json"
    json_path.write_text(json.dumps({"id": "test_network", "name": "Test network"}), encoding="utf-8")

    def fake_run_cmd(args):
        assert args[2:4] == ["bkn", "get"]
        return json.dumps({"id": "test_network", "name": "Test network"})

    monkeypatch.setattr(import_kn_module, "run_cmd", fake_run_cmd)

    report = import_kn_module.import_kn(json_path)

    assert report["action"] == "already_present"
    assert report["verified"] is True
