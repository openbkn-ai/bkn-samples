#!/usr/bin/env python3
"""Write manifest-index.json for the pinned VERSION and an explicit git revision."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from installer.contract import ContractError, write_manifest_index  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", required=True, help="40-character source commit")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        index = write_manifest_index(ROOT, args.output, args.revision)
    except ContractError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(f"wrote {args.output} version={index['version']} samples={len(index['samples'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
