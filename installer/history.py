"""Persistent terminal installation records for the Studio sample API."""

from __future__ import annotations

import json
import re
from pathlib import Path

from installer.state_store import write_json

TERMINAL_STATUSES = {"installed", "failed", "conflict"}
_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")


def record_terminal_installation(state_dir: Path, record: dict) -> None:
    """Keep the latest terminal result for each installation/version pair."""
    if record.get("status") not in TERMINAL_STATUSES:
        return
    sample = record.get("sample")
    if not isinstance(sample, str) or not sample:
        return
    version = _safe(record.get("version") or "unknown")
    installation_id = _safe(record.get("id") or "installation")
    write_json(state_dir / "history" / sample / f"{installation_id}-{version}.json", record)


def read_installation_history(state_dir: Path, sample: str, current: dict | None) -> tuple[list[dict], bool]:
    directory = state_dir / "history" / sample
    items: list[dict] = []
    if directory.is_dir():
        for path in directory.glob("*.json"):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(value, dict) and value.get("sample") == sample:
                items.append(value)
    if current and current.get("status") in TERMINAL_STATUSES and not any(
        item.get("id") == current.get("id") and item.get("version") == current.get("version")
        for item in items
    ):
        items.append(current)
    items.sort(key=lambda item: item.get("finishedAt") or item.get("startedAt") or "", reverse=True)
    return items, directory.is_dir()


def _safe(value: object) -> str:
    return _SAFE.sub("_", str(value))
