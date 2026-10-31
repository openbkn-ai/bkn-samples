"""Discover, register and publish the sample's local Skills idempotently."""

from __future__ import annotations

import argparse
import json
import re
import subprocess

try:
    from installer.sample_logging import run as run_sample_command
except ImportError:
    # Older installers retain the original subprocess behavior.
    run_sample_command = subprocess.run
from pathlib import Path
from typing import Any


from ownership_receipt import require_owned, remember

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"


def skill_name(skill_dir: Path) -> str:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    match = re.search(r"^name:\s*([^\n]+)$", text, re.MULTILINE)
    if not match:
        raise ValueError(f"""SKILL.md missing name: {skill_dir}""")
    return match.group(1).strip().strip('"\'')


def local_skills() -> list[tuple[str, Path]]:
    items = [(skill_name(path), path) for path in sorted(SKILLS_DIR.iterdir()) if (path / "SKILL.md").is_file()]
    if not items:
        raise RuntimeError(f"""Skill directory not found: {SKILLS_DIR}""")
    return items


def run_cli(args: list[str]) -> dict[str, Any]:
    completed = run_sample_command(["openbkn", "--json", *args], check=False, capture_output=True, text=True)
    if completed.returncode:
        raise RuntimeError((completed.stderr or completed.stdout).strip() or 'openbkn skill call failed')
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


def run(*, apply: bool, kn_id: str | None = None) -> dict[str, Any]:
    skills = local_skills()
    if not apply:
        return {"mode": "dry_run", "skills": [{"name": name, "directory": str(path)} for name, path in skills]}
    listing = run_cli(["skill", "list", "--all"])
    entries = listing.get("data") or listing.get("entries") or []
    existing = {str(item.get("name")): item for item in entries if isinstance(item, dict)}
    results = []
    for name, path in skills:
        found = existing.get(name)
        if found and entry_id(found):
            skill_id = entry_id(found)
            require_owned("skills", skill_id)
            run_cli(["skill", "update-package", skill_id, str(path)])
            operation = "updated"
        else:
            created = run_cli(["skill", "register", str(path), "--source", "custom"])
            skill_id = entry_id(created)
            if not skill_id:
                raise RuntimeError(f"""Skill registered without skill_id: {name}""")
            remember("skills", skill_id)
            operation = "registered"
        run_cli(["skill", "set-status", skill_id, "published"])
        results.append({"name": name, "skill_id": skill_id, "operation": operation, "status": "published"})
    if kn_id:
        run_cli(["bkn", "capability", "attach", kn_id, "--skill",
                 ",".join(item["skill_id"] for item in results)])
    return {"mode": "apply", "skills": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Register/update and publish Skills")
    parser.add_argument("--kn-id", help="Mount these skills to the target knowledge network")
    args = parser.parse_args()
    print(json.dumps(run(apply=args.apply, kn_id=args.kn_id), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
