import json

from setup_kit_plan_dataset import DATASET_NAME, dataset_schema, history_rows, plan_object, run

CONFIG = {"openbkn": {"kn_id": "supply_ontology_hand"}, "vega": {"catalog_id": "cat-1"}}


class Cli:
    def __init__(self, existing=None):
        self.calls = []
        self.existing = existing or []

    def __call__(self, args):
        self.calls.append(args)
        if args[2:5] == ["vega", "catalog", "resources"]:
            return json.dumps({"entries": self.existing})
        if args[2:5] == ["bkn", "object-type", "get"]:
            return json.dumps({"entries": [{"id": args[6], "name": "齐套排产计划", "data_properties": []}]})
        if args[2] == "call" and args[4:6] == ["-X", "POST"]:
            return json.dumps({"id": "res-new"})
        return ""


def test_dataset_schema_follows_the_plan_object():
    plan = plan_object("supply_ontology_hand")
    schema = {f["name"]: f["type"] for f in dataset_schema(plan)}
    assert schema["plan_id"] == "string" and schema["planned_start"] == "datetime"
    assert schema["reschedule_count"] == "integer" and schema["quantity"] == "integer" and schema["kit_date"] == "date"
    rows = history_rows(plan)
    assert len(rows) == 13 and all(isinstance(r["reschedule_count"], int) for r in rows)
    assert all("product_code" not in r for r in rows if r["plan_id"].endswith("-ALL-01"))


def test_creates_the_dataset_binds_the_object_and_loads_history():
    cli = Cli()
    report = run(CONFIG, cmd=cli)
    assert report == {"resource_id": "res-new", "created": True, "object_type_id": "supply_ontology_hand_kitplan",
                      "history_rows": 13}
    create = next(c for c in cli.calls if c[2] == "call" and c[5] == "POST")
    body = json.loads(create[7])
    assert body["catalog_id"] == "cat-1" and body["category"] == "dataset" and body["name"] == DATASET_NAME
    assert any(c[2:5] == ["bkn", "object-type", "update"] for c in cli.calls)
    puts = [c for c in cli.calls if c[2] == "call" and c[5] == "PUT"]
    assert len(puts) == 13 and puts[0][3].startswith("/api/vega-backend/v1/resources/res-new/data/KP-")


def test_rerun_reuses_the_dataset():
    cli = Cli(existing=[{"id": "res-old", "name": DATASET_NAME, "category": "dataset"}])
    assert run(CONFIG, cmd=cli)["resource_id"] == "res-old"
    assert not any(c[2] == "call" and c[5] == "POST" for c in cli.calls)
