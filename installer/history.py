"""Persistent terminal installation records for the Studio sample API."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from installer.state_store import write_json

TERMINAL_STATUSES = {"installed", "failed", "conflict", "uninstalled", "uninstall_failed"}
_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")


def record_terminal_installation(state_dir: Path, record: dict) -> None:
    """Archive each terminal attempt once; keep legacy records readable."""
    if record.get("status") not in TERMINAL_STATUSES:
        return
    sample = record.get("sample")
    if not isinstance(sample, str) or not sample:
        return
    version = _safe(record.get("version") or "unknown")
    installation_id = _safe(record.get("id") or "installation")
    attempt = record.get("attemptId")
    suffix = f"-{_safe(attempt)}" if attempt else ""
    path = state_dir / "history" / sample / f"{installation_id}-{version}{suffix}.json"
    if not path.exists():
        write_json(path, record)


def begin_installation_attempt(state_dir: Path, record: dict, previous: dict | None) -> None:
    """Called under the sample worker lock after a request passes preparation."""
    if previous:
        record_terminal_installation(state_dir, previous)
    _, complete = read_installation_history(state_dir, record["sample"], previous)
    record["historyComplete"] = complete if previous or (state_dir / "history" / record["sample"]).exists() else True
    if previous and previous.get("status") == "uninstalled":
        record["id"] = f"inst-{record['sample']}-{uuid4().hex}"
    record["attemptId"] = uuid4().hex
    record["startedAt"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    record.pop("finishedAt", None)
    write_json(state_dir / f"{record['sample']}.json", record)


def read_installation_history(state_dir: Path, sample: str, current: dict | None) -> tuple[list[dict], bool]:
    directory = state_dir / "history" / sample
    items: list[dict] = []
    valid = True
    if directory.is_dir():
        for path in directory.glob("*.json"):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                valid = False
                continue
            if isinstance(value, dict) and value.get("sample") == sample:
                items.append(value)
            else:
                valid = False
    if current and current.get("status") in TERMINAL_STATUSES and not any(
        item.get("attemptId") == current.get("attemptId") and item.get("id") == current.get("id")
        and item.get("version") == current.get("version")
        for item in items
    ):
        items.append(current)
    items.sort(key=lambda item: item.get("finishedAt") or item.get("startedAt") or "", reverse=True)
    complete = bool(items) and valid and all(item.get("historyComplete") is True for item in items)
    if current and current.get("historyComplete") is not True:
        complete = False
    return items, complete


def _safe(value: object) -> str:
    return _SAFE.sub("_", str(value))
