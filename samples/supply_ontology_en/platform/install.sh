#!/bin/sh
# Platform hook. Reads BKN_SAMPLE_INPUT and does not call kubectl.
set -eu
cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/tools"
exec python3 platform/install_supply.py
