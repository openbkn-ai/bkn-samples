#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/tools"
python3 db/verify_supply.py
