"""Sample-owned metadata and evaluation contract for Foundry #2516."""
import json
from pathlib import Path

import import_kn as importer

PACKAGE = Path(__file__).resolve().parents[2]
KN = PACKAGE / "kn" / f"{PACKAGE.name}.json"


def material_properties(payload):
    material = next(o for o in payload["object_types"] if o["id"].endswith("_material"))
    return {p["name"]: p for p in material["data_properties"]}


def test_material_classifications_keep_distinct_meanings():
    fields = material_properties(json.loads(KN.read_text()))
    assert fields["group_name"]["display_name"] != fields["group_type"]["display_name"]
    for name, other in [("group_name", "group_type"), ("group_type", "group_name")]:
        prop = fields[name]
        assert prop["mapped_field"]["name"] == name
        # Both descriptions must identify the other field and distinguish it.
        assert other in prop["comment"]
        assert ("不同" in prop["comment"]) or ("distinct" in prop["comment"])


def test_import_sends_the_classification_metadata_without_rewriting(monkeypatch):
    source = json.loads(KN.read_text())
    sent = []
    lookups = 0

    def call(args):
        nonlocal lookups
        if args[2:4] == ["bkn", "get"]:
            lookups += 1
            if lookups == 1:
                raise RuntimeError("fixture network does not exist")
            return json.dumps({"id": source["id"], "name": source["name"]})
        assert args[2] == "call"
        sent.append(json.loads(args[-1]))
        return '{}'

    monkeypatch.setattr(importer, "run_cmd", call)
    assert importer.import_kn(KN)["verified"]
    assert len(sent) == 1
    actual = material_properties(sent[0])
    expected = material_properties(source)
    for name in ["group_name", "group_type"]:
        assert actual[name] == expected[name]

