from __future__ import annotations


def test_existing_native_toolbox_updates_every_business_named_function(monkeypatch):
    import register_native_function_toolbox as registry
    from function_catalog import FUNCTION_CATALOG

    calls: list[list[str]] = []

    def fake_call(args):
        calls.append(args)
        if args[:2] == ["toolbox", "list"]:
            return {"data": [{"box_name": "供应链原生计算函数", "box_id": "box-1", "status": "published"}]}
        if args[:2] == ["tool", "list"]:
            return {"tools": [
                {"name": spec["name"], "tool_id": f"tool-{operation}", "status": "enabled"}
                for operation, spec in FUNCTION_CATALOG.items()
            ]}
        return {}

    monkeypatch.setattr(registry, "_call", fake_call)

    result = registry.run(box_name="供应链原生计算函数", apply=True)

    assert result["box_id"] == "box-1"
    assert set(result["tool_ids"]) == set(FUNCTION_CATALOG)
    assert result["legacy_tool_disabled"] is False
    updates = [call for call in calls if call[:2] == ["call", "/api/agent-operator-integration/v1/tool-box/box-1/tool/tool-bom_list"]]
    assert updates
    assert "supply_chain_compute" not in updates[0][5]


def test_action_update_accepts_empty_success_without_masking_bad_responses(monkeypatch):
    import json
    import subprocess
    import pytest
    import register_native_function_toolbox as registry

    args = ["call", "/api/bkn-backend/v1/knowledge-networks/sample/action-types/draft", "-X", "PUT", "-d", "{}"]
    for stdout in ("", "\n", " \n\t"):
        monkeypatch.setattr(registry.subprocess, "run", lambda *a, _stdout=stdout, **kw: subprocess.CompletedProcess(a, 0, _stdout, ""))
        assert registry._call(args) == {}
    monkeypatch.setattr(registry.subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(a, 0, '{"updated":true}', ""))
    assert registry._call(args) == {"updated": True}
    monkeypatch.setattr(registry.subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(a, 0, "not-json", ""))
    with pytest.raises(json.JSONDecodeError):registry._call(args)
    monkeypatch.setattr(registry.subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(a, 1, "", "permission denied"))
    with pytest.raises(RuntimeError, match="permission denied"):registry._call(args)

    monkeypatch.setattr(registry.subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(a, 0, "\n", ""))
    for read in (["toolbox", "list", "--limit", "100"], ["tool", "list", "--toolbox", "box", "--all"], ["call", "/api/bkn-backend/v1/knowledge-networks", "-X", "GET"]):
        with pytest.raises(json.JSONDecodeError):registry._call(read)


def test_shared_demand_parameters_describe_object_items_not_string_items():
    from register_native_function_toolbox import _operation_inputs

    demands = next(p for p in _operation_inputs('shared_contention') if p['name'] == 'demands')
    assert demands['type'] == 'array'
    items, = demands.get('sub_parameters', [])
    assert items['type'] == 'object'
    fields = {p['name']: p for p in items['sub_parameters']}
    assert set(fields) == {'product', 'qty'}
    assert fields['product']['type'] == 'string' and fields['product']['required']
    assert fields['qty']['type'] == 'number' and fields['qty']['required']
