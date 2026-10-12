"""Local-only prerequisite checks for the OpenBKN 0.1.4 onboarding path."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

import yaml

_CLI_VERSION = "0.1.4"
_MIN_NODE = (24, 19, 0)


def _local_run(args: list[str]) -> str:
    completed = subprocess.run(args, check=False, capture_output=True, text=True)
    if completed.returncode:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(f"{' '.join(args)} failed: {detail}")
    return completed.stdout.strip()


def _version(value: str) -> tuple[int, int, int] | None:
    match = re.search(r"v?(\d+)\.(\d+)\.(\d+)", value)
    return tuple(map(int, match.groups())) if match else None


def run_preflight(config: dict, *, run_local: Callable[[list[str]], str] | None = None) -> dict:
    """Validate local tooling and config only; never call an OpenBKN platform."""
    run = run_local or _local_run
    errors: list[str] = []
    warnings: list[str] = []
    cli_version = ""
    node_version = ""

    try:
        cli_version = run(["openbkn", "--version"]).strip().lstrip("v")
        if cli_version != _CLI_VERSION:
            errors.append(f"openbkn CLI must be {_CLI_VERSION}; found {cli_version or 'unknown'}")
    except RuntimeError as exc:
        errors.append(str(exc))

    try:
        node_version = run(["node", "--version"]).strip().lstrip("v")
        parsed_node = _version(node_version)
        if parsed_node is None or parsed_node < _MIN_NODE:
            errors.append("Node.js must be >=24.19.0 for openbkn CLI 0.1.4")
    except RuntimeError as exc:
        errors.append(str(exc))

    database = config.get("database") or {}
    engine = database.get("engine")
    if engine not in {"postgres", "mysql"}:
        errors.append("database.engine must be postgres or mysql")
    for key in ("host", "port", "database", "user"):
        if not database.get(key):
            errors.append(f"database.{key} is required")

    options = (config.get("vega") or {}).get("connector_options") or {}
    if engine == "mysql" and "sslmode" in options:
        warnings.append("vega.connector_options.sslmode is PostgreSQL-only and will be ignored for MySQL")

    return {
        "ok": not errors,
        "cli_version": cli_version,
        "node_version": node_version,
        "errors": errors,
        "warnings": warnings,
        "network_checked": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check local OpenBKN 0.1.4 prerequisites without network calls")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    args = parser.parse_args(argv)
    try:
        config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
        report = run_preflight(config)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ok"] else 1
    except (OSError, yaml.YAMLError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
