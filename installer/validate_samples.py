#!/usr/bin/env python3
"""Validate every samples/*/sample.yaml against samples.openbkn.ai/v1alpha1."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from installer.contract import ContractError, validate_repository  # noqa: E402


def main() -> int:
    try:
        samples = validate_repository(ROOT)
    except ContractError as exc:
        print(exc, file=sys.stderr)
        return 1
    names = ", ".join(sample["metadata"]["name"] for sample in samples) or "(none)"
    print(f"valid samples: {names}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
