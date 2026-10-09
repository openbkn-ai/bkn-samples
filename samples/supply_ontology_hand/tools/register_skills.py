"""Register the sample's three local Skills, then publish them idempotently."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"


def skill_name(skill_dir: Path) -> str:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    match = re.search(r"^name:\s*([^\n]+)$", text, re.MULTILINE)
    if not match:
        raise ValueError(f"SKILL.md 缺少 name: {skill_dir}")
    return match.group(1).strip().strip('"\'')


def local_skills() -> list[tuple[str, Path]]:
    items = [(skill_name(path), path) for path in sorted(SKILLS_DIR.iterdir()) if (path / "SKILL.md").is_file()]
    if not items:
        raise RuntimeError(f"未找到 Skill 目录: {SKILLS_DIR}")
    return items


def run_cli(args: list[str]) -> dict[str, Any]:
    completed = subprocess.run(["openbkn", "--json", *args], check=False, capture_output=True, text=True)
    if completed.returncode:
        raise RuntimeError((completed.stderr or completed.stdout).strip() or "openbkn skill 调用失败")
    return json.loads(completed.stdout or "{}")


def entry_id(payload: dict[str, Any]) -> str:
    for key in ("skill_id", "id"):
        if payload.get(key):
            return str(payload[key])
    for key in ("data", "entry"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            found = entry_id(nested)
            if found:
                return found
    return ""


def run(*, apply: bool) -> dict[str, Any]:
    skills = local_skills()
    if not apply:
        return {"mode": "dry_run", "skills": [{"name": name, "directory": str(path)} for name, path in skills]}
    listing = run_cli(["skill", "list"])
    entries = listing.get("data") or listing.get("entries") or []
    existing = {str(item.get("name")): item for item in entries if isinstance(item, dict)}
    results = []
    for name, path in skills:
        found = existing.get(name)
        if found and entry_id(found):
            skill_id = entry_id(found)
            run_cli(["skill", "update-package", skill_id, str(path)])
            operation = "updated"
        else:
            created = run_cli(["skill", "register", str(path), "--source", "custom"])
            skill_id = entry_id(created)
            if not skill_id:
                raise RuntimeError(f"Skill 注册成功但未返回 skill_id: {name}")
            operation = "registered"
        run_cli(["skill", "set-status", skill_id, "published"])
        results.append({"name": name, "skill_id": skill_id, "operation": operation, "status": "published"})
    return {"mode": "apply", "skills": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Register/update and publish Skills")
    args = parser.parse_args()
    print(json.dumps(run(apply=args.apply), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
