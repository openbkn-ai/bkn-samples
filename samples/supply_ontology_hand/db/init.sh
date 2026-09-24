#!/bin/sh
# Load supply-chain CSVs into MariaDB. Official entrypoint calls this on an empty datadir.
set -eu
cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/tools"
python3 db/load_supply.py
