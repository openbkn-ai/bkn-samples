#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/tools"
exec python3 platform/verify_platform.py
