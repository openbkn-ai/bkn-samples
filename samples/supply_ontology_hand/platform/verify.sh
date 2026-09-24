#!/usr/bin/env bash
set -Eeuo pipefail

: "${BKN_CATALOG_ID:?BKN_CATALOG_ID is required}"
: "${BKN_KN_ID:?BKN_KN_ID is required}"
openbkn --json vega catalog get "$BKN_CATALOG_ID" >/dev/null
openbkn --json bkn get "$BKN_KN_ID" >/dev/null
openbkn --json bkn capability list "$BKN_KN_ID" --limit -1 | python3 -c '
import json
import sys

payload = json.load(sys.stdin)
entries = payload.get("entries", [])
boxes = payload.get("boxes", [])
skills = [entry for entry in entries if entry.get("capability_type") == "skill"]
if len(skills) < 3:
    raise SystemExit("expected the three sample skills to be mounted on the knowledge network")
if not any(box.get("total_tools") == box.get("mounted_tools") and box.get("mounted_tools", 0) >= 14 for box in boxes):
    raise SystemExit("expected all 14 sample function tools to be mounted on the knowledge network")
'
