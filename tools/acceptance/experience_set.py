#!/usr/bin/env python3
"""Run a sample's experience-set Cypher on an installed platform and compare it with the answers.

Every `cypher.query` must return its case's expected values; every `cypher.graph` pattern, completed
with `RETURN count(*)`, must match a small, non-empty graph.
The platform token is read from OPENBKN_TOKEN and never printed.

    OPENBKN_TOKEN=... python3 tools/acceptance/experience_set.py samples/supply_ontology_hand \
        --base-url http://localhost:8081
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from installer import experience_set  # noqa: E402
from installer.contract import load_sample  # noqa: E402

RUN_CYPHER_PATH = "/api/agent-retrieval/v1/kn/run_cypher?response_format=json"
# A graph case is read on the canvas; beyond this many paths it is a data question, not a picture.
GRAPH_ROW_LIMIT = 50


def run_cypher(base_url: str, token: str, kn_id: str, query: str) -> dict:
    request = urllib.request.Request(
        base_url.rstrip("/") + RUN_CYPHER_PATH,
        data=json.dumps({"kn_id": kn_id, "query": query}).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        return {"error": f"HTTP {error.code}: {error.read().decode('utf-8', 'replace')[:400]}"}


def check(sample_dir: Path, base_url: str, token: str) -> dict:
    sample = load_sample(sample_dir)
    kn_id = sample["spec"]["knowledgeNetwork"]["id"]
    document = experience_set.load(sample_dir / sample["spec"]["studio"]["experienceSet"])
    cases = []
    for case in document["spec"]["cases"]:
        result = {"id": case["id"], "surfaces": case["surfaces"]}
        cypher = case.get("cypher", {})
        if "query" in cypher:
            response = run_cypher(base_url, token, kn_id, cypher["query"])
            if "error" in response:
                result["query"] = [response["error"]]
            else:
                columns = [column["name"] for column in response.get("columns", [])]
                result["query"] = experience_set.compare_query_result(
                    case["expected"], columns, response.get("entries", []))
        if "graph" in cypher:
            response = run_cypher(base_url, token, kn_id, cypher["graph"] + "\nRETURN count(*) AS paths")
            if "error" in response:
                result["graph"] = [response["error"]]
            else:
                rows = int((response.get("entries") or [{}])[0].get("paths") or 0)
                result["graphRows"] = rows
                if not rows:
                    result["graph"] = ["graph query returned no rows"]
                elif rows > GRAPH_ROW_LIMIT:
                    result["graph"] = [f"graph query returned {rows} rows, more than {GRAPH_ROW_LIMIT} to read on a canvas"]
                else:
                    result["graph"] = []
        result["passed"] = not result.get("query") and not result.get("graph")
        cases.append(result)
    return {
        "sample": sample["metadata"]["name"],
        "knowledgeNetwork": kn_id,
        "passed": all(item["passed"] for item in cases),
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sample_dir", type=Path)
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()
    token = os.environ.get("OPENBKN_TOKEN", "")
    if not token:
        print("OPENBKN_TOKEN is required", file=sys.stderr)
        return 2
    report = check(args.sample_dir.resolve(), args.base_url, token)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
