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


def test_shared_contention_declares_object_items_in_020_function_metadata():
    """020 defaults an array without sub_parameters to string items."""
    from register_native_function_toolbox import _tool_inputs

    payload = _tool_inputs()["shared_contention"]
    demands = next(item for item in payload["inputs"] if item["name"] == "demands")
    assert demands["type"] == "array" and demands["required"] is True
    assert len(demands.get("sub_parameters", [])) == 1
    item = demands["sub_parameters"][0]
    assert item["type"] == "object"
    fields = {field["name"]: field for field in item["sub_parameters"]}
    assert set(fields) == {"product", "qty"}
    assert fields["product"]["type"] == "string"
    assert fields["qty"]["type"] == "number"
    assert all(field["required"] is True for field in fields.values())
    assert all(field["description"] for field in fields.values())
