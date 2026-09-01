"""Step 2: import experience-pack KN JSON via openbkn CLI."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_DEFAULT_JSON = _SCRIPT_DIR.parent / "kn" / "supply_ontology_hand.json"
_IMPORT_PATH = "/api/ontology-manager/v1/knowledge-networks"
_UI_FALLBACK_MSG = "请按说明书步骤 2 UI 导入知识网络"


def run_cmd(args: list[str]) -> str:
    proc = subprocess.run(args, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(
            f"openbkn failed ({proc.returncode}): {' '.join(args)}\n{detail}"
        )
    return proc.stdout


def resolve_default_embedding() -> str:
    raw = run_cmd([
        "openbkn", "--json", "model", "small", "get-default", "--type", "embedding"
    ])
    model_id = json.loads(raw).get("model_id")
    if not model_id:
        raise RuntimeError("target environment has no default embedding model")
    return str(model_id)


def strip_index_config(node) -> None:
    """Recursively remove deprecated property index settings in place."""
    if isinstance(node, dict):
        node.pop("index_config", None)
        for value in node.values():
            strip_index_config(value)
    elif isinstance(node, list):
        for item in node:
            strip_index_config(item)


def import_kn(
    json_path: Path, *, dry_run: bool = False, resolve_embedding: bool = False
) -> dict:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    kn_id = payload.get("id")
    kn_name = payload.get("name")
    if not kn_id or not kn_name:
        raise ValueError(f"KN JSON missing id/name: {json_path}")

    if resolve_embedding:
        embedding_id = resolve_default_embedding()
        for obj in payload.get("object_types", []):
            for prop in obj.get("data_properties", []):
                vector = prop.get("index_config", {}).get("vector_config")
                if vector and vector.get("enabled"):
                    vector["model_id"] = embedding_id

    report = {
        "json_path": str(json_path),
        "kn_id": kn_id,
        "kn_name": kn_name,
        "dry_run": dry_run,
    }

    if dry_run:
        report["action"] = "would_import"
        return report

    def post(body_payload: dict) -> str:
        body = json.dumps(body_payload, ensure_ascii=False)
        return run_cmd(["openbkn", "--json", "call", "-X", "POST", _IMPORT_PATH, "-d", body])

    try:
        raw = post(payload)
        report["index_config_stripped"] = False
    except RuntimeError as exc:
        if "index_config" not in str(exc):
            raise
        stripped = copy.deepcopy(payload)
        strip_index_config(stripped)
        raw = post(stripped)
        report["index_config_stripped"] = True
    try:
        report["import_response"] = json.loads(raw)
    except json.JSONDecodeError:
        report["import_response_raw"] = raw

    got = json.loads(run_cmd(["openbkn", "--json", "bkn", "get", kn_id]))
    report["verified"] = got.get("id") == kn_id and got.get("name") == kn_name
    if not report["verified"]:
        raise RuntimeError(f"import verification failed for {kn_id}: {got!r}")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import KN JSON (step 2) via openbkn call")
    parser.add_argument(
        "--json",
        default=str(_DEFAULT_JSON),
        help="Path to KN export JSON (default: ../kn/supply_ontology_hand.json)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only print kn id/name")
    parser.add_argument(
        "--resolve-embedding",
        action="store_true",
        help="Resolve the target environment default embedding before import",
    )
    args = parser.parse_args(argv)

    try:
        report = import_kn(
            Path(args.json),
            dry_run=args.dry_run,
            resolve_embedding=args.resolve_embedding,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (RuntimeError, json.JSONDecodeError, OSError, ValueError) as exc:
        print(_UI_FALLBACK_MSG, file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
