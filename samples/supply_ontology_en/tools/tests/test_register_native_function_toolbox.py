from __future__ import annotations


def test_creation_and_update_publish_use_rules_on_the_existing_tool_contract(monkeypatch):
    import json
    import register_native_function_toolbox as registry
    from function_catalog import FUNCTION_CATALOG

    monkeypatch.setattr(registry, 'require_owned', lambda *args: None)
    for existing in (False, True):
        bodies = []
        def fake_call(args):
            if args[:2] == ['toolbox', 'list']:
                return {'data': [{'box_name': 'Supply_EN_Functions', 'box_id': 'box', 'status': 'published'}]}
            if args[:2] == ['tool', 'list']:
                return {'tools': [{'name': spec['name'], 'tool_id': operation, 'status': 'enabled'} for operation, spec in FUNCTION_CATALOG.items()] if existing else []}
            if args[0] == 'call' and args[1].startswith('/api/agent-operator-integration/v1/tool-box/box/tool'):
                payload = json.loads(args[args.index('-d') + 1]); bodies.append(payload)
                return {'success_ids': [payload['function_input']['name']]}
            return {}
        monkeypatch.setattr(registry, '_call', fake_call)
        registry.run(box_name='Supply_EN_Functions', apply=True)
        assert len(bodies) == len(FUNCTION_CATALOG)
        assert all('toolbox_id=owner_id' in b['use_rule'] for b in bodies)
        assert all('use_rule' not in b['function_input'] for b in bodies), 'usage rules belong to the Tool metadata, not Function inputs'


def test_existing_native_toolbox_updates_every_business_named_function(monkeypatch):
    import register_native_function_toolbox as registry
    from function_catalog import FUNCTION_CATALOG

    calls: list[list[str]] = []

    def fake_call(args):
        calls.append(args)
        if args[:2] == ["toolbox", "list"]:
            return {"data": [{"box_name": 'Supply_EN_Functions', "box_id": "box-1", "status": "published"}]}
        if args[:2] == ["tool", "list"]:
            return {"tools": [
                {"name": spec["name"], "tool_id": f"tool-{operation}", "status": "enabled"}
                for operation, spec in FUNCTION_CATALOG.items()
            ]}
        return {}

    monkeypatch.setattr(registry, "_call", fake_call)

    result = registry.run(box_name='Supply_EN_Functions', apply=True)

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
