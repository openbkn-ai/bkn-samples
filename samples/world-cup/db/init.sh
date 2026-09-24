#!/bin/sh
# Download, verify, and load the world-cup CSVs into MariaDB.
set -eu
cd "$(dirname "$0")/.."
exec python3 db/load_worldcup.py
