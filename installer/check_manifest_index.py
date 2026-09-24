#!/usr/bin/env python3
"""Check a built manifest index against VERSION and the sample files."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from installer.contract import ContractError, check_manifest_index  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    args = parser.parse_args()
    try:
        check_manifest_index(ROOT, json.loads(args.index.read_text(encoding="utf-8")))
    except ContractError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(f"manifest index matches VERSION and {args.index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
