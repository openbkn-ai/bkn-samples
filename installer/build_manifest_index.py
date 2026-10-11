#!/usr/bin/env python3
"""Write manifest-index.json for the pinned VERSION and an explicit git revision."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from installer.contract import ContractError, write_manifest_index  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", required=True, help="40-character source commit")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--samples", nargs="+", help="Only index samples included in the bundled data image")
    args = parser.parse_args()
    try:
        index = write_manifest_index(ROOT, args.output, args.revision)
        if args.samples:
            selected = set(args.samples)
            if not selected <= {item["name"] for item in index["samples"]}:
                raise ContractError("unknown bundled sample")
            index["samples"] = [item for item in index["samples"] if item["name"] in selected]
            args.output.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except ContractError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(f"wrote {args.output} version={index['version']} samples={len(index['samples'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
