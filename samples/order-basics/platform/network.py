"""Import and query the sample through standard OpenBKN CLI APIs."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KN = "order_basics"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def cli(*args):
    result = subprocess.run(["openbkn", "--json", *args], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("standard OpenBKN API call failed")
    return json.loads(result.stdout)


def entries(value):
    if isinstance(value, list):
        return value
    for key in ("entries", "datas", "data", "instances"):
        if isinstance(value.get(key), list):
            return value[key]
    raise ValueError("missing result entries")


def main():
    payload = json.loads(Path(os.environ["BKN_SAMPLE_INPUT"]).read_text())
    require(payload["sample"] == "order-basics", "unexpected sample")
    require(payload["knowledgeNetwork"]["id"] == KN, "unexpected network")
    require(payload["database"]["name"] == KN, "unexpected database")
    tags = {"bkn-samples", "bkn-sample-order-basics", "bkn-samples-version-" + payload["version"].replace(".", "-")}
    if sys.argv[1] == "install":
        resources = entries(cli("vega", "resource", "list", "--catalog-id", payload["catalog"]["id"], "--category", "table", "--limit", "100"))
        source = json.loads((ROOT / "kn/order_basics.json").read_text())
        source["tags"] = sorted(tags)
        for obj in source["object_types"]:
            matches = [r for r in resources if r["name"].rsplit(".", 1)[-1] == obj["id"]]
            require(len(matches) == 1, "missing or ambiguous data resource")
            source_id = matches[0]["id"]
            obj["data_source"] = {"type": "resource", "id": source_id, "name": matches[0]["name"]}
        existing = subprocess.run(["openbkn", "--json", "bkn", "get", KN], capture_output=True, text=True)
        if existing.returncode == 0:
            current = json.loads(existing.stdout)
            require(tags <= set(current.get("tags", [])), "knowledge network ownership conflict")
            for obj in source["object_types"]:
                found = cli("bkn", "object-type", "get", KN, obj["id"])
                found = entries(found)[0] if isinstance(found, list) or (isinstance(found, dict) and "entries" in found) else found
                require(found["data_source"]["id"] == obj["data_source"]["id"], "knowledge network binding conflict")
        else:
            require("404" in existing.stderr + existing.stdout, "cannot confirm that knowledge network is absent")
            cli("call", "-X", "POST", "/api/ontology-manager/v1/knowledge-networks",
                "-d", json.dumps(source, ensure_ascii=False))
        checks = [{"name": "network-import", "ok": True}]
    elif sys.argv[1] == "verify":
        products = entries(cli("bkn", "object-type", "query", KN, "products", "--body", '{"limit":10}'))
        orders = entries(cli("bkn", "object-type", "query", KN, "orders", "--body", '{"limit":10}'))
        require(len(products) == 3 and len(orders) == 4, "object counts differ")
        prices = {p["product_id"]: float(p["unit_price"]) for p in products}
        require(sum(int(o["quantity"]) for o in orders) == 8, "order quantity differs")
        require(sum(int(o["quantity"]) * prices[o["product_id"]] for o in orders) == 750, "joined amount differs")
        network = cli("bkn", "get", KN, "--export")
        require(len(network["relation_types"]) == 1, "relation count differs")
        checks = [{"name": name, "ok": True} for name in ("object-query", "order-product-join", "relation-import")]
    else:
        raise ValueError("expected install or verify")
    result = {"ok": True, "stage": "platform-" + sys.argv[1],
              "resources": {"catalogId": payload["catalog"]["id"], "knowledgeNetworkId": KN,
                            "ownedExecution": {"toolboxes": [], "skills": []}},
              "checks": checks, "degrade": [], "message": ""}
    Path(os.environ["BKN_SAMPLE_OUTPUT"]).write_text(json.dumps(result, ensure_ascii=False))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
