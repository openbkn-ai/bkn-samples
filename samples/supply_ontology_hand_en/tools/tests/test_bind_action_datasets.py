from bind_action_datasets import build_bindings, discover_catalog, run_bind


def test_build_bindings_qualifies_schema_and_uses_kn_id():
    mapping = {"bindings": [{"object_type_id": "supply_ontology_hand_mon_task", "dataset": "sc_plan_monitor_task"}]}
    assert build_bindings(mapping, kn_id="supply_ontology_hand_en", schema="public") == [
        {"kn_id": "supply_ontology_hand_en", "object_type_id": "supply_ontology_hand_mon_task", "dataset": "public.sc_plan_monitor_task"}
    ]


def test_build_bindings_expands_schema_placeholder():
    mapping = {"bindings": [{"object_type_id": "ot1", "dataset": "${ACTION_DATASET_SCHEMA}.sc_pr_decision"}]}
    assert build_bindings(mapping, kn_id="supply_ontology_hand_en", schema="public")[0]["dataset"] == "public.sc_pr_decision"


def test_discover_catalog_waits_for_new_action_tables():
    calls = []

    def run_cmd(args):
        calls.append(args)
        if args[2:5] == ["vega", "catalog", "discover"]:
            return '{"id":"task-1"}'
        if args[2:5] == ["vega", "discover-task", "get"]:
            return '{"id":"task-1","status":"completed"}'
        raise AssertionError(f"unexpected command: {args}")

    discover_catalog("catalog1", run_cmd=run_cmd)
    assert calls == [
        ["openbkn", "--json", "vega", "catalog", "discover", "catalog1"],
        ["openbkn", "--json", "vega", "discover-task", "get", "task-1"],
    ]


def test_dry_run_does_not_update_object_type():
    calls = []
    report = run_bind(
        {"openbkn": {"kn_id": "supply_ontology_hand_en"}, "database": {"schema": "public"}},
        {"bindings": [{"object_type_id": "ot1", "dataset": "sc_plan_monitor_task"}]},
        dry_run=True,
        run_cmd=lambda args: calls.append(args),
    )
    assert report["ok"] is True
    assert calls == []


def test_apply_resolves_catalog_resource_and_uses_resource_data_source():
    calls = []

    def run_cmd(args):
        calls.append(args)
        if args[2:4] == ["resource", "find"]:
            return '{"entries":[{"id":"resource-task"}]}'
        if args[2:5] == ["bkn", "object-type", "get"]:
            return '{"entries":[{"id":"ot1","name":"Monitor Task","data_properties":[]}]}'
        return "{}"

    report = run_bind(
        {"openbkn": {"kn_id": "supply_ontology_hand_en"}, "vega": {"catalog_id": "catalog1"}, "database": {"schema": "public"}},
        {"bindings": [{"object_type_id": "ot1", "dataset": "sc_plan_monitor_task"}]},
        dry_run=False,
        run_cmd=run_cmd,
    )
    assert report["bindings"][0]["resource_id"] == "resource-task"
    assert any("--body-file" in call for call in calls)
