"""Resolve a data-image build from a validated sample manifest, not a name list."""

import argparse
import json
import re
from pathlib import Path

from installer.contract import discover_sample_dirs, load_sample, validate_repository


def plan(root: Path, sample: str, version: str, context: str) -> dict:
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", sample):
        raise ValueError("invalid sample ID")
    if not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", version):
        raise ValueError("version must be MAJOR.MINOR.PATCH")
    if context not in {"repository", "sample"}:
        raise ValueError("unsupported build context")
    validate_repository(root)
    matches = [p for p in discover_sample_dirs(root)
               if load_sample(p)["metadata"]["name"] == sample]
    if len(matches) != 1:
        raise ValueError("sample ID must resolve to exactly one manifest")
    directory = matches[0]
    for path in [directory / "db/Dockerfile",
                 directory / "releases" / version / "release-notes.en-US.md"]:
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("missing or unsafe Dockerfile or version release notes")
    relative = directory.relative_to(root).as_posix()
    return {"directory": relative, "context": "." if context == "repository" else relative,
            "dockerfile": relative + "/db/Dockerfile",
            "tag": f"ghcr.io/openbkn-ai/bkn-samples:sample-{sample}-v{version}"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--context", choices=["repository", "sample"], default="sample")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    result = plan(Path(__file__).resolve().parents[2], args.sample, args.version, args.context)
    if args.github_output:
        with args.github_output.open("a") as output:
            for key, value in result.items():
                output.write(f"{key}={value}\n")
    print(json.dumps(result))
